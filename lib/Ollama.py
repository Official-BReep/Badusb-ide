import json
import urllib.request

from PyQt6.QtCore import QThread, pyqtSignal


class OllamaWorker(QThread):
    finished_text = pyqtSignal(str, str)
    def __init__(self, base_url, model, prompt, context):
        super().__init__()
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.prompt = prompt
        self.context = context
    def run(self):
        try:
            payload = {
                "model": self.model,
                "stream": False,
                "messages": [
                    {"role": "system", "content": "Du bist ein lokaler Programmierassistent in einer Flipper Zero IDE. Hilf bei JavaScript/mJS und BadUSB/DuckyScript. Erkläre Unsicherheiten und erfinde keine API-Funktionen. Gib bei Code-Aufgaben möglichst den vollständigen Code in einem Codeblock zurück."},
                    {"role": "user", "content": self.prompt + ("\n\nAktueller Editorinhalt:\n```\n" + self.context + "\n```" if self.context else "")}
                ]
            }
            req = urllib.request.Request(self.base_url + '/api/chat', data=json.dumps(payload).encode('utf-8'), headers={'Content-Type':'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=180) as response:
                data = json.loads(response.read().decode('utf-8'))
            self.finished_text.emit(data.get('message', {}).get('content', '(Leere Antwort)'), '')
        except Exception as ex:
            self.finished_text.emit('', f'{type(ex).__name__}: {ex}')