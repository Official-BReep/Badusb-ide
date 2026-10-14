import os
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class GitManagerDialog(QDialog):
    """GUI for Git repositories; private-repository auth uses Git Credential Manager or SSH."""
    def __init__(self, ide):
        super().__init__(ide)
        self.ide = ide
        self.repo_path = None
        self.setWindowTitle("Git · Repository-Verwaltung")
        self.resize(760, 590)
        root = QVBoxLayout(self)
        form = QFormLayout()
        self.repo_edit = QLineEdit()
        self.repo_edit.setPlaceholderText("Lokaler Repository-Ordner")
        browse = QPushButton("Ordner…")
        browse.clicked.connect(self.choose_repo)
        repo_row = QHBoxLayout(); repo_row.addWidget(self.repo_edit, 1); repo_row.addWidget(browse)
        repo_wrap = QWidget(); repo_wrap.setLayout(repo_row)
        form.addRow("Repository", repo_wrap)
        self.remote_edit = QLineEdit()
        self.remote_edit.setPlaceholderText("https://github.com/benutzer/private-repo.git oder git@github.com:benutzer/private-repo.git")
        form.addRow("Remote-URL", self.remote_edit)
        self.branch_combo = QComboBox(); self.branch_combo.setMinimumWidth(0)
        form.addRow("Branch", self.branch_combo)
        root.addLayout(form)
        clone_row = QHBoxLayout()
        self.clone_path = QLineEdit()
        self.clone_path.setPlaceholderText("Zielordner für Clone (optional; sonst Name aus URL)")
        clone_browse = QPushButton("Ziel…"); clone_browse.clicked.connect(self.choose_clone_target)
        clone_btn = QPushButton("Private/öffentliche Repo klonen")
        clone_btn.clicked.connect(self.clone_repo)
        clone_row.addWidget(self.clone_path, 1); clone_row.addWidget(clone_browse); clone_row.addWidget(clone_btn)
        root.addLayout(clone_row)
        actions = QHBoxLayout()
        for label, callback in [
            ("Repo öffnen", self.load_repo), ("Status / Refresh", self.refresh),
            ("Fetch", self.fetch), ("Pull", self.pull), ("Push", self.push),
            ("Branch wechseln", self.switch_branch), ("Neuer Branch", self.create_branch),
        ]:
            b = QPushButton(label); b.clicked.connect(callback); actions.addWidget(b)
        root.addLayout(actions)
        commit_row = QHBoxLayout()
        self.commit_edit = QLineEdit(); self.commit_edit.setPlaceholderText("Commit-Nachricht")
        commit_btn = QPushButton("Änderungen committen")
        commit_btn.clicked.connect(self.commit_changes)
        commit_row.addWidget(self.commit_edit, 1); commit_row.addWidget(commit_btn)
        root.addLayout(commit_row)
        self.output = QPlainTextEdit(); self.output.setReadOnly(True); self.output.setPlaceholderText("Git-Ausgabe und Repository-Status")
        root.addWidget(self.output, 1)
        bottom = QHBoxLayout(); bottom.addStretch(1)
        close_btn = QPushButton("Schließen"); close_btn.clicked.connect(self.accept); bottom.addWidget(close_btn)
        root.addLayout(bottom)
        # Start in the directory associated with the active document, when possible.
        try:
            initial = str(ide.working_directory())
            self.repo_edit.setText(initial)
            self.load_repo(silent=True)
        except Exception:
            pass

    def log(self, text):
        self.output.appendPlainText(str(text).rstrip())

    def git(self, args, cwd=None, check=True):
        env = os.environ.copy()
        # Git Credential Manager / SSH agents can still authenticate, but Git will not
        # hang forever waiting for a username/password in an invisible terminal.
        env.setdefault("GIT_TERMINAL_PROMPT", "0")
        try:
            proc = subprocess.run(["git", *args], cwd=str(cwd or self.repo_path or Path.cwd()),
                                  text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  encoding="utf-8", errors="replace", env=env, timeout=180)
        except FileNotFoundError:
            raise RuntimeError("Git wurde nicht gefunden. Installiere Git for Windows und starte die IDE neu.")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Git hat nach 180 Sekunden abgebrochen.")
        if proc.stdout.strip(): self.log(proc.stdout)
        if check and proc.returncode:
            hint = ""
            low = proc.stdout.lower()
            if "authentication failed" in low or "could not read username" in low or "permission denied (publickey)" in low:
                hint = ("\nAuthentifizierung fehlgeschlagen. Für HTTPS Git Credential Manager verwenden/anmelden; "
                        "für SSH einen SSH-Schlüssel beim Git-Host hinterlegen. Tokens nicht in die Remote-URL schreiben.")
            raise RuntimeError(f"git {' '.join(args)} schlug fehl (Exit-Code {proc.returncode}).\n{proc.stdout}{hint}")
        return proc.stdout.strip()

    def choose_repo(self):
        start = self.repo_edit.text().strip() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "Git-Repository auswählen", start)
        if path:
            self.repo_edit.setText(path); self.load_repo()

    def choose_clone_target(self):
        path = QFileDialog.getExistingDirectory(self, "Zielordner für Repository wählen", str(Path.home()))
        if path: self.clone_path.setText(path)

    def clone_repo(self):
        url = self.remote_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Git", "Bitte zuerst eine HTTPS- oder SSH-Remote-URL eintragen."); return
        target = self.clone_path.text().strip()
        if not target:
            name = url.rstrip("/").rsplit("/", 1)[-1].rsplit(":", 1)[-1]
            if name.endswith(".git"): name = name[:-4]
            target = str(Path.home() / "Documents" / name)
        target_path = Path(target).expanduser()
        if target_path.exists() and any(target_path.iterdir()):
            QMessageBox.warning(self, "Git", "Der Zielordner existiert und ist nicht leer."); return
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            self.git(["clone", "--", url, str(target_path)], cwd=target_path.parent)
            self.repo_edit.setText(str(target_path)); self.load_repo()
            QMessageBox.information(self, "Git", "Repository erfolgreich geklont.")
        except Exception as e:
            QMessageBox.critical(self, "Clone fehlgeschlagen", str(e))

    def load_repo(self, silent=False):
        path = Path(self.repo_edit.text().strip()).expanduser() if self.repo_edit.text().strip() else None
        if path is None:
            if not silent: QMessageBox.warning(self, "Git", "Bitte Repository-Ordner auswählen.")
            return
        try:
            top = self.git(["rev-parse", "--show-toplevel"], cwd=path)
            self.repo_path = Path(top).resolve()
            self.repo_edit.setText(str(self.repo_path))
            remote = self.git(["remote", "get-url", "origin"], check=False)
            if remote and not self.remote_edit.text().strip(): self.remote_edit.setText(remote)
            self.refresh()
        except Exception as e:
            self.repo_path = None
            if not silent: QMessageBox.critical(self, "Kein Git-Repository", str(e))

    def require_repo(self):
        if not self.repo_path or not (self.repo_path / ".git").exists():
            self.load_repo(silent=True)
        if not self.repo_path:
            raise RuntimeError("Bitte einen lokalen Git-Repository-Ordner auswählen und auf „Repo öffnen“ klicken.")

    def run_action(self, args, success=None):
        try:
            self.require_repo(); self.git(args, cwd=self.repo_path)
            if success: self.log(success)
            self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Git-Fehler", str(e))

    def refresh(self):
        try:
            self.require_repo()
            branch = self.git(["branch", "--show-current"], cwd=self.repo_path, check=False) or "(detached HEAD)"
            branches = self.git(["branch", "--format=%(refname:short)"], cwd=self.repo_path, check=False).splitlines()
            self.branch_combo.clear(); self.branch_combo.addItems(branches)
            idx = self.branch_combo.findText(branch)
            if idx >= 0: self.branch_combo.setCurrentIndex(idx)
            status = self.git(["status", "--short", "--branch"], cwd=self.repo_path, check=False)
            self.log(f"\n[{self.repo_path}]\n{status or 'Arbeitsverzeichnis sauber'}")
        except Exception as e:
            self.log(f"Fehler: {e}")

    def fetch(self): self.run_action(["fetch", "--all", "--prune"], "Fetch abgeschlossen.")
    def pull(self): self.run_action(["pull", "--ff-only"], "Pull abgeschlossen.")
    def push(self): self.run_action(["push"], "Push abgeschlossen.")

    def switch_branch(self):
        branch = self.branch_combo.currentText().strip()
        if branch: self.run_action(["switch", branch], f"Branch gewechselt: {branch}")

    def create_branch(self):
        name, ok = QInputDialog.getText(self, "Neuer Branch", "Branch-Name:")
        if ok and name.strip(): self.run_action(["switch", "-c", name.strip()], f"Branch erstellt: {name.strip()}")

    def commit_changes(self):
        message = self.commit_edit.text().strip()
        if not message:
            QMessageBox.warning(self, "Git", "Bitte eine Commit-Nachricht eingeben."); return
        try:
            self.require_repo()
            self.git(["add", "--all"], cwd=self.repo_path)
            self.git(["commit", "-m", message], cwd=self.repo_path)
            self.commit_edit.clear(); self.refresh()
        except Exception as e:
            QMessageBox.critical(self, "Commit fehlgeschlagen", str(e))
