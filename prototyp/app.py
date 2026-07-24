from io import BytesIO

from flask import Flask, render_template, abort, request, redirect, url_for, send_file, flash
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.pdfgen import canvas
from datetime import datetime

from models import db, Project, Service, AuditEntry, Order 

app = Flask(__name__)
app.secret_key = "lean-erp-prototyp-evaluation"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///lean_erp.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

def format_date_german(value):
    """Wandelt ein ISO-Datum (2026-05-01) in deutsche Schreibweise (01.05.2026)."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return value

def format_euro(value):
    """Formatiert einen Betrag im deutschen Stil mit Tausenderpunkt und Dezimalkomma."""
    # Punkt und Komma sind im deutschen Format vertauscht, daher der Umweg über X.
    formatted = f"{value:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


app.jinja_env.filters["euro"] = format_euro

def parse_positive_number(raw_value):
    """Wandelt eine Formulareingabe in eine positive Zahl um.

    Gibt die Zahl zurück, wenn die Eingabe gültig und größer als null ist,
    sonst None.
    """
    try:
        number = float(str(raw_value).replace(",", "."))
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return number

AVAILABLE_ROLES = {
    "project_manager_a": "Projektleitung A",
    "project_manager_b": "Projektleitung B",
    "controlling": "Controlling",
    "management": "Management",
}

# Freigabe-Workflow: erfasst -> geprüft -> freigegeben.
SERVICE_STATUSES = ["erfasst", "geprüft", "freigegeben"]

# Projektstatus
PROJECT_STATUSES = ["Angebot", "Beauftragt", "In Bearbeitung", "Abgerechnet", "Gestorben"]

# Rollenbasierte Rechte für die Statusübergänge.
# Projektleitung darf prüfen, Controlling gibt final frei.
STATUS_PERMISSIONS = {
    "geprüft": {"project_manager_a", "project_manager_b"},
    "freigegeben": {"controlling"},
    "erfasst": {"project_manager_a", "project_manager_b", "controlling"},
}

# Erlaubte Statusübergänge. Die Kette wird schrittweise durchlaufen,
# ein Überspringen von 'geprüft' ist nicht möglich. Ein Schritt zurück
# bleibt zulässig, damit Fehleingaben korrigiert werden koennen.
ALLOWED_TRANSITIONS = {
    "erfasst": {"geprüft"},
    "geprüft": {"erfasst", "freigegeben"},
    "freigegeben": {"geprüft"},
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

def can_add_project(role):
    """Wer darf neue Projekte anlegen? Nur Controlling."""
    return role == "controlling"

def can_set_status(role, new_status):
    """Wer darf eine Leistung auf einen bestimmten Status setzen?"""
    return role in STATUS_PERMISSIONS.get(new_status, set())

def is_allowed_transition(old_status, new_status):
    """Ist der Übergang vom aktuellen auf den neuen Status zulässig?"""
    return new_status in ALLOWED_TRANSITIONS.get(old_status, set())

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
        project_statuses=PROJECT_STATUSES,
        allowed_transitions=ALLOWED_TRANSITIONS,
    )


@app.route("/projects/<int:project_id>/add-service", methods=["POST"])
def add_service(project_id):
    current_role = get_form_role()
    project = get_project_or_404(project_id, current_role)

    if not can_edit_project(current_role):
        abort(403)

    description = request.form["description"].strip()
    hours = parse_positive_number(request.form["hours"])

    if not description:
        flash("Bitte eine Beschreibung für die Leistung angeben.", "error")
        return redirect(url_for("project_detail", project_id=project_id, role=current_role))

    if hours is None:
        flash("Bitte für die Stunden eine positive Zahl angeben.", "error")
        return redirect(url_for("project_detail", project_id=project_id, role=current_role))

    # Neue Leistungen starten immer im Status 'erfasst'.
    new_service = Service(
        date=request.form["date"],
        description=description,
        hours=hours,
        status="erfasst",
    )
    project.services.append(new_service)

    AuditEntry.create(
        project,
        "Leistung hinzugefügt",
        f"{new_service.description} mit {new_service.hours:.1f} Stunden wurde im Status 'erfasst' angelegt.",
    )

    db.session.commit()
    flash("Leistung wurde erfasst.", "success")
    return redirect(url_for("project_detail", project_id=project_id, role=current_role))

@app.route("/projects/<int:project_id>/add-order", methods=["POST"])
def add_order(project_id):
    current_role = get_form_role()
    project = get_project_or_404(project_id, current_role)

    if not can_add_order(current_role):
        abort(403)

    description = request.form["description"].strip()
    supplier = request.form["supplier"].strip()
    amount = parse_positive_number(request.form["amount"])

    if not description:
        flash("Bitte eine Bezeichnung für die Bestellung angeben.", "error")
        return redirect(url_for("project_detail", project_id=project_id, role=current_role))

    if not supplier:
        flash("Bitte einen Lieferanten angeben.", "error")
        return redirect(url_for("project_detail", project_id=project_id, role=current_role))

    if amount is None:
        flash("Bitte für den Betrag eine positive Zahl angeben.", "error")
        return redirect(url_for("project_detail", project_id=project_id, role=current_role))

    # Neue Bestellungen starten standardmässig im Status 'offen'.
    new_order = Order(
        date=request.form["date"],
        description=description,
        supplier=supplier,
        amount=amount,
        status="offen",
    )
    project.orders.append(new_order)

    AuditEntry.create(
        project,
        "Bestellung erfasst",
        f"Bestellung '{new_order.description}' über {new_order.amount:.2f} EUR ({new_order.supplier}) wurde im Status 'offen' angelegt.",
    )

    db.session.commit()
    flash("Bestellung wurde erfasst.", "success")
    return redirect(url_for("project_detail", project_id=project_id, role=current_role))

@app.route("/projects/new", methods=["POST"])
def add_project():
    current_role = get_form_role()

    if not can_add_project(current_role):
        abort(403)

    project_number = request.form["project_number"].strip()
    name = request.form["name"].strip()
    customer = request.form["customer"].strip()
    project_manager = request.form["project_manager"].strip()
    budget = parse_positive_number(request.form["budget"])
    hourly_rate = parse_positive_number(request.form["hourly_rate"])
    customer_order_number = request.form.get("customer_order_number", "").strip() or None

    if not project_number or not name or not customer or not project_manager:
        flash("Bitte alle Pflichtfelder des Projekts ausfüllen.", "error")
        return redirect(url_for("index", role=current_role))

    if budget is None:
        flash("Bitte für das Budget eine positive Zahl angeben.", "error")
        return redirect(url_for("index", role=current_role))

    if hourly_rate is None:
        flash("Bitte für den Stundensatz eine positive Zahl angeben.", "error")
        return redirect(url_for("index", role=current_role))

    # Projektnummer muss eindeutig sein.
    existing = Project.query.filter_by(project_number=project_number).first()
    if existing is not None:
        flash(f"Die Projektnummer {project_number} ist bereits vergeben.", "error")
        return redirect(url_for("index", role=current_role))

    project = Project(
        project_number=project_number,
        name=name,
        customer=customer,
        status="In Bearbeitung",
        budget=budget,
        project_manager=project_manager,
        hourly_rate=hourly_rate,
        customer_order_number=customer_order_number,
    )
    db.session.add(project)

    AuditEntry.create(
        project,
        "Projekt angelegt",
        f"Projekt '{name}' ({project_number}) wurde im System angelegt.",
    )

    db.session.commit()
    flash("Projekt wurde angelegt.", "success")
    return redirect(url_for("project_detail", project_id=project.id, role=current_role))

@app.route("/projects/<int:project_id>/update-order-number", methods=["POST"])
def update_order_number(project_id):
    current_role = get_form_role()
    project = get_project_or_404(project_id, current_role)

    # Nur das Controlling pflegt die Bestellnummer des Kunden.
    if current_role != "controlling":
        abort(403)

    new_number = request.form.get("customer_order_number", "").strip()
    old_number = project.customer_order_number

    if not new_number and not old_number:
        return redirect(url_for("project_detail", project_id=project_id, role=current_role))

    project.customer_order_number = new_number or None

    if new_number and not old_number:
        details = f"Bestellnummer des Kunden '{new_number}' wurde ergänzt."
    elif new_number:
        details = f"Bestellnummer des Kunden von '{old_number}' auf '{new_number}' geändert."
    else:
        details = f"Bestellnummer des Kunden '{old_number}' wurde entfernt."

    AuditEntry.create(project, "Bestellnummer aktualisiert", details)
    db.session.commit()
    flash("Bestellnummer des Kunden aktualisiert.", "success")
    return redirect(url_for("project_detail", project_id=project_id, role=current_role))

@app.route("/projects/<int:project_id>/orders/<int:order_id>/update-amount", methods=["POST"])
def update_order_amount(project_id, order_id):
    current_role = get_form_role()
    project = get_project_or_404(project_id, current_role)

    # Korrekturen am Bestellbetrag nimmt nur das Controlling vor.
    if not can_add_order(current_role):
        abort(403)

    order = Order.query.get(order_id)
    if order is None or order.project_id != project.id:
        abort(404)

    new_amount = parse_positive_number(request.form["amount"])
    if new_amount is None:
        flash("Bitte für den Betrag eine positive Zahl angeben.", "error")
        return redirect(url_for("project_detail", project_id=project_id, role=current_role))

    old_amount = order.amount
    if new_amount == old_amount:
        return redirect(url_for("project_detail", project_id=project_id, role=current_role))

    order.amount = new_amount

    AuditEntry.create(
        project,
        "Bestellbetrag korrigiert",
        f"Der Betrag der Bestellung '{order.description}' wurde von {old_amount:.2f} EUR auf {new_amount:.2f} EUR geändert.",
    )

    db.session.commit()
    flash("Bestellbetrag wurde korrigiert.", "success")
    return redirect(url_for("project_detail", project_id=project_id, role=current_role))

@app.route("/projects/<int:project_id>/update-status", methods=["POST"])
def update_project_status(project_id):
    current_role = get_form_role()
    project = get_project_or_404(project_id, current_role)

    # Der kaufmännische Projektstatus wird vom Controlling gepflegt.
    if current_role != "controlling":
        abort(403)

    new_status = request.form.get("status", "")
    if new_status not in PROJECT_STATUSES:
        abort(400)

    old_status = project.status
    if new_status == old_status:
        return redirect(url_for("project_detail", project_id=project_id, role=current_role))

    project.status = new_status

    AuditEntry.create(
        project,
        "Projektstatus geändert",
        f"Der Projektstatus wurde von '{old_status}' auf '{new_status}' gesetzt.",
    )

    db.session.commit()
    flash("Projektstatus wurde aktualisiert.", "success")
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

   # Rollenbasierte Prüfung des Statusübergangs.
    if not can_set_status(current_role, new_status):
        abort(403)

    old_status = service.status

    # Fachliche Prüfung der Statusfolge.
    if not is_allowed_transition(old_status, new_status):
        flash("Dieser Statuswechsel ist nicht vorgesehen.", "error")
        return redirect(url_for("project_detail", project_id=project_id, role=current_role))

    service.status = new_status

    AuditEntry.create(
        project,
        "Status geändert",
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
    service_dates = sorted(s.date for s in approved_services)
    service_period = None
    if len(service_dates) == 1:
        service_period = format_date_german(service_dates[0])
    elif service_dates:
        service_period = f"{format_date_german(service_dates[0])} – {format_date_german(service_dates[-1])}"

    return render_template(
        "invoice_draft.html",
        project=project,
        approved_services=approved_services,
        total_hours=total_hours,
        total_amount=total_amount,
        service_period=service_period,
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
    service_dates = sorted(s.date for s in approved_services)
    service_period = None
    if len(service_dates) == 1:
        service_period = format_date_german(service_dates[0])
    elif service_dates:
        service_period = f"{format_date_german(service_dates[0])} – {format_date_german(service_dates[-1])}"
    created_on = datetime.now().strftime("%d.%m.%Y")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left = 25 * mm
    right = width - 25 * mm

    pdf.setTitle(f"Rechnungsentwurf_{project.project_number}")

    # --- Briefkopf (Platzhalter, frei änderbar) ---
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(left, height - 30 * mm, "Musterfirma GmbH")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(left, height - 35 * mm, "Musterstraße 1, 12345 Musterstadt")
    pdf.drawString(left, height - 39 * mm, "kontakt@musterfirma.de")

    # --- Titel und Trennlinie ---
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(left, height - 52 * mm, "Rechnungsentwurf")
    pdf.setFont("Helvetica-Oblique", 10)
    pdf.drawString(left, height - 58 * mm, "Keine Rechnung – Zuarbeit für die Rechnungsstellung")
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(right, height - 52 * mm, f"Erstellt am {created_on}")
    pdf.setLineWidth(0.8)
    pdf.line(left, height - 61 * mm, right, height - 61 * mm)

    # --- Projektangaben ---
    y = height - 70 * mm
    pdf.setFont("Helvetica", 10)
    angaben = [
        ("Projekt", project.name),
        ("Projektnummer", project.project_number),
        ("Kunde", project.customer),
        ("Stundensatz", f"{format_euro(project.hourly_rate)} EUR"),
        ("Ihre Bestellnummer", project.customer_order_number or "–"),
        ("Leistungszeitraum", service_period or "–"),
    ]
    for label, value in angaben:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(left, y, f"{label}:")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(left + 35 * mm, y, str(value))
        y -= 6 * mm

    # --- Leistungstabelle ---
    y -= 6 * mm
    if approved_services:
        data = [["Pos.", "Datum", "Bezeichnung", "Menge", "Einheit", "Einzel EUR", "Gesamt EUR"]]
        for pos, s in enumerate(approved_services, start=1):
            betrag = s.hours * project.hourly_rate
            data.append([
                str(pos),
                format_date_german(s.date),
                s.description,
                f"{s.hours:.2f}",
                "h",
                format_euro(project.hourly_rate),
                format_euro(betrag),
            ])

        table = Table(data, colWidths=[10 * mm, 22 * mm, 52 * mm, 16 * mm, 14 * mm, 22 * mm, 24 * mm])
        table.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
            ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f2f5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1f2933")),
            ("ALIGN", (3, 0), (6, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd2d9")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))

        table_width, table_height = table.wrapOn(pdf, width, height)
        table.drawOn(pdf, left, y - table_height)
        y = y - table_height - 10 * mm

        # --- Summenbereich ---
        pdf.setFont("Helvetica", 10)
        pdf.drawRightString(right - 32 * mm, y, "Gesamtstunden:")
        pdf.drawRightString(right, y, f"{total_hours:.2f}")
        y -= 7 * mm
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawRightString(right - 32 * mm, y, "Entwurfsbetrag (netto):")
        pdf.drawRightString(right, y, f"{format_euro(total_amount)} EUR")
        y -= 7 * mm
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(right, y, "Umsatzsteuer und Gesamtbetrag werden bei der Rechnungsstellung ergänzt.")
    else:
        pdf.setFont("Helvetica", 10)
        pdf.drawString(left, y, "Für dieses Projekt liegen aktuell keine freigegebenen Leistungen vor.")

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
    app.run(debug=True, port=5001)