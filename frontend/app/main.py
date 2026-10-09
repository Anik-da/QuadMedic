import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QStackedWidget
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPalette, QColor, QBrush, QLinearGradient

# Add absolute imports path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from frontend.app.api_client import QuadMedicAPIClient
from frontend.app.views.auth_views import AuthWindow
from frontend.app.views.student_view import StudentDashboard
from frontend.app.views.doctor_view import DoctorDashboard
from frontend.app.views.admin_view import AdminDashboard

class QuadMedicMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("QuadMedic - Smart Healthcare Ecosystem")
        self.setMinimumSize(QSize(1000, 680))
        self.resize(1100, 720)
        
        # Initialize API client
        self.api_client = QuadMedicAPIClient()
        
        # Stacked widget to switch views (Auth -> Dashboard)
        self.central_stack = QStackedWidget(self)
        self.setCentralWidget(self.central_stack)
        
        # Set up global dark mode styling
        self.apply_global_theme()
        
        # Initialize Auth View
        self.auth_view = AuthWindow(self.api_client)
        self.auth_view.login_success.connect(self.handle_login_success)
        self.central_stack.addWidget(self.auth_view)
        
        self.central_stack.setCurrentWidget(self.auth_view)

    def apply_global_theme(self):
        # Premium dark styling with cyan & purple highlights
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0E1621;
            }
            QWidget {
                font-family: 'Segoe UI', Inter, sans-serif;
            }
            QLabel {
                color: #FFFFFF;
            }
            QMessageBox {
                background-color: #0E1621;
                color: white;
            }
            QMessageBox QLabel {
                color: white;
            }
            QMessageBox QPushButton {
                background-color: #00F0FF;
                color: #0E1621;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 15px;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0,0,0,40);
                width: 8px;
                margin: 0px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,40);
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: none;
                background: none;
            }
        """)

    def handle_login_success(self, token: str, role: str, username: str, email: str):
        # Create and add Dashboard based on role
        if role == "student":
            self.dashboard = StudentDashboard(self.api_client)
            self.dashboard.logout_requested.connect(self.handle_logout)
            self.central_stack.addWidget(self.dashboard)
            self.central_stack.setCurrentWidget(self.dashboard)
        elif role == "doctor":
            self.dashboard = DoctorDashboard(self.api_client)
            # Find and connect the logout button in Doctor view
            # (We find the QPushButton matching text)
            for child in self.dashboard.findChildren(QPushButton):
                if "Logout" in child.text():
                    child.clicked.connect(self.handle_logout)
                    break
            self.central_stack.addWidget(self.dashboard)
            self.central_stack.setCurrentWidget(self.dashboard)
        elif role == "admin":
            self.dashboard = AdminDashboard(self.api_client)
            for child in self.dashboard.findChildren(QPushButton):
                if "Logout" in child.text():
                    child.clicked.connect(self.handle_logout)
                    break
            self.central_stack.addWidget(self.dashboard)
            self.central_stack.setCurrentWidget(self.dashboard)

    def handle_logout(self):
        self.api_client.logout()
        self.central_stack.setCurrentWidget(self.auth_view)
        # Clean up dashboard widget
        widget = self.central_stack.widget(1)
        if widget:
            self.central_stack.removeWidget(widget)
            widget.deleteLater()

def main():
    app = QApplication(sys.argv)
    
    # Enable High DPI scaling
    app.setAttribute(Qt.ApplicationAttribute.AA_DontCreateShowToolTipsOnFirstShow, True)
    
    window = QuadMedicMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
