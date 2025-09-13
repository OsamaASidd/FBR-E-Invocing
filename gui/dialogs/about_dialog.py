# gui/dialogs/about_dialog.py
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QApplication
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPixmap
from pathlib import Path


class AboutDialog(QDialog):
    """About dialog for FBR E-Invoicing System"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle("About FBR E-Invoicing System")
        self.setModal(True)
        self.setFixedSize(600, 700)
        
        self.setStyleSheet("""
            QDialog { 
                background-color: #0f1115; 
                color: #eaeef6;
            }
            QLabel { 
                color: #eaeef6; 
                font-size: 13px; 
            }
            QTextEdit {
                background: #1b2028;
                color: #eaeef6;
                border: 1px solid #2c3b52;
                border-radius: 8px;
                padding: 12px;
            }
            QPushButton {
                background-color: #5aa2ff; 
                color: #0f1115; 
                border: none;
                padding: 10px 20px; 
                border-radius: 6px; 
                font-weight: 700;
                font-size: 14px;
            }
            QPushButton:hover { background:#7bb6ff; }
            QPushButton:pressed { background:#4b92ec; }
        """)
        
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Header with logo
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #2c3b52;
                border-radius: 12px;
                margin: 5px;
                padding: 20px;
            }
        """)
        
        header_layout = QVBoxLayout(header_frame)
        
        # Try to load FBR logo
        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Look for FBR logo in various locations
        logo_paths = [
            Path("resources/icons/fbr.jpg"),
            Path("resources/icons/fbr.png"),
            Path("gui/dialogs/../../../resources/icons/fbr.jpg"),
            Path(__file__).parent.parent.parent / "resources" / "icons" / "fbr.jpg"
        ]
        
        logo_found = False
        for logo_path in logo_paths:
            if logo_path.exists():
                pixmap = QPixmap(str(logo_path))
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        200, 80, 
                        Qt.AspectRatioMode.KeepAspectRatio, 
                        Qt.TransformationMode.SmoothTransformation
                    )
                    logo_label.setPixmap(scaled_pixmap)
                    logo_found = True
                    break
        
        if not logo_found:
            logo_label.setText("🏛️ Federal Board of Revenue")
            logo_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #5aa2ff;")
        
        header_layout.addWidget(logo_label)
        
        # Application title
        title_label = QLabel("FBR E-Invoicing System")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #5aa2ff; margin: 10px 0;")
        header_layout.addWidget(title_label)
        
        # Version
        version_label = QLabel("Version 1.0.0")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #cccccc; font-size: 14px; margin-bottom: 10px;")
        header_layout.addWidget(version_label)
        
        layout.addWidget(header_frame)
        
        # Application info
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setMaximumHeight(350)
        
        info_content = """
<h3 style="color: #5aa2ff;">About This Application</h3>

<p><strong>FBR E-Invoicing System</strong> is a comprehensive desktop application designed to help Pakistani businesses comply with Federal Board of Revenue (FBR) electronic invoicing requirements.</p>

<h4 style="color: #ffc107;">Key Features:</h4>
<ul>
<li>📄 <strong>Invoice Management:</strong> Create, edit, and manage sales invoices</li>
<li>🏢 <strong>Multi-Company Support:</strong> Handle multiple companies from single application</li>
<li>📦 <strong>Item Management:</strong> Manage products and services with FBR HS codes</li>
<li>🔄 <strong>FBR Integration:</strong> Direct integration with FBR APIs for real-time validation</li>
<li>⚡ <strong>Queue System:</strong> Automatic retry mechanism for failed submissions</li>
<li>📊 <strong>Comprehensive Logging:</strong> Detailed logs of all FBR transactions</li>
<li>🔒 <strong>Secure:</strong> Encrypted storage of sensitive data</li>
<li>🎯 <strong>Sandbox Testing:</strong> Test your invoices before production submission</li>
</ul>

<h4 style="color: #ffc107;">Technology Stack:</h4>
<ul>
<li><strong>Framework:</strong> PyQt6 for modern desktop UI</li>
<li><strong>Database:</strong> PostgreSQL with SQLAlchemy ORM</li>
<li><strong>Cloud Database:</strong> Neon PostgreSQL for reliable hosting</li>
<li><strong>APIs:</strong> Direct integration with FBR PRAL APIs</li>
</ul>

<h4 style="color: #ffc107;">Compliance:</h4>
<p>This application is designed to comply with FBR's electronic invoicing requirements as per the latest regulations. It supports both sandbox testing and production environments.</p>

<h4 style="color: #28a745;">Support:</h4>
<p>For technical support, documentation, or feature requests, please contact your system administrator.</p>

<hr>
<p style="text-align: center; color: #888888; font-size: 12px;">
© 2024 FBR E-Invoicing System. Built with ❤️ for Pakistani businesses.
</p>
        """
        
        info_text.setHtml(info_content)
        layout.addWidget(info_text)
        
        # System info
        system_frame = QFrame()
        system_frame.setStyleSheet("""
            QFrame {
                background-color: #1b2028;
                border: 1px solid #2c3b52;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }
        """)
        
        system_layout = QVBoxLayout(system_frame)
        
        system_label = QLabel("System Information")
        system_label.setStyleSheet("font-weight: bold; color: #5aa2ff; font-size: 14px;")
        system_layout.addWidget(system_label)
        
        # Get system info
        import platform
        try:
            from PyQt6.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
            qt_version = QT_VERSION_STR
            pyqt_version = PYQT_VERSION_STR
        except ImportError:
            qt_version = "Unknown"
            pyqt_version = "Unknown"
        
        system_info = f"""
<table style="color: #cccccc; font-size: 12px;">
<tr><td><strong>Platform:</strong></td><td>{platform.system()} {platform.release()}</td></tr>
<tr><td><strong>Python:</strong></td><td>{platform.python_version()}</td></tr>
<tr><td><strong>PyQt6:</strong></td><td>{pyqt_version}</td></tr>
<tr><td><strong>Qt:</strong></td><td>{qt_version}</td></tr>
<tr><td><strong>Architecture:</strong></td><td>{platform.machine()}</td></tr>
</table>
        """
        
        system_info_label = QLabel(system_info)
        system_info_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        system_layout.addWidget(system_info_label)
        
        layout.addWidget(system_frame)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("✅ Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)


# Test the dialog
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    dialog = AboutDialog()
    result = dialog.exec()
    
    sys.exit(app.exec())