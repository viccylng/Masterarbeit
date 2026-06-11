## Aktueller Entwicklungsstand des Prototyps

### Grundlegende Architekturentscheidung
Für den Prototyp wurdfe eine browserbasierte Web-Anwendung aus Basis von Flask gewählt. Die Entscheidung für Flask erfolgt, weil für das Vorhaben zunächst kein komplexes verteiltes System erfoderlich ist, sondern ein schlanker und nachvollziehbarer Prototyp mit klarer Trennung zwischen Anwendungslogik, Templates und Styling. Die Anwendung wurde bewusst inkrementell aufgebaut, um fachliche Kernkompetenzen zunächst mit möglichst geringer technischer Komplexität umzusetzen.

### Umgang mit Daten im frühen Prototypenstadium
Zu Beginn wurde mit Mock-Daten gearbeitet, um die fachliche Logik unabhängig von einer produktiven Datenanbindung entwickeln und testen zu können. Nachdem der Prototyp mehrere Funktionen umfasste, wurden die Beispieldaten aus app.py in eine eigene Datei ausgelagert, um die Anwendungslogik übersichtlicher zu halten und spätere Anpassungen an Evaluationsdaten zu erleichtern.

### Umgesetzte Kernfunktionen
Im aktuellen Stand umfasst der Prototyp folgende Kernfunktionen:

- Projektübersicht als zentrale Einstiegssicht
- Detailansicht projektbezogener Leistungen
- Änderung des Bearbeitungsstatus von Leistungen
- PDF-Export des Rechnunsgentwurfs
- Historie beziehungsweise Audit-Log für relevante Änderungen
- einfache rollenabhängige Sicht- und Bearbeitungslogik

Die Umsetzung erfolgte in dieser Reihenfolge, um zunächst die fachliche Grundlogik und anschließend ergänzende Funktionen wie Nachvollziehbarkeit, Ausgabeformate und Rollensicht zu integrieren.

### Fachliche Designentscheidungen
Eine zentrale fachliche Entscheidung bestand darin, dass Rechnungsentwürfe ausschließlich auf Basis freigegebener Lesitungen gebildet werden. Damit wird im Prototyp bewusst eine einfache, aber nachvollziehbare Statuslogik umgesetzt. Der Rechnungsentwurf stellt somit keine vollständige Rechnungserstellung dar, sondern einen vorbereitenden Bearbeitungsstand für die spätere abrechnungsbezogene Weiterverarbeitung.

Zur Erhöhung der Nachvollziehbarkeit wurde zusätzlich ein einfaches Audit-Log eingeführt. Dieses dokumentiert derzeit insbesondere ds Hinzufügen von Leistungen sowie Änderungen von Leistungsstatus. Damit wird ein zentraler Schwachpunkt der Excel-basierten Lösung adressiert, nämlich die nur begrenzt nachvoollziehbare Bearbeitung projektbezogener Informationen.

### Rollenlogik
Die Rollenlogik wurde bewusst einfach gehalten. Statt eines vollständigen Authentifizierungs- und Rechtesystems wird die aktive Rolle im Prototypen direkt ausgewählt. Dadurch kann die unterschiedliche Sicht auf Projekte und Beabreitungsmöglichkeiten bereits nachvollziehbar demonstriert werden, ohne die technische Komplexität unnötig zu erhöhen. Im aktuellen Stand gilt:

- Projektleistungen sehen nur ihnen zugeordnete Projekte
- Controlling sieht alle Projekte und kann bearbeiten
- Management sieht alle Projekte, aber nur lesbar

Diese Lösung ist als prototypische Annäherung an rollenabhängige Systemnutzung zu verstehen und nciht als produktionsreifes Berechtigungskonzept.

### Frontend-Entscheidungen
Die visuelle Ausgestaltung wurde erst nach Umsetzung der wesentlichen Kernfunktionen gezielt überarbeitet. Damit sollte vermieden werden, frühzeitig Aufwand in Oberflächengestaltung zu investieren, obwohl sich Struktur und Logik des Prototyps noch ändern konnten. Erst nachdem die Kernlogik stabil war, wurde das Frontend vereinheitlicht, insbesondere durch klarere Seitenköpfe, strukturierte Informationskarten, Status-Badges und konsistentere Tabellen- und Formularlayouts.

### Bewusste Abgrenzungen
Mehrere Funktionen wurden im aktuellen Prototypen bewusst nicht umgesetzt, um den Lean-ERP-Charakter zu erhalten und die Komplexität beherrschbar zu halten. Dazu gehören insbesondere:

- keine produktiven Schnittstellen zu DATEV, Timebutler oder anderen Vorsystemen
- kein vollständiges Login- oder Benutzerverwaltungssystem
- keine vollständige Rechnungserstellung mit Buchungslogik
- keine umfassende ERP-Funktionalität ausßerhalb der Projekkontroolle
- zunächst keine persistente Datenhaltung in einer Datenbank

Der Prototyp ist damit bewusst auf diejenigen Funktionen begrenzt, die für Projektkontrolle, Statusnachvollziehbarkeit und Rechnungsentwurf im Anwendungskontext zentral sind.