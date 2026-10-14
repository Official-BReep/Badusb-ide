from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QProgressBar, QVBoxLayout, QWidget


class StartupSplash(QWidget):
    """Compact startup screen shown while the IDE initializes."""
    def __init__(self, icon_path: Path):
        super().__init__(None, Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle("ScriptMonkey – Start")
        self.setFixedSize(460, 300)
        self.setStyleSheet("""
            QWidget { background: #171a21; color: #eef2f8; font-family: Segoe UI, sans-serif; }
            QLabel#appTitle { font-size: 22px; font-weight: 700; }
            QLabel#subtitle { color: #aab4c4; font-size: 11px; }
            QLabel#status { color: #d9e2f0; font-size: 12px; }
            QProgressBar { border: 1px solid #3c4657; border-radius: 5px; background: #242a35; height: 12px; text-align: center; }
            QProgressBar::chunk { border-radius: 4px; background: #4f8cff; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(10)
        logo = QLabel()
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(str(icon_path)) if icon_path.exists() else QPixmap()
        if not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(88, 88, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            logo.setText("⚡")
            logo.setStyleSheet("font-size: 58px;")
        layout.addWidget(logo, 1)
        title = QLabel("ScriptMonkey")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        subtitle = QLabel("Flipper Zero Payload Editor")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        self.status_label = QLabel("Starte Anwendung …")
        self.status_label.setObjectName("status")
        layout.addWidget(self.status_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
        self.setWindowIcon(QIcon(str(icon_path)))
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._center()

    def _center(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(geo.center().x() - self.width() // 2, geo.center().y() - self.height() // 2)

    def update_progress(self, value: int, message: str):
        self.progress.setValue(value)
        self.status_label.setText(message)
        QApplication.processEvents()