from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

# Zentrale Datenbank-Instanz. Wird in app.py mit der Flask-App verbunden.
db = SQLAlchemy()


class Project(db.Model):
    """Zentrale Bezugseinheit der Projektkontrolle.

    Entspricht im Domaenenmodell dem Objekt 'Projekt', an das Leistungen,
    Audit-Eintraege und die kaufmaennischen Kennzahlen gebunden sind.
    """

    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    project_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    customer = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), nullable=False, default="In Bearbeitung")
    budget = db.Column(db.Float, nullable=False, default=0.0)
    invoiced = db.Column(db.Float, nullable=False, default=0.0)
    remaining_budget = db.Column(db.Float, nullable=False, default=0.0)
    project_manager = db.Column(db.String(100), nullable=False)
    hourly_rate = db.Column(db.Float, nullable=False, default=0.0)

    # 1:n - ein Projekt hat mehrere Leistungen und Audit-Eintraege.
    # cascade sorgt dafuer, dass abhaengige Objekte mitgeloescht werden.
    services = db.relationship(
        "Service",
        backref="project",
        cascade="all, delete-orphan",
        order_by="Service.id",
    )
    audit_log = db.relationship(
        "AuditEntry",
        backref="project",
        cascade="all, delete-orphan",
        order_by="AuditEntry.id.desc()",
    )


class Service(db.Model):
    """Projektbezogene Leistung mit dreistufigem Freigabe-Status.

    Status-Werte: 'erfasst' -> 'geprueft' -> 'freigegeben'.
    Nur freigegebene Leistungen flie\u00dfen in den Rechnungsentwurf ein.
    """

    __tablename__ = "services"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    hours = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(20), nullable=False, default="erfasst")


class AuditEntry(db.Model):
    """Eintrag im Audit-Log. Dokumentiert Aenderungen an einem Projekt."""

    __tablename__ = "audit_entries"

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    timestamp = db.Column(db.String(20), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.String(500), nullable=False)

    @staticmethod
    def create(project, action, details):
        """Legt einen neuen Audit-Eintrag fuer das Projekt an."""
        entry = AuditEntry(
            project=project,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            action=action,
            details=details,
        )
        db.session.add(entry)
        return entry