from io import BytesIO

from flask import Flask, render_template, abort, request, redirect, url_for, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from models import db, Project, Service, AuditEntry, Order 

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lean_erp.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

def format_euro(value):
    """Formatiert einen Betrag im deutschen Stil mit Tausenderpunkt und Dezimalkomma."""
    # Punkt und Komma sind im deutschen Format vertauscht, daher der Umweg über X.
    formatted = f"{value:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


app.jinja_env.filters["euro"] = format_euro

AVAILABLE_ROLES = {
    "project_manager_a": "Projektleitung A",
    "project_manager_b": "Projektleitung B",
    "controlling": "Controlling",
    "management": "Management",
}

# Freigabe-Workflow: erfasst -> geprüft -> freigegeben.
SERVICE_STATUSES = ["erfasst", "geprüft", "freigegeben"]

# Rollenbasierte Rechte für die Statusübergänge.
# Projektleitung darf prüfen, Controlling gibt final frei.
STATUS_PERMISSIONS = {
    "geprüft": {"project_manager_a", "project_manager_b"},
    "freigegeben": {"controlling"},
    "erfasst": {"project_manager_a", "project_manager_b", "controlling"},
}


def get_current_role():
    role = request.args.get("role", "controlling")
    if role not in AVAILABLE_ROLES:
        role = "controlling"
    return role


def get_form_role():
    role = request.form.get("role", "controlling")
    if role not in AVAILABLE_ROLES:
        role = "controlling"
    return role


def get_visible_projects(role):
    if role == "project_manager_a":
        return Project.query.filter_by(project_manager="Projektleitung A").all()
    if role == "project_manager_b":
        return Project.query.filter_by(project_manager="Projektleitung B").all()
    return Project.query.all()


def get_project_or_404(project_id, role):
    project = Project.query.get(project_id)
    if project is None:
        abort(404)

    # Projektleitung darf nur eigene Projekte sehen.
    if role == "project_manager_a" and project.project_manager != "Projektleitung A":
        abort(404)
    if role == "project_manager_b" and project.project_manager != "Projektleitung B":
        abort(404)

    return project


def can_edit_project(role):
    """Wer darf Leistungen erfassen?"""
    return role in {"project_manager_a", "project_manager_b", "controlling"}

def can_add_order(role):
    """Wer darf Bestellungen erfassen? Nur Controlling."""
    return role == "controlling"

def can_set_status(role, new_status):
    """Wer darf eine Leistung auf einen bestimmten Status setzen?"""
    return role in STATUS_PERMISSIONS.get(new_status, set())


@app.route("/")
def index():
    current_role = get_current_role()
    visible_projects = get_visible_projects(current_role)

    return render_template(
        "index.html",
        projects=visible_projects,
        current_role=current_role,
        available_roles=AVAILABLE_ROLES,
    )


@app.route("/projects/<int:project_id>")
def project_detail(project_id):
    current_role = get_current_role()
    project = get_project_or_404(project_id, current_role)

    return render_template(
        "project_detail.html",
        project=project,
        current_role=current_role,
        available_roles=AVAILABLE_ROLES,
        can_edit=can_edit_project(current_role),
        can_add_order=can_add_order(current_role),
        statuses=SERVICE_STATUSES,
        status_permissions=STATUS_PERMISSIONS,
    )


@app.route("/projects/<int:project_id>/add-service", methods=["POST"])
def add_service(project_id):
    current_role = get_form_role()
    project = get_project_or_404(project_id, current_role)

    if not can_edit_project(current_role):
        abort(403)

    # Neue Leistungen starten immer im Status 'erfasst'.
    new_service = Service(
        date=request.form["date"],
        description=request.form["description"],
        hours=float(request.form["hours"]),
        status="erfasst",
    )
    project.services.append(new_service)

    AuditEntry.create(
        project,
        "Leistung hinzugefuegt",
        f"{new_service.description} mit {new_service.hours:.1f} Stunden wurde im Status 'erfasst' angelegt.",
    )

    db.session.commit()
    return redirect(url_for("project_detail", project_id=project_id, role=current_role))

