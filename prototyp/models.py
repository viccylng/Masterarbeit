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

    # --- Berechnete Kennzahlen (Soll-Ist-Sicht auf Projektebene) ---
    # Abgeleitete Groessen werden nicht gespeichert, sondern bei jeder Abfrage
    # aus den zugrunde liegenden Leistungen berechnet. Damit koennen Budget,
    # Verbrauch und Restbudget nicht auseinanderlaufen.

    @property
    def consumed(self):
        """Verbrauch (Ist): gepruefte und freigegebene Leistungen, in Euro."""
        relevant = [s for s in self.services if s.status in ("geprüft", "freigegeben")]
        return sum(s.hours for s in relevant) * self.hourly_rate

    @property
    def invoiced(self):
        """Verrechnet (fakturiert): nur freigegebene Leistungen, in Euro."""
        relevant = [s for s in self.services if s.status == "freigegeben"]
        return sum(s.hours for s in relevant) * self.hourly_rate

    @property
    def remaining_budget(self):
        """Restbudget (Soll minus Ist): Budget abzueglich Verbrauch, in Euro."""
        return self.budget - self.consumed

    @property
    def budget_consumption_percent(self):
        """Budgetauslastung in Prozent. 0.0, wenn kein Budget hinterlegt ist."""
        if self.budget == 0:
            return 0.0
        return self.consumed / self.budget * 100

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