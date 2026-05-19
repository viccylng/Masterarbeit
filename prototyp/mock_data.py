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
        "hourly_rate": 120.00,
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
        "audit_log": [
            {
                "timestamp": "2026-05-15 10:00",
                "action": "Projekt angelegt",
                "details": "Projekt A wurde als Beispielprojekt im Prototyp angelegt."
            }
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
        "hourly_rate": 95.00,
        "services": [
            {
                "date": "2026-05-02",
                "description": "Prüfung",
                "hours": 4,
                "status": "geprüft"
            },
        ],
        "audit_log": [
            {
                "timestamp": "2026-05-15 10:05",
                "action": "Projekt angelegt",
                "details": "Projekt B wurde als Beispielprojekt im Prototyp angelegt."
            }
        ],
    },
]