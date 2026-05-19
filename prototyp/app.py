from datetime import datetime
from io import BytesIO

from flask import Flask, render_template, abort, request, redirect, url_for, send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from mock_data import PROJECTS

app = Flask(__name__)


def add_audit_entry(project, action, details):
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "action": action,
        "details": details,
    }
    project["audit_log"].insert(0, entry)


@app.route("/")
def index():
    return render_template("index.html", projects=PROJECTS)


@app.route("/projects/<int:project_id>")
def project_detail(project_id):
    project = next((p for p in PROJECTS if p["id"] == project_id), None)
    if project is None:
        abort(404)
    return render_template("project_detail.html", project=project)


@app.route("/projects/<int:project_id>/add-service", methods=["POST"])
def add_service(project_id):
    project = next((p for p in PROJECTS if p["id"] == project_id), None)
    if project is None:
        abort(404)

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

    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/services/<int:service_index>/update-status", methods=["POST"])
def update_service_status(project_id, service_index):
    project = next((p for p in PROJECTS if p["id"] == project_id), None)
    if project is None:
        abort(404)

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

    return redirect(url_for("project_detail", project_id=project_id))


@app.route("/projects/<int:project_id>/invoice-draft")
def invoice_draft(project_id):
    project = next((p for p in PROJECTS if p["id"] == project_id), None)
    if project is None:
        abort(404)

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
    )

@app.route("/projects/<int:project_id>/invoice-draft/pdf")
def invoice_draft_pdf(project_id):
    project = next((p for p in PROJECTS if p["id"] == project_id), None)
    if project is None:
        abort(404)

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