"""Initialisierungsskript für die Datenbank.

Legt die Tabellen an und spielt die Beispielprojekte ein. Bei jedem Aufruf
wird der Datenbestand zurueckgesetzt, sodass für die Evaluation ein
einheitlicher und reproduzierbarer Ausgangszustand vorliegt.

Aufruf:  python seed.py
"""

from app import app
from models import db, Project, Service, AuditEntry, Order

# Beispielprojekte als reine Datenstruktur. Diese Werte werden in die
# Datenbank geschrieben und bilden den Ausgangszustand der Evaluation.
SEED_PROJECTS = [
    {
        "project_number": "P-001",
        "name": "Umrichter Gen3",
        "customer": "Kunde 1",
        "status": "In Bearbeitung",
        "budget": 50000.00,
        "project_manager": "Projektleitung A",
        "hourly_rate": 120.00,
        "customer_order_number": "4500018231",
        "services": [
            {"date": "2026-05-01", "description": "Anforderungsanalyse", "hours": 80, "status": "freigegeben"},
            {"date": "2026-05-03", "description": "Reglerkonzept", "hours": 60, "status": "geprüft"},
            {"date": "2026-05-08", "description": "Detailauslegung Leistungsteil", "hours": 40, "status": "erfasst"},
        ],
        "orders": [
            {"date": "2026-05-04", "description": "Messtechnik-Sensoren, 5 Stück", "supplier": "Lieferant 1", "amount": 3200.00, "status": "bezahlt"},
            {"date": "2026-05-09", "description": "Prüflingsadapter, 2 Stück", "supplier": "Lieferant 2", "amount": 1800.00, "status": "offen"},
        ],
        "audit_log": [
            {
                "timestamp": "2026-05-15 10:00",
                "action": "Projekt angelegt",
                "details": "Projekt Umrichter Gen3 wurde als Beispielprojekt im Prototyp angelegt.",
            }
        ],
    },
    {
        "project_number": "P-002",
        "name": "Support Serienanlauf HW",
        "customer": "Kunde 2",
        "status": "Angebot",
        "budget": 30000.00,
        "project_manager": "Projektleitung B",
        "hourly_rate": 95.00,
        "services": [
            {"date": "2026-05-02", "description": "Prüfung", "hours": 40, "status": "geprüft"},
        ],
        "orders": [
            {"date": "2026-05-06", "description": "Kabelsatz HV, 1 Satz", "supplier": "Lieferant 3", "amount": 2500.00, "status": "offen"},
        ],
        "audit_log": [
            {
                "timestamp": "2026-05-15 10:05",
                "action": "Projekt angelegt",
                "details": "Support Serienanlauf HW wurde als Beispielprojekt im Prototyp angelegt.",
            }
        ],
    },
    {
        "project_number": "P-003",
        "name": "E-Maschine 800V",
        "customer": "Kunde 3",
        "status": "In Bearbeitung",
        "budget": 40000.00,
        "project_manager": "Projektleitung A",
        "hourly_rate": 110.00,
        "customer_order_number": "4500019476",
        "services": [
            {"date": "2026-05-05", "description": "Systemarchitektur", "hours": 70, "status": "freigegeben"},
            {"date": "2026-05-07", "description": "Elektromagnetische Auslegung", "hours": 55, "status": "geprüft"},
            {"date": "2026-05-12", "description": "Mechanik-Konstruktion", "hours": 45, "status": "geprüft"},
            {"date": "2026-05-14", "description": "Testvorbereitung", "hours": 30, "status": "erfasst"},
        ],
        "orders": [
            {"date": "2026-05-08", "description": "Leistungselektronik-Module, 3 Stück", "supplier": "Lieferant 4", "amount": 4200.00, "status": "bezahlt"},
            {"date": "2026-05-13", "description": "Wicklungsmaterial, Sonderposten", "supplier": "Lieferant 5", "amount": 2600.00, "status": "offen"},
        ],
        "audit_log": [
            {
                "timestamp": "2026-05-15 10:10",
                "action": "Projekt angelegt",
                "details": "E-Maschine 800V wurde als Beispielprojekt im Prototyp angelegt.",
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
                project_manager=project_data["project_manager"],
                hourly_rate=project_data["hourly_rate"],
                customer_order_number=project_data.get("customer_order_number"),
            )

            for service_data in project_data["services"]:
                project.services.append(Service(**service_data))

            for order_data in project_data["orders"]:
                project.orders.append(Order(**order_data))

            for audit_data in project_data["audit_log"]:
                project.audit_log.append(AuditEntry(**audit_data))

            db.session.add(project)

        db.session.commit()
        print(f"Datenbank initialisiert. {len(SEED_PROJECTS)} Projekte eingespielt.")


if __name__ == "__main__":
    seed_database()