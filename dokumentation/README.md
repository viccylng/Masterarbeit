# Lean-ERP-Prototyp zur Projektkontrolle

Prototyp zur Masterarbeit „Lean-ERP zur Projektkontrolle: Prototypische Entwicklung und Entscheidungshilfe für den Übergang von Excel zu ERP-Systemen in klei-nen Ingenieurdienstleistungsunternehmen" von
Victoria Langner, Studiengang Information Systems,
Julius-Maximilians-Universität Würzburg, 2026.

Der Prototyp bildet den Kontrollkern der Projektkontrolle in einem kleinen,
projektbasierten Ingenieurdienstleistungsunternehmen ab. Er führt Projekte,
Leistungen und Bestellungen als eigenständige Objekte und berechnet die
Kontrollgrößen zum Zeitpunkt der Anzeige. Der Prototyp diente als Artefakt
der in der Arbeit beschriebenen Evaluation.

## Voraussetzungen

Python 3.12 oder neuer.

## Installation

```
cd prototyp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Unter Windows lautet die Aktivierung .venv\Scripts\activate

## Start

Zuerst den Datenbestand einspielen, dann die Anwendung starten:

```
python seed_a.py
python app.py
```

Die Anwendung ist anschließend unter http://127.0.0.1:5000 erreichbar.
Vor dem erneuten Einspielen muss die Anwendung beendet werden, sonst bleibt
der alte Datenbestand teilweise erhalten.

## Datenvarianten

Für die Evaluation liegen zwei Datenvarianten vor, die sich allein in drei
Projektbudgets und einer Stundenzahl unterscheiden. Aufgabenstellung,
Datenstruktur und Bedienwege sind identisch. Die Trennung verhindert, dass
Teilnehmer im zweiten Durchlauf einen zuvor gelesenen Wert aus der
Erinnerung nennen.

```
python seed_a.py   # Variante A
python seed_b.py   # Variante B
```

Beide Skripte setzen den Datenbestand vollständig zurück.

## Aufbau

```
prototyp/app.py                   Routen, Rollenlogik, Kennzahlen, PDF-Ausgabe
prototyp/models.py                Domänenobjekte und Datenbankschema
prototyp/seed_a.py                Beispieldaten Variante A
prototyp/seed_b.py                Beispieldaten Variante B
prototyp/requirements.txt         Benötigte Pakete
prototyp/templates/               Oberfläche
prototyp/static/                  Stylesheet
dokumentation/entscheidungen.md   Designentscheidungen während der Umsetzung
```

## Hinweise und Grenzen

Es handelt sich um einen Forschungsprototyp, nicht um ein produktives System.

Eine Anmeldung findet nicht statt. Die Rolle wird über eine Auswahl in der
Oberfläche gesetzt und nicht technisch durchgesetzt. Das Audit-Log hält
Zeitpunkt und Art einer Änderung fest, jedoch keinen personenbezogenen
Nachweis. Die Rollenabbildung ist fachlich gemeint und ersetzt keinen
Zugriffsschutz.

Der Rechnungsentwurf ist ein berechneter Arbeitsstand und keine Rechnung.
Die Rechnungsstellung verbleibt im Rechnungswesen.

Alle enthaltenen Projekt-, Kunden- und Lieferantendaten sind erfunden.