from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QMessageBox, QSplitter)
from PyQt6.QtCore import Qt, QTimer
from frontend.app.components.glass_card import GlassCard

# Import matplotlib to embed plots
import matplotlib
matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        # Setup dark-mode background figure matching our dark slate theme
        fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#0E1621')
        self.axes = fig.add_subplot(111, facecolor='#121C2B')
        
        # Color ticks and labels
        self.axes.tick_params(colors='white')
        self.axes.xaxis.label.set_color('white')
        self.axes.yaxis.label.set_color('white')
        for spine in self.axes.spines.values():
            spine.set_color('rgba(255,255,255,30)')
            
        super().__init__(fig)

class AdminDashboard(QWidget):
    def __init__(self, api_client):
        super().__init__()
        self.api_client = api_client
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Campus Health Analytics Command Center")
        title.setStyleSheet("color: #FFFFFF; font-size: 22px; font-weight: bold;")
        header.addWidget(title)
        
        btn_logout = QPushButton("🚪 Logout")
        btn_logout.setStyleSheet("background: transparent; color: #FF4D4D; border: none; font-size: 13px; text-decoration: underline;")
        header.addWidget(btn_logout)
        layout.addLayout(header)
        
        # Splitter between charts and Emergency logs
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top Panel: Analytical Charts row
        charts_widget = QWidget()
        charts_layout = QHBoxLayout(charts_widget)
        charts_layout.setContentsMargins(0, 0, 0, 0)
        charts_layout.setSpacing(15)
        
        # Chart 1: Sickness frequency (Bar Chart)
        self.illness_card = GlassCard(title="Common Sickness Distribution")
        self.canvas_illness = MplCanvas(self, width=4, height=3)
        self.illness_card.addWidget(self.canvas_illness)
        charts_layout.addWidget(self.illness_card)
        
        # Chart 2: Risk categories (Pie Chart)
        self.risk_card = GlassCard(title="Student Health Risk Categories")
        self.canvas_risk = MplCanvas(self, width=4, height=3)
        self.risk_card.addWidget(self.canvas_risk)
        charts_layout.addWidget(self.risk_card)
        
        # Chart 3: Appointments monthly (Line Chart)
        self.appt_card = GlassCard(title="Monthly Appointment Load")
        self.canvas_appt = MplCanvas(self, width=4, height=3)
        self.appt_card.addWidget(self.canvas_appt)
        charts_layout.addWidget(self.appt_card)
        
        splitter.addWidget(charts_widget)
        
        # Bottom Panel: Emergency cases center
        emergency_card = GlassCard(title="Real-Time Emergency Monitor & Dispatch Center")
        
        emerg_layout = QHBoxLayout()
        
        self.emergency_list = QListWidget()
        self.emergency_list.setStyleSheet("background-color: rgba(180,0,0,30); border: 1px solid rgba(255,0,0,40); border-radius: 8px; color: #FFFFFF; padding: 10px;")
        emerg_layout.addWidget(self.emergency_list)
        
        btns_lay = QVBoxLayout()
        btn_resolve = QPushButton("✅ Mark Case Resolved")
        btn_resolve.setStyleSheet(self.get_btn_style("#00FF66"))
        btn_resolve.clicked.connect(self.handle_resolve_emergency)
        btns_lay.addWidget(btn_resolve)
        
        btn_refresh = QPushButton("🔄 Refresh Analytics")
        btn_refresh.setStyleSheet(self.get_btn_style("#00F0FF"))
        btn_refresh.clicked.connect(self.refresh_dashboard)
        btns_lay.addWidget(btn_refresh)
        btns_lay.addStretch()
        emerg_layout.addLayout(btns_lay)
        
        emergency_card.addLayout(emerg_layout)
        splitter.addWidget(emergency_card)
        
        layout.addWidget(splitter)
        
        # Refresh analytics initially
        QTimer.singleShot(100, self.refresh_dashboard)

    def refresh_dashboard(self):
        try:
            # Query analytics data
            data = self.api_client.get_analytics()
            
            # Update Illnesses Bar Chart
            self.canvas_illness.axes.clear()
            illnesses = [item["name"] for item in data["illnesses"]]
            counts = [item["count"] for item in data["illnesses"]]
            self.canvas_illness.axes.bar(illnesses, counts, color='#00F0FF', edgecolor='white', width=0.5)
            self.canvas_illness.axes.set_ylabel("Occurrences")
            self.canvas_illness.axes.tick_params(axis='x', labelrotation=30, labelsize=8)
            self.canvas_illness.draw()
            
            # Update Risk Category Pie Chart
            self.canvas_risk.axes.clear()
            categories = [item["category"] for item in data["health_scores"]]
            cat_counts = [item["count"] for item in data["health_scores"]]
            # Custom matching colors (Teal, Green, Orange, Red)
            colors = ['#00FF66', '#00F0FF', '#FF8800', '#FF3333']
            self.canvas_risk.axes.pie(cat_counts, labels=categories, colors=colors, autopct='%1.1f%%', textprops={'color':"w", 'fontsize':8})
            self.canvas_risk.draw()
            
            # Update Appointment Load Line Chart
            self.canvas_appt.axes.clear()
            months = [item["month"] for item in data["appointments"]]
            appt_counts = [item["count"] for item in data["appointments"]]
            self.canvas_appt.axes.plot(months, appt_counts, marker='o', color='#FF00FF', linewidth=2)
            self.canvas_appt.axes.set_ylabel("Bookings")
            self.canvas_appt.draw()
            
            # Update Emergency monitor list
            self.emergency_list.clear()
            emerg = data["emergencies"]
            self.emergency_list.addItem(f"🚨 ACTIVE RED ALERTS: {emerg.get('active', 0)} dispatch cases currently pending response.")
            self.emergency_list.addItem(f"✅ RESOLVED EMERGENCIES: {emerg.get('resolved', 0)} cases successfully closed.")
            
        except Exception as e:
            QMessageBox.critical(self, "Analytics Error", f"Could not load campus charts: {e}")

    def handle_resolve_emergency(self):
        QMessageBox.information(self, "Emergency Resolved", "Emergency dispatch status marked as Resolved. Dispatch crew signaled.")
        self.refresh_dashboard()

    def get_btn_style(self, color: str) -> str:
        return f"""
            QPushButton {{
                background-color: {color};
                color: #0E1621;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                min-width: 150px;
            }}
            QPushButton:hover {{
                background-color: #FFFFFF;
                color: {color};
            }}
        """
