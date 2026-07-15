"""Comment dialog."""
from __future__ import annotations
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit, QDialogButtonBox

class CommentDialog(QDialog):
    def __init__(self, title: str, label: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(label))
        self.text = QTextEdit()
        self.text.setMinimumHeight(90)
        layout.addWidget(self.text)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def value(self) -> str:
        return self.text.toPlainText().strip()


