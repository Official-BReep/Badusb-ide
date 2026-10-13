# BadUSB IDE – Flipper Zero Payload Editor

Eine desktopbasierte IDE auf Basis von **Python und PyQt6** zum Schreiben, Bearbeiten und Prüfen von BadUSB-Payloads sowie JavaScript-/mJS-Skripten für den Flipper Zero. Die Anwendung bietet einen Code-Editor, Befehlsreferenzen, Dateiexplorer, optionale lokale KI-Unterstützung über Ollama und ein Plugin-System.

> **Hinweis:** Dieses Projekt ist ein Community-/Lernwerkzeug. Prüfe Payloads vor dem Einsatz und verwende sie ausschließlich auf Geräten und Systemen, für die du eine ausdrückliche Berechtigung hast.

## Funktionen

- **Code-Editor mit Tabs** für mehrere geöffnete Dokumente
- Syntaxhervorhebung für BadUSB/DuckyScript und JavaScript
- Zeilennummern, optionale Autovervollständigung und Live-Prüfung
- Befehls-Palette und integrierte Befehlsreferenzen
- Payload-Vorschau und grobe Laufzeitschätzung
- Lokaler Dateiexplorer und separater Flipper-Dateiexplorer
- Einstellungsdialog für Darstellung und Editorverhalten
- Verschiebbare und andockbare Bereiche, darunter Befehle, Output/Prüfung, Dateiexplorer und lokale KI
- Speichern und Wiederherstellen der Fenstergeometrie und Dock-Anordnung
- Optionale Verbindung zum Flipper Zero über serielle Schnittstelle, sofern Gerät, Firmware/CLI und Verbindung dies unterstützen
- Plugin-Verwaltung mit Aktivieren, Deaktivieren, Plugin-Einstellungen und Löschen
- Git-basierter Plugin-Marktplatz zum Klonen und Aktualisieren von Repositories
- Optionale lokale KI-Anbindung an einen Ollama-Server

Die verfügbaren Aktionen können je nach Betriebssystem, angeschlossenem Flipper, installierten optionalen Paketen und Ollama-Konfiguration variieren.

## Voraussetzungen

- Python **3.10 oder neuer** empfohlen
- PyQt6
- Optional: `pyserial` für serielle Verbindungsfunktionen
- Optional: Git für den Plugin-Marktplatz
- Optional: Ollama und ein lokal verfügbares Modell für KI-Funktionen

## Installation

### 1. Projekt herunterladen

Lade die Python-Datei des Projekts herunter oder klone das Repository, falls du es aus einem Git-Repository beziehst. Wechsle anschließend im Terminal in den Ordner der Datei.

### 2. Virtuelle Umgebung erstellen (empfohlen)

**Windows (PowerShell):**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Falls PowerShell die Aktivierung blockiert, kannst du die Umgebung auch direkt über `.venv\Scripts\python.exe` verwenden.

**Linux/macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 3. Abhängigkeiten installieren

```bash
python -m pip install PyQt6
```

Für serielle Flipper-Funktionen zusätzlich:

```bash
python -m pip install pyserial
```

Git und Ollama sind eigenständige optionale Programme und werden nicht über diesen Python-Befehl installiert.

### 4. Anwendung starten

Ersetze `badusb_ide_pyqt6_layout_restore.py` gegebenenfalls durch den Namen deiner heruntergeladenen Projektdatei.

```bash
python badusb_ide_pyqt6_layout_restore.py
```

Unter Windows kannst du alternativ `py badusb_ide_pyqt6_layout_restore.py` ausführen.

## Grundlegende Verwendung

1. Starte die Anwendung.
2. Erstelle einen neuen Tab oder öffne eine vorhandene Datei.
3. Wähle den passenden Arbeitsmodus für BadUSB oder JavaScript/mJS, sofern die entsprechende Umschaltfunktion in der Oberfläche verfügbar ist.
4. Schreibe oder bearbeite dein Skript und nutze die Befehlsreferenz sowie die Prüfung als Hilfe.
5. Speichere die Datei lokal.
6. Verbinde den Flipper nur dann, wenn du die Übertragungsfunktionen tatsächlich verwenden möchtest und die Verbindung eingerichtet ist.
7. Teste Skripte zunächst in einer kontrollierten Umgebung.

Die IDE ersetzt weder die offizielle Flipper-Dokumentation noch die Prüfung auf dem tatsächlichen Zielgerät. Nicht jeder Befehl oder jede mJS-Funktion wird zwangsläufig vollständig simuliert oder statisch erkannt.

## Layout und Einstellungen

Die Anwendung speichert Einstellungen in einer JSON-Datei im Home-Verzeichnis:

```text
~/.badusb_ide_pyqt6.json
```

Unter Windows entspricht `~` normalerweise deinem Benutzerprofil, beispielsweise `C:\Users\<Benutzername>`.

Dort werden unter anderem Darstellungs- und Editoroptionen sowie – sofern aktiviert – Fenstergröße, Fenstergeometrie und Dock-Anordnung abgelegt. Die Layout-Wiederherstellung funktioniert am besten, wenn beim Start dieselben integrierten Panels und dieselben Plugins verfügbar sind wie beim letzten Schließen.

Wenn die Anordnung beschädigt ist oder sich die Fensterposition nicht mehr eignet, schließe die IDE und sichere oder benenne die Einstellungsdatei um. Beim nächsten Start legt die Anwendung neue Einstellungen an. Dadurch werden auch andere gespeicherte Einstellungen zurückgesetzt.

## Lokale KI mit Ollama (optional)

Die IDE kann mit einem Ollama-Server kommunizieren. Installiere und starte Ollama separat und lade ein Modell, das zu deinem Rechner passt. Trage in der IDE die URL des Servers und den Modellnamen ein.

Typische lokale URL:

```text
http://localhost:11434
```

Wenn Ollama auf einem anderen Rechner im eigenen Netzwerk läuft, muss Ollama dort so konfiguriert sein, dass Verbindungen aus dem Netzwerk erlaubt sind. Verwende die Funktion nur in vertrauenswürdigen Netzwerken und setze keine öffentliche Freigabe ohne geeignete Absicherung auf.

Die KI-Funktion ist optional; der Editor kann auch ohne Ollama verwendet werden.

## Plugins

### Plugin-Verzeichnis

Die IDE verwaltet Plugins im Benutzerverzeichnis:

```text
~/.badusb_ide_addons/
```

Git-Repositories des Marktplatzes werden unterhalb des Marketplace-Verzeichnisses dieses Plugin-Ordners abgelegt. Python-Dateien, die der Plugin-Manager findet, können dort zur Aktivierung angeboten werden.

### Minimales Plugin

Ein Plugin muss mindestens eine Funktion `register(ide)` bereitstellen. `configure(ide)` oder `open_settings(ide)` ist optional. Für das Aufräumen beim Deaktivieren kann `unregister(ide)` bereitgestellt werden.

```python
ADDON_NAME = "Beispiel-Plugin"
ADDON_VERSION = "1.0.0"

def register(ide):
    # Beispiel: Aktion in einem vorhandenen IDE-Menü registrieren.
    ide.register_menu_action(
        "Beispielaktion",
        lambda: print("Plugin-Aktion ausgeführt"),
        menu="Erweiterungen",
    )

def configure(ide):
    # Optional: Einstellungsdialog anzeigen.
    pass

def unregister(ide):
    # Optional: eigene Timer, Threads oder Ressourcen beenden.
    pass
```

Die genaue Plugin-API richtet sich nach der verwendeten IDE-Version. Nutze für Menüs, Toolbar-Schaltflächen und Panels möglichst die Registrierungsfunktionen der IDE, statt Qt-Elemente direkt anzulegen. Prüfe die im Quellcode vorhandenen Methoden wie `register_menu`, `register_menu_action`, `register_toolbar_button` und `register_panel`, bevor du ein Plugin entwickelst.

### Plugin-Sicherheit

