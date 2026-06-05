"""Initialisierungsskript fuer die Datenbank.

Legt die Tabellen an und spielt die Beispielprojekte ein. Bei jedem Aufruf
wird der Datenbestand zurueckgesetzt, sodass fuer die Evaluation ein
einheitlicher und reproduzierbarer Ausgangszustand vorliegt.

Aufruf:  python seed.py
"""

from app import app
from models import db, Project, Service, AuditEntry

# Beispielprojekte als reine Datenstruktur. Diese Werte werden in die
# Datenbank geschrieben und bilden den Ausgangszustand der Evaluation.
SEED_PROJECTS = [
    {
        "project_number": "P-001",
        "name": "Projekt A",
        "customer": "Kundenprojekt 1",
        "status": "In Bearbeitung",
        "budget": 50000.00,
        "invoiced": 15000.00,
        "remaining_budget": 35000.00,
        "project_manager": "Projektleitung A",
        "hourly_rate": 120.00,
        "services": [
            {"date": "2026-05-01", "description": "Analyse", "hours": 8, "status": "freigegeben"},
            {"date": "2026-05-03", "description": "Konzeption", "hours": 6, "status": "erfasst"},
        ],
        "audit_log": [
            {
                "timestamp": "2026-05-15 10:00",
                "action": "Projekt angelegt",
                "details": "Projekt A wurde als Beispielprojekt im Prototyp angelegt.",
            }
        ],
    },
    {
        "project_number": "P-002",
        "name": "Projekt B",
        "customer": "Kundenprojekt 2",
        "status": "Angebotsphase",
        "budget": 30000.00,
        "invoiced": 0.00,
        "remaining_budget": 30000.00,
        "project_manager": "Projektleitung B",
        "hourly_rate": 95.00,
        "services": [
            {"date": "2026-05-02", "description": "Prüfung", "hours": 4, "status": "geprueft"},
        ],
        "audit_log": [
            {
                "timestamp": "2026-05-15 10:05",
                "action": "Projekt angelegt",
                "details": "Projekt B wurde als Beispielprojekt im Prototyp angelegt.",
            }
        ],
    },
]


def seed_database():
    with app.app_context():
        # Sauberer Ausgangszustand: bestehende Tabellen verwerfen und neu anlegen.
        db.drop_all()
        db.create_all()

        for project_data in SEED_PROJECTS:
            project = Project(
                project_number=project_data["project_number"],
                name=project_data["name"],
                customer=project_data["customer"],
                status=project_data["status"],
                budget=project_data["budget"],
                invoiced=project_data["invoiced"],
                remaining_budget=project_data["remaining_budget"],
                project_manager=project_data["project_manager"],
                hourly_rate=project_data["hourly_rate"],
            )

            for service_data in project_data["services"]:
                project.services.append(Service(**service_data))

            for audit_data in project_data["audit_log"]:
                project.audit_log.append(AuditEntry(**audit_data))

            db.session.add(project)

        db.session.commit()
        print(f"Datenbank initialisiert. {len(SEED_PROJECTS)} Projekte eingespielt.")


if __name__ == "__main__":
    seed_database()