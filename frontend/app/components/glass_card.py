from PyQt6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QVBoxLayout, QLabel, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

class GlassCard(QFrame):
    def __init__(self, parent=None, title: str = "", border_color: str = "rgba(255, 255, 255, 35)", bg_color: str = "rgba(20, 30, 45, 140)"):
        super().__init__(parent)
        
        # Apple VisionOS Liquid Glass styling via QSS
        self.setStyleSheet(f"""
            GlassCard {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 20px;
            }}
        """)
        
        # Inner layout
        self.card_layout = QVBoxLayout(self)
        self.card_layout.setContentsMargins(15, 15, 15, 15)
        self.card_layout.setSpacing(10)
        
        # Add soft, modern shadow effect
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(25)
        self.shadow.setColor(QColor(0, 0, 0, 80))
        self.shadow.setOffset(0, 10)
        self.setGraphicsEffect(self.shadow)
        
        # Add Title if provided
        if title:
            self.title_label = QLabel(title, self)
            self.title_label.setStyleSheet("""
                font-family: 'Segoe UI', Inter, sans-serif;
                font-size: 16px;
                font-weight: bold;
                color: #00F0FF; /* Bright glowing cyan cyan header */
                background: transparent;
                border: none;
            """)
            self.card_layout.addWidget(self.title_label)
            
    def addWidget(self, widget: QWidget):
        self.card_layout.addWidget(widget)

    def addLayout(self, layout):
        self.card_layout.addLayout(layout)
