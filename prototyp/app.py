from datetime import datetime
from io import BytesIO

from flask import Flask, render_template, abort, request, redirect, url_for, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from mock_data import PROJECTS

app = Flask(__name__)

AVAILABLE_ROLES = {
    "project_manager_a": "Projektleitung A",
    "project_manager_b": "Projektleitung B",
    "controlling": "Controlling",
    "management": "Management",
}


def add_audit_entry(project, action, details):
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "action": action,
        "details": details,
    }
    project["audit_log"].insert(0, entry)


def get_current_role():
    role = request.args.get("role", "controlling")
    if role not in AVAILABLE_ROLES:
        role = "controlling"
    return role


def get_visible_projects(role):
    if role == "project_manager_a":
        return [project for project in PROJECTS if project["project_manager"] == "Projektleitung A"]
    if role == "project_manager_b":
        return [project for project in PROJECTS if project["project_manager"] == "Projektleitung B"]
    return PROJECTS


def get_project_or_404(project_id, role):
    visible_projects = get_visible_projects(role)
    project = next((p for p in visible_projects if p["id"] == project_id), None)
    if project is None:
        abort(404)
    return project


def can_edit_project(role):
    return role in {"project_manager_a", "project_manager_b", "controlling"}


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
    )


@app.route("/projects/<int:project_id>/add-service", methods=["POST"])
def add_service(project_id):
    current_role = request.form.get("role", "controlling")
    project = get_project_or_404(project_id, current_role)

    if not can_edit_project(current_role):
        abort(403)

    new_service = {
        "date": request.form["date"],
        "description": request.form["description"],
        "hours": float(request.form["hours"]),
        "status": request.form["status"],
    }

    project["services"].append(new_service)

    add_audit_entry(
        project,
        "Leistung hinzugefügt",
        f"{new_service['description']} mit {new_service['hours']:.1f} Stunden und Status '{new_service['status']}' wurde erfasst.",
    )

    return redirect(url_for("project_detail", project_id=project_id, role=current_role))


@app.route("/projects/<int:project_id>/services/<int:service_index>/update-status", methods=["POST"])
def update_service_status(project_id, service_index):
    current_role = request.form.get("role", "controlling")
    project = get_project_or_404(project_id, current_role)

    if not can_edit_project(current_role):
        abort(403)

    if service_index < 0 or service_index >= len(project["services"]):
        abort(404)

    service = project["services"][service_index]
    old_status = service["status"]
    new_status = request.form["status"]
    service["status"] = new_status

    add_audit_entry(
        project,
        "Status geändert",
        f"Die Leistung '{service['description']}' wurde von '{old_status}' auf '{new_status}' gesetzt.",
    )

    return redirect(url_for("project_detail", project_id=project_id, role=current_role))


@app.route("/projects/<int:project_id>/invoice-draft")
def invoice_draft(project_id):
    current_role = get_current_role()
    project = get_project_or_404(project_id, current_role)

    approved_services = [
        service for service in project["services"]
        if service["status"] == "freigegeben"
    ]

    total_hours = sum(service["hours"] for service in approved_services)
    total_amount = total_hours * project["hourly_rate"]

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

    approved_services = [
        service for service in project["services"]
        if service["status"] == "freigegeben"
    ]

    total_hours = sum(service["hours"] for service in approved_services)
    total_amount = total_hours * project["hourly_rate"]

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50

    pdf.setTitle(f"Rechnungsentwurf_{project['project_number']}")

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "Rechnungsentwurf")
    y -= 30

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Projekt: {project['name']}")
    y -= 20
    pdf.drawString(50, y, f"Projektnummer: {project['project_number']}")
    y -= 20
    pdf.drawString(50, y, f"Kunde: {project['customer']}")
    y -= 20
    pdf.drawString(50, y, f"Stundensatz: {project['hourly_rate']:.2f} €")
    y -= 30

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Freigegebene Leistungen")
    y -= 25

    pdf.setFont("Helvetica", 10)

    if approved_services:
        for service in approved_services:
            line = (
                f"{service['date']} | {service['description']} | "
                f"{service['hours']:.2f} h | {service['status']}"
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
        pdf.drawString(50, y, f"Entwurfsbetrag: {total_amount:.2f} €")
    else:
        pdf.drawString(50, y, "Für dieses Projekt liegen aktuell keine freigegebenen Leistungen vor.")

    pdf.save()
    buffer.seek(0)

    filename = f"rechnungsentwurf_{project['project_number']}.pdf"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf",
    )


if __name__ == "__main__":
    app.run(debug=True)