from flask import Flask, render_template, abort, request, redirect, url_for

app = Flask(__name__)

PROJECTS = [
    {
        "id": 1,
        "project_number": "P-001",
        "name": "Projekt A",
        "customer": "Kundenprojekt 1",
        "status": "In Bearbeitung",
        "budget": 50000.00,
        "invoiced": 15000.00,
        "remaining_budget": 35000.00,
        "project_manager": "Projektleitung A",
        "services": [
            {
                "date": "2026-05-01",
                "description": "Analyse",
                "hours": 8,
                "status": "freigegeben"
            },
            {
                "date": "2026-05-03",
                "description": "Konzeption",
                "hours": 6,
                "status": "erfasst"
            },
        ],
    },
    {
        "id": 2,
        "project_number": "P-002",
        "name": "Projekt B",
        "customer": "Kundenprojekt 2",
        "status": "Angebotsphase",
        "budget": 30000.00,
        "invoiced": 0.00,
        "remaining_budget": 30000.00,
        "project_manager": "Projektleitung B",
        "services": [
            {
                "date": "2026-05-02",
                "description": "Prüfung",
                "hours": 4,
                "status": "geprüft"
            },
        ],
    },
]


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

    return redirect(url_for("project_detail", project_id=project_id))

@app.route("/projects/<int:project_id>/services/<int:service_index>/update-status", methods=["POST"])
def update_service_status(project_id, service_index):
    project = next((p for p in PROJECTS if p["id"] == project_id), None)
    if project is None:
        abort(404)

    if service_index < 0 or service_index >= len(project["services"]):
        abort(404)

    new_status = request.form["status"]
    project["services"][service_index]["status"] = new_status

    return redirect(url_for("project_detail", project_id=project_id))

if __name__ == "__main__":
    app.run(debug=True)