@app.route("/projects/<int:project_id>/add-order", methods=["POST"])
def add_order(project_id):
    current_role = get_form_role()
    project = get_project_or_404(project_id, current_role)

    if not can_add_order(current_role):
        abort(403)

    # Neue Bestellungen starten standardmaessig im Status 'offen'.
    new_order = Order(
        date=request.form["date"],
        description=request.form["description"],
        supplier=request.form["supplier"],
        amount=float(request.form["amount"]),
        status="offen",
    )
    project.orders.append(new_order)

    AuditEntry.create(
        project,
        "Bestellung erfasst",
        f"Bestellung '{new_order.description}' ueber {new_order.amount:.2f} EUR ({new_order.supplier}) wurde im Status 'offen' angelegt.",
    )

    db.session.commit()
    return redirect(url_for("project_detail", project_id=project_id, role=current_role))


@app.route("/projects/<int:project_id>/services/<int:service_id>/update-status", methods=["POST"])
def update_service_status(project_id, service_id):
    current_role = get_form_role()
    project = get_project_or_404(project_id, current_role)

    service = Service.query.get(service_id)
    if service is None or service.project_id != project.id:
        abort(404)

    new_status = request.form["status"]
    if new_status not in SERVICE_STATUSES:
        abort(400)

    # Rollenbasierte Pruefung des Statusuebergangs.
    if not can_set_status(current_role, new_status):
        abort(403)

    old_status = service.status
    service.status = new_status

    AuditEntry.create(
        project,
        "Status geaendert",
        f"Die Leistung '{service.description}' wurde von '{old_status}' auf '{new_status}' gesetzt.",
    )

    db.session.commit()
    return redirect(url_for("project_detail", project_id=project_id, role=current_role))


def _approved_services(project):
    return [s for s in project.services if s.status == "freigegeben"]


@app.route("/projects/<int:project_id>/invoice-draft")
def invoice_draft(project_id):
    current_role = get_current_role()
    project = get_project_or_404(project_id, current_role)

    approved_services = _approved_services(project)
    total_hours = sum(s.hours for s in approved_services)
    total_amount = total_hours * project.hourly_rate

    return render_template(
        "invoice_draft.html",
        project=project,
        approved_services=approved_services,
        total_hours=total_hours,
        total_amount=total_amount,
        current_role=current_role,
        available_roles=AVAILABLE_ROLES,
    )


@app.route("/projects/<int:project_id>/invoice-draft/pdf")
def invoice_draft_pdf(project_id):
    current_role = get_current_role()
    project = get_project_or_404(project_id, current_role)

    approved_services = _approved_services(project)
    total_hours = sum(s.hours for s in approved_services)
    total_amount = total_hours * project.hourly_rate

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    pdf.setTitle(f"Rechnungsentwurf_{project.project_number}")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Rechnungsentwurf")
    y -= 30

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Projekt: {project.name}")
    y -= 20
    pdf.drawString(50, y, f"Projektnummer: {project.project_number}")
    y -= 20
    pdf.drawString(50, y, f"Kunde: {project.customer}")
    y -= 20
    pdf.drawString(50, y, f"Stundensatz: {format_euro(project.hourly_rate)} EUR")
    y -= 30

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Freigegebene Leistungen")
    y -= 25

    pdf.setFont("Helvetica", 10)

    if approved_services:
        for service in approved_services:
            line = (
                f"{service.date} | {service.description} | "
                f"{service.hours:.2f} h | {service.status}"
            )
            pdf.drawString(50, y, line)
            y -= 18
            if y < 80:
                pdf.showPage()
                y = height - 50
                pdf.setFont("Helvetica", 10)

        y -= 10
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(50, y, f"Gesamtstunden: {total_hours:.2f}")
        y -= 20
        pdf.drawString(50, y, f"Entwurfsbetrag: {format_euro(total_amount)} EUR")
    else:
        pdf.drawString(50, y, "Fuer dieses Projekt liegen aktuell keine freigegebenen Leistungen vor.")

    pdf.save()
    buffer.seek(0)

    filename = f"rechnungsentwurf_{project.project_number}.pdf"
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


if __name__ == "__main__":
    app.run(debug=True)