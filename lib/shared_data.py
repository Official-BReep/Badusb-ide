"""Shared configuration data used by ScriptMonkey's app and editor widgets."""



COMMANDS = {'REM': 'Kommentarzeile',
 'DELAY': 'Warten in Millisekunden, z. B. DELAY 500',
 'STRING': 'Text tippen, z. B. STRING Hallo',
 'STRINGLN': 'Text tippen + Enter',
 'ALTSTRING': 'Text per Alt+NumPad',
 'GUI': 'Windows/Cmd + Taste, z. B. GUI r',
 'CTRL': 'Strg-Kombination, z. B. CTRL SHIFT ESC',
 'ALT': 'Alt-Kombination',
 'SHIFT': 'Shift-Kombination',
 'ENTER': 'Enter-Taste',
 'TAB': 'Tab-Taste',
 'SPACE': 'Leerzeichen',
 'ESC': 'Escape',
 'BACKSPACE': 'Rücktaste',
 'DELETE': 'Entf',
 'PRINTSCREEN': 'Screenshot',
 'CAPSLOCK': 'Feststelltaste',
 'DOWN': 'Pfeil runter',
 'UP': 'Pfeil hoch',
 'LEFT': 'Pfeil links',
 'RIGHT': 'Pfeil rechts',
 'HOME': 'Pos1',
 'END': 'Ende',
 'INSERT': 'Einfg',
 'PAGEUP': 'Bild hoch',
 'PAGEDOWN': 'Bild runter',
 'REPEAT': 'Befehl wiederholen, z. B. REPEAT 5 TAB',
 'WAIT_FOR_BUTTON_PRESS': 'Auf Flipper-Button warten',
 'HOLD': 'Nächsten Befehl für Millisekunden halten',
 'ALTCHAR': 'Alt+NumPad-Zeichen'}
GROUPS = {'Text': ['STRING', 'STRINGLN', 'ALTSTRING', 'ALTCHAR'],
 'Tastenkombinationen': ['GUI', 'CTRL', 'ALT', 'SHIFT'],
 'Tasten': ['ENTER',
            'TAB',
            'SPACE',
            'ESC',
            'BACKSPACE',
            'DELETE',
            'CAPSLOCK',
            'PRINTSCREEN'],
 'Navigation': ['DOWN',
                'UP',
                'LEFT',
                'RIGHT',
                'HOME',
                'END',
                'INSERT',
                'PAGEUP',
                'PAGEDOWN'],
 'Ablaufsteuerung': ['DELAY', 'HOLD', 'REPEAT', 'WAIT_FOR_BUTTON_PRESS'],
 'Sonstiges': ['REM']}
EXAMPLES = {'Hello Notepad': 'ID Hello_Ducky\n'
                  '\n'
                  'REM Öffnet den Ausführen-Dialog und startet Notepad\n'
                  'GUI r\n'
                  'DELAY 500\n'
                  'STRING notepad\n'
                  'ENTER\n'
                  'DELAY 1000\n'
                  'STRINGLN Hallo vom Flipper Zero!\n',
 'Terminal öffnen': 'ID Open_Terminal\n'
                    '\n'
                    'REM Öffnet Windows Terminal (abhängig von Windows-Version)\n'
                    'GUI r\n'
                    'DELAY 500\n'
                    'STRING wt\n'
                    'ENTER\n'
                    'DELAY 1200\n'
                    'STRINGLN whoami\n',
 'Warten auf Button': 'ID Wait_For_Button\n'
                      '\n'
                      'REM Startet erst nach Bestätigung am Flipper\n'
                      'WAIT_FOR_BUTTON_PRESS\n'
                      'DELAY 200\n'
                      'GUI r\n'
                      'DELAY 500\n'
                      'STRINGLN notepad\n'}
JS_GLOBALS = {'let': 'Variable deklarieren',
 'if': 'Bedingung',
 'else': 'Alternativzweig',
 'for': 'Schleife',
 'while': 'Schleife',
 'function': 'Funktion definieren',
 'return': 'Wert zurückgeben',
 'true': 'Boolescher Wert',
 'false': 'Boolescher Wert',
 'null': 'Nullwert',
 'undefined': 'Nicht definierter Wert',
 'print': 'Text in die JS-Konsole ausgeben',
 'delay': 'Ausführung anhalten',
 'require': 'Flipper-JS-Modul laden',
 'load': 'Weitere JS-Datei laden',
 'JSON': 'JSON-Hilfsfunktionen',
 'Math': 'Mathematikfunktionen',
 'parseInt': 'Ganzzahl parsen',
 'parseFloat': 'Fließkommazahl parsen',
 'checkSdkFeatures': 'Firmware-Features prüfen',
 'doesSdkSupport': 'Firmware-Feature abfragen'}
JS_MODULES = {'badusb': 'USB-HID / Tastatureingabe',
 'storage': 'Dateisystem',
 'event_loop': 'Ereignisgesteuerte Abläufe',
 'flipper': 'Geräteinformationen',
 'gpio': 'GPIO-Pins',
 'gui': 'Flipper-GUI',
 'math': 'Mathematik',
 'notification': 'LED / Ton / Vibration',
 'serial': 'UART / serielle Schnittstelle',
 'i2c': 'I2C (Momentum)',
 'spi': 'SPI (Momentum)',
 'subghz': 'Sub-GHz (Momentum)',
 'blebeacon': 'BLE-Beacons (Momentum)',
 'vgm': 'Video Game Module (Momentum)',
 'widget': 'GUI-Widgets (Momentum)',
 'usbdisk': 'Virtuelles USB-Laufwerk (Momentum)'}
JS_METHODS = {'badusb': {'setup': 'USB-HID initialisieren',
            'isConnected': 'USB-Verbindung prüfen',
            'print': 'Text tippen',
            'println': 'Text tippen und Enter senden',
            'press': 'Taste(n) drücken',
            'hold': 'Taste(n) halten',
            'release': 'Tasten loslassen',
            'quit': 'USB-HID freigeben'},
 'storage': {'exists': 'Pfad prüfen',
             'readDirectory': 'Verzeichnisinhalt lesen',
             'openFile': 'Datei öffnen',
             'read': 'Dateiinhalt lesen',
             'write': 'Dateiinhalt schreiben',
             'mkdir': 'Verzeichnis erstellen',
             'copy': 'Datei kopieren',
             'rename': 'Datei umbenennen',
             'remove': 'Datei entfernen',
             'stat': 'Dateiinformationen abrufen'},
 'event_loop': {'subscribe': 'Ereignis abonnieren',
                'run': 'Event Loop starten',
                'stop': 'Event Loop stoppen'},
 'notification': {'success': 'Erfolg signalisieren',
                  'error': 'Fehler signalisieren',
                  'message': 'Benachrichtigung anzeigen'},
 'flipper': {'getName': 'Flipper-Namen abrufen',
             'getBatteryLevel': 'Akkustand abrufen',
             'firmwareVendor': 'Firmware-Anbieter ermitteln'},
 'gpio': {'get': 'Pinwert lesen',
          'set': 'Pinwert setzen',
          'init': 'GPIO initialisieren'},
 'gui': {'dialog': 'Dialog anzeigen',
         'textBox': 'Text anzeigen',
         'submenu': 'Menü anzeigen',
         'textInput': 'Texteingabe anzeigen'},
 'serial': {'setup': 'Serielle Schnittstelle initialisieren',
            'write': 'Daten senden',
            'read': 'Daten empfangen'},
 'blebeacon': {'isActive': 'Beacon-Status prüfen',
               'setConfig': 'Beacon konfigurieren',
               'setData': 'Paketdaten setzen',
               'start': 'Beacon starten',
               'stop': 'Beacon stoppen',
               'keepAlive': 'Beacon weiterlaufen lassen'},
 'subghz': {'setup': 'Sub-GHz initialisieren',
            'getFrequency': 'Frequenz abfragen',
            'getRssi': 'Signalstärke abfragen',
            'getState': 'Funkzustand abfragen',
            'setFrequency': 'Frequenz einstellen',
            'setIdle': 'IDLE-Modus',
            'setRx': 'Empfang aktivieren',
            'transmitFile': 'Unterstützte Datei senden'},
 'usbdisk': {'createImage': 'Laufwerksabbild erstellen',
             'start': 'USB-Laufwerk bereitstellen',
             'stop': 'Laufwerk trennen'}}

THEMES = {
"Flipper Amber": dict(bg="#12151c", panel="#1a1f29", hover="#242b38", editor="#0e1118", fg="#e8eaf0", muted="#7d8698", accent="#ffb347", key="#6fc3ff", comment="#687386", string="#a8d08d", btn="#2a3242", error="#48232a"),
"Midnight Blue": dict(bg="#101722", panel="#172334", hover="#23354b", editor="#0a111c", fg="#e5efff", muted="#8b9db6", accent="#66c7ff", key="#a6e3a1", comment="#63758d", string="#f9e2af", btn="#25364b", error="#43252d"),
"Nord": dict(bg="#2e3440", panel="#3b4252", hover="#434c5e", editor="#242933", fg="#eceff4", muted="#aab4c5", accent="#88c0d0", key="#81a1c1", comment="#7b879a", string="#a3be8c", btn="#434c5e", error="#4c2f3a"),
"Light": dict(bg="#e9edf2", panel="#dce3eb", hover="#cbd6e2", editor="#ffffff", fg="#202733", muted="#5d6878", accent="#b35b00", key="#006bb6", comment="#657080", string="#357a38", btn="#cbd6e2", error="#ffe1e1"),
"OLED Black": dict(bg="#000000", panel="#090909", hover="#1c1c1c", editor="#000000", fg="#f4f4f4", muted="#929292", accent="#ff9d00", key="#5ecbff", comment="#777777", string="#9be28f", btn="#222222", error="#431b22")
}
STANDALONE = {"ENTER","TAB","SPACE","ESC","PRINTSCREEN","CAPSLOCK","BACKSPACE","DELETE","WAIT_FOR_BUTTON_PRESS","DOWN","UP","LEFT","RIGHT","HOME","END","INSERT","PAGEUP","PAGEDOWN"}
KEYS = {"ENTER","TAB","SPACE","ESC","BACKSPACE","DELETE","PRINTSCREEN","CAPSLOCK","DOWN","UP","LEFT","RIGHT","HOME","END","INSERT","PAGEUP","PAGEDOWN","NUMLOCK", *[chr(i) for i in range(65,91)], *[str(i) for i in range(10)]}