**Python-Plugins führen beliebigen Python-Code mit den Rechten des laufenden Benutzerkontos aus.** Ein Plugin kann daher unter anderem Dateien lesen oder verändern und Netzwerkverbindungen aufbauen.

- Aktiviere nur Plugins aus Quellen, denen du vertraust.
- Prüfe den Quellcode vor dem Aktivieren.
- Ein Git-Repository zu klonen bedeutet nicht, dass dessen Inhalt sicher ist.
- Installiere keine Plugins mit unnötigen Berechtigungen.

## Flipper Zero und serielle Verbindung

Serielle Funktionen benötigen gegebenenfalls `pyserial`, einen passenden USB-Anschluss und einen vom Betriebssystem erkannten seriellen Port. Ob Dateiübertragung und Terminalbefehle funktionieren, hängt unter anderem von der verfügbaren Flipper-CLI bzw. Firmware und der Verbindung ab.

Die IDE kann keine erfolgreiche Übertragung garantieren, wenn das Gerät nicht verbunden ist oder die benötigten Befehle nicht unterstützt werden. Prüfe Zielpfade und überschreibe keine Dateien, die du behalten möchtest.

## Fehlerbehebung

### `ModuleNotFoundError: No module named 'PyQt6'`

Installiere PyQt6 in genau der Python-Umgebung, mit der du die Anwendung startest:

```bash
python -m pip install PyQt6
```

### Serielle Funktionen sind nicht verfügbar

```bash
python -m pip install pyserial
```

Prüfe anschließend den Geräteanschluss, den seriellen Port und die erforderlichen Betriebssystemberechtigungen.

### Plugin wird nicht geladen

- Kontrolliere, ob die Datei im Plugin-Verzeichnis liegt und gültiges Python enthält.
- Stelle sicher, dass sie `register(ide)` definiert.
- Lies die Fehlermeldung im Plugin-Manager.
- Prüfe, ob das Plugin Methoden aufruft, die in deiner IDE-Version tatsächlich existieren.
- Aktiviere nur Plugins, deren Code du geprüft hast.

### Git-Marktplatz funktioniert nicht

- Prüfe, ob Git installiert und im `PATH` verfügbar ist.
- Kontrolliere die Repository-URL und deine Netzwerk-/SSH-Berechtigungen.
- Ein Update bestehender Repositories verwendet `git pull --ff-only`; lokale Änderungen, die einen Fast-Forward verhindern, müssen manuell geklärt werden.

### Ollama ist nicht erreichbar

- Prüfe, ob der Ollama-Dienst läuft.
- Kontrolliere die Server-URL und den Modellnamen.
- Bei einem anderen Rechner müssen Netzwerkzugriff und Firewallregeln passend konfiguriert sein.

## Sicherheit und verantwortungsvolle Nutzung

BadUSB-Payloads können Tastatureingaben automatisieren und dadurch auf angeschlossenen Systemen Aktionen auslösen. Verwende sie ausschließlich auf eigenen Geräten oder mit ausdrücklicher Genehmigung. Prüfe den Inhalt jeder Payload, bevor du sie ausführst oder auf ein Gerät überträgst. Speichere keine Zugangsdaten oder vertraulichen Informationen in Beispiel-Payloads oder Plugins.

## Entwicklung und Beiträge

- Halte Plugins möglichst unabhängig und dokumentiere ihre Voraussetzungen.
- Beende Timer und Threads beim Deaktivieren eines Plugins.
- Behandle Fehler bei optionalen Funktionen so, dass der Editor weiter nutzbar bleibt.
- Teste Änderungen in einer separaten Python-Umgebung.
- Stelle vor einem Pull Request sicher, dass die Anwendung zumindest syntaktisch geprüft ist.

## Lizenz

In der bereitgestellten Projektdatei ist keine eindeutige Lizenzangabe dokumentiert. Ergänze eine `LICENSE`-Datei, bevor du anderen eine verbindliche Nutzung, Weitergabe oder Änderung unter bestimmten Lizenzbedingungen zusicherst.
"""