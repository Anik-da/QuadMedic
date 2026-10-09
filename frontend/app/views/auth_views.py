from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QMessageBox, QStackedWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from frontend.app.components.glass_card import GlassCard

class AuthWindow(QWidget):
    # Signal emitted on successful login
    login_success = pyqtSignal(str, str, str, str) # token, role, username, email

    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.setup_ui()

    def setup_ui(self):
        # Stacked layout for switching between Login, Registration, and OTP
        self.stacked_widget = QStackedWidget(self)
        
        self.login_widget = self.create_login_widget()
        self.register_widget = self.create_register_widget()
        self.otp_widget = self.create_otp_widget()
        
        self.stacked_widget.addWidget(self.login_widget)
        self.stacked_widget.addWidget(self.register_widget)
        self.stacked_widget.addWidget(self.otp_widget)
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.stacked_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(50, 50, 50, 50)

    def create_login_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        card = GlassCard(title="QuadMedic Authentication")
        card.setFixedWidth(400)
        
        logo = QLabel("QUADMEDIC Portal")
        logo.setStyleSheet("font-size: 24px; font-weight: bold; color: #FFFFFF; font-family: 'Segoe UI'; margin-bottom: 20px;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card.addWidget(logo)
        
        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("Email Address")
        self.login_email.setStyleSheet(self.get_input_style())
        card.addWidget(self.login_email)
        
        self.login_password = QLineEdit()
        self.login_password.setPlaceholderText("Password")
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password.setStyleSheet(self.get_input_style())
        card.addWidget(self.login_password)
        
        btn_login = QPushButton("LOGIN")
        btn_login.setStyleSheet(self.get_btn_style("#00F0FF"))
        btn_login.clicked.connect(self.handle_login)
        card.addWidget(btn_login)
        
        btn_goto_register = QPushButton("Create Student Account")
        btn_goto_register.setStyleSheet("color: #C0C0C0; background: transparent; border: none; font-size: 12px; text-decoration: underline;")
        btn_goto_register.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        card.addWidget(btn_goto_register)
        
        layout.addWidget(card)
        return widget

    def create_register_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        card = GlassCard(title="Student Registration")
        card.setFixedWidth(420)
        
        self.reg_username = QLineEdit()
        self.reg_username.setPlaceholderText("Full Name")
        self.reg_username.setStyleSheet(self.get_input_style())
        card.addWidget(self.reg_username)
        
        self.reg_email = QLineEdit()
        self.reg_email.setPlaceholderText("Email Address")
        self.reg_email.setStyleSheet(self.get_input_style())
        card.addWidget(self.reg_email)
        
        self.reg_password = QLineEdit()
        self.reg_password.setPlaceholderText("Password")
        self.reg_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_password.setStyleSheet(self.get_input_style())
        card.addWidget(self.reg_password)
        
        # Student specific credentials
        self.reg_student_id = QLineEdit()
        self.reg_student_id.setPlaceholderText("Student ID (e.g. S-1024)")
        self.reg_student_id.setStyleSheet(self.get_input_style())
        card.addWidget(self.reg_student_id)
        
        self.reg_dept = QLineEdit()
        self.reg_dept.setPlaceholderText("Department (e.g. CS)")
        self.reg_dept.setStyleSheet(self.get_input_style())
        card.addWidget(self.reg_dept)
        
        self.reg_year = QComboBox()
        self.reg_year.addItems(["1st Year", "2nd Year", "3rd Year", "4th Year"])
        self.reg_year.setStyleSheet(self.get_input_style())
        card.addWidget(self.reg_year)
        
        self.reg_blood = QComboBox()
        self.reg_blood.addItems(["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
        self.reg_blood.setStyleSheet(self.get_input_style())
        card.addWidget(self.reg_blood)
        
        # Register Role Selector (so we can also register Doctors or Admins for testing!)
        role_layout = QHBoxLayout()
        role_label = QLabel("Role:")
        role_label.setStyleSheet("color: white;")
        self.reg_role = QComboBox()
        self.reg_role.addItems(["student", "doctor", "admin"])
        self.reg_role.setStyleSheet(self.get_input_style())
        role_layout.addWidget(role_label)
        role_layout.addWidget(self.reg_role)
        card.addLayout(role_layout)
        
        btn_register = QPushButton("REGISTER")
        btn_register.setStyleSheet(self.get_btn_style("#00FF66"))
        btn_register.clicked.connect(self.handle_register)
        card.addWidget(btn_register)
        
        btn_back_login = QPushButton("Back to Login")
        btn_back_login.setStyleSheet("color: #C0C0C0; background: transparent; border: none; font-size: 12px; text-decoration: underline;")
        btn_back_login.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        card.addWidget(btn_back_login)
        
        layout.addWidget(card)
        return widget

    def create_otp_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        card = GlassCard(title="2-Factor Verification")
        card.setFixedWidth(400)
        
        self.otp_info_label = QLabel("An OTP code has been dispatched. Enter the digits below to complete login:")
        self.otp_info_label.setWordWrap(True)
        self.otp_info_label.setStyleSheet("color: #E0E0E0; font-family: 'Segoe UI'; margin-bottom: 15px;")
        card.addWidget(self.otp_info_label)
        
        self.otp_input = QLineEdit()
        self.otp_input.setPlaceholderText("Enter 6-digit OTP code")
        self.otp_input.setStyleSheet(self.get_input_style())
        card.addWidget(self.otp_input)
        
        btn_verify = QPushButton("VERIFY OTP")
        btn_verify.setStyleSheet(self.get_btn_style("#FFA500"))
        btn_verify.clicked.connect(self.handle_verify_otp)
        card.addWidget(btn_verify)
        
        layout.addWidget(card)
        return widget

    def handle_login(self):
        email = self.login_email.text().strip()
        password = self.login_password.text().strip()
        
        if not email or not password:
            QMessageBox.warning(self, "Validation Error", "Please fill in all credentials.")
            return
            
        try:
            # Connect to backend
            data = self.api_client.login(email, password)
            # Send simulated OTP for security confirmation
            otp_res = self.api_client.send_otp(email)
            demo_otp_str = ""
            if isinstance(otp_res, dict) and "demo_otp" in otp_res:
                demo_otp_str = f"\n\n(For testing, use code: {otp_res['demo_otp']} or fallback to 123456)"
            self.otp_info_label.setText(f"An OTP code has been dispatched to {email}. Enter the digits below to complete login:{demo_otp_str}")
            self.pending_login_data = data
            self.stacked_widget.setCurrentIndex(2) # Switch to OTP verify view
        except Exception as e:
            QMessageBox.critical(self, "Login Failed", f"Authentication error: {e}")

    def handle_register(self):
        username = self.reg_username.text().strip()
        email = self.reg_email.text().strip()
        password = self.reg_password.text().strip()
        student_id = self.reg_student_id.text().strip()
        dept = self.reg_dept.text().strip()
        year = self.reg_year.currentText()
        blood = self.reg_blood.currentText()
        role = self.reg_role.currentText()
        
        if not username or not email or not password:
            QMessageBox.warning(self, "Validation Error", "Please fill in Name, Email, and Password.")
            return
            
        try:
            self.api_client.register(
                email=email,
                username=username,
                password=password,
                role=role,
                student_id=student_id,
                dept=dept,
                year=year,
                blood=blood
            )
            QMessageBox.information(self, "Registration Successful", "You have registered. Please login.")
            self.stacked_widget.setCurrentIndex(0) # Back to login screen
        except Exception as e:
            QMessageBox.critical(self, "Registration Failed", f"Could not create account: {e}")

    def handle_verify_otp(self):
        otp = self.otp_input.text().strip()
        email = self.pending_login_data["email"]
        
        try:
            self.api_client.verify_otp(email, otp)
            # Emit token
            self.login_success.emit(
                self.pending_login_data["access_token"],
                self.pending_login_data["role"],
                self.pending_login_data["username"],
                self.pending_login_data["email"]
            )
        except Exception as e:
            QMessageBox.critical(self, "Verification Failed", f"Invalid OTP: {e}")

    def get_input_style(self) -> str:
        return """
            QLineEdit, QComboBox {
                background-color: rgba(255, 255, 255, 15);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 8px;
                padding: 10px;
                color: #FFFFFF;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #00F0FF;
            }
        """

    def get_btn_style(self, color: str) -> str:
        return f"""
            QPushButton {{
                background-color: {color};
                color: #0E1621;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                margin-top: 10px;
            }}
            QPushButton:hover {{
                background-color: #FFFFFF;
                color: {color};
            }}
        """
