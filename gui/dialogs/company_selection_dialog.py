# gui/dialogs/company_selection_dialog.py
import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox, QFormLayout, QLineEdit, QMessageBox,
    QDialogButtonBox, QFrame, QTextEdit, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor, QPixmap
from pathlib import Path


from fbr_core.models import Company


class CompanySelectionDialog(QDialog):
    """Company selection dialog that appears on app startup"""
    
    company_selected = pyqtSignal(dict)  # Emits selected company data
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.selected_company = None
        
        
        self.setWindowTitle("Select Company - FBR E-Invoicing System")
        self.setModal(True)
        self.setFixedSize(700,650)
        
        # Make dialog not closable without selection
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | 
                          Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
        
        self.setStyleSheet("""
            QDialog { 
                background-color: #0f1115; 
                color: #eaeef6;
            }
            QLabel { 
                color: #eaeef6; 
                font-size: 13px; 
            }
            QGroupBox {
                background: #1b2028;
                border: 1px solid #2c3b52;
                border-radius: 10px;
                /* more top padding so the title has space inside the box */
                padding: 28px 12px 12px 12px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;   /* keep it inside the box */
                left: 12px;
                top: 0px;                        /* <-- no negative offset */
                background: #2c3b52;
                color: #eaeef6;
                border-radius: 8px;
                padding: 2px 10px;
                font-weight: 600;
            }
            QComboBox, QLineEdit, QTextEdit {
                background: #0f141c;
                color: #eaeef6;
                border: 1px solid #334561;
                border-radius: 6px;
                padding: 8px 12px;
                min-height: 34px;
            }
            QComboBox:focus, QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #5aa2ff;
                box-shadow: 0 0 0 2px rgba(90,162,255,0.18);
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
            QPushButton:disabled { background:#333; color:#666; }
            QPushButton[style="success"] { background-color: #28a745; }
            QPushButton[style="success"]:hover { background-color: #218838; }
            QPushButton[style="warning"] { background-color: #ffc107; color: #000; }
            QPushButton[style="warning"]:hover { background-color: #e0a800; }
        """)

        
        self.setup_ui()
        self.load_companies()

    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_label = QLabel("Welcome to FBR E-Invoicing System")
        header_font = QFont()
        header_font.setPointSize(18)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("color: #5aa2ff; margin: 20px 0;")
        layout.addWidget(header_label)

        # --- FBR logo under the welcome text ---

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        here = Path(__file__).resolve()
        candidates = [
            # resources next to repo root
            here.parents[2] / "resources" / "icons" / "fbr.jpg",
            # resources next to the GUI package
            here.parents[1] / "resources" / "icons" / "fbr.jpg",
            # common repo names (case sensitive on Linux)
            here.parents[2] / "FBR-E-Invoicing" / "resources" / "icons" / "fbr.jpg",
            here.parents[2] / "FBR-E-Invocing" / "resources" / "icons" / "fbr.jpg",
            # fallback to cwd
            Path.cwd() / "resources" / "icons" / "fbr.jpg",
        ]

        pix = QPixmap()
        for p in candidates:
            if p.exists():
                pix = QPixmap(str(p))
                break

        if not pix.isNull():
            scaled = pix.scaled(
                320, 120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(scaled)
            logo_label.setStyleSheet("margin: 8px 0 14px 0;")
            layout.addWidget(logo_label)

        # Subtitle
        subtitle_label = QLabel("Please select your company to continue")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("color: #cccccc; font-size: 14px; margin-bottom: 20px;")
        layout.addWidget(subtitle_label)
        
        # Company selection group
        company_group = QGroupBox("Company Selection")
        company_layout = QVBoxLayout(company_group)
        
        # Company dropdown
        form_layout = QFormLayout()
        self.company_combo = QComboBox()
        self.company_combo.setPlaceholderText("Select a company...")
        self.company_combo.currentIndexChanged.connect(self.on_company_changed)
        form_layout.addRow("Company:", self.company_combo)
        
        company_layout.addLayout(form_layout)
        
        # Company details preview
        self.details_group = QGroupBox("Company Details")
        details_layout = QFormLayout(self.details_group)
        
        self.ntn_label = QLabel("-")
        self.address_label = QLabel("-")
        
        details_layout.addRow("NTN/CNIC:", self.ntn_label)
        details_layout.addRow("Address:", self.address_label)
        
        self.details_group.setVisible(False)
        company_layout.addWidget(self.details_group)
        
        layout.addWidget(company_group)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("color: #334561;")
        layout.addWidget(separator)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        # Add new company button
        self.new_company_btn = QPushButton("➕ Add New Company")
        self.new_company_btn.setProperty("style", "warning")
        self.new_company_btn.clicked.connect(self.add_new_company)
        button_layout.addWidget(self.new_company_btn)
        
        button_layout.addStretch()
        
        # Continue button
        self.continue_btn = QPushButton("✅ Continue")
        self.continue_btn.setProperty("style", "success")
        self.continue_btn.clicked.connect(self.continue_with_company)
        self.continue_btn.setEnabled(False)
        button_layout.addWidget(self.continue_btn)
        
        layout.addLayout(button_layout)
        
        # Footer
        footer_label = QLabel("FBR E-Invoicing System v1.0")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setStyleSheet("color: #888888; font-size: 11px; margin-top: 20px;")
        layout.addWidget(footer_label)

    def load_companies(self):
        """Load companies from database"""
        try:
            session = self.db_manager.get_session()
            companies = session.query(Company).all()
            
            self.company_combo.clear()
            self.companies_data = {}
            
            if not companies:
                self.company_combo.addItem("No companies found")
                self.company_combo.setEnabled(False)
            else:
                self.company_combo.addItem("-- Select Company --")
                for company in companies:
                    display_name = f"{company.name} ({company.ntn_cnic})"
                    self.company_combo.addItem(display_name)
                    self.companies_data[display_name] = {
                        'ntn_cnic': company.ntn_cnic,
                        'name': company.name,
                        'address': company.address or "No address specified",
                        'created_at': company.created_at
                    }
                    
        except Exception as e:
            QMessageBox.critical(self, "Database Error", 
                               f"Failed to load companies: {str(e)}")
            
    def on_company_changed(self):
        """Handle company selection change"""
        current_text = self.company_combo.currentText()
        
        if current_text in self.companies_data:
            company_data = self.companies_data[current_text]
            self.selected_company = company_data
            
            # Update details
            self.ntn_label.setText(company_data['ntn_cnic'])
            self.address_label.setText(company_data['address'])
            
            self.details_group.setVisible(True)
            self.continue_btn.setEnabled(True)
        else:
            self.selected_company = None
            self.details_group.setVisible(False)
            self.continue_btn.setEnabled(False)

    def add_new_company(self):
        """Open dialog to add new company"""
        dialog = AddCompanyDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_companies()  # Refresh company list

    def continue_with_company(self):
        """Continue with selected company"""
        if self.selected_company:
            self.company_selected.emit(self.selected_company)
            self.accept()
        else:
            QMessageBox.warning(self, "Warning", "Please select a company to continue")


class AddCompanyDialog(QDialog):
    """Dialog to add a new company"""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        
        self.setWindowTitle("Add New Company")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        self.setStyleSheet(parent.styleSheet())  # Inherit parent style
        
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Form group
        form_group = QGroupBox("Company Information")
        form_layout = QFormLayout(form_group)
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter company name")
        form_layout.addRow("Company Name*:", self.name_edit)
        
        self.ntn_edit = QLineEdit()
        self.ntn_edit.setPlaceholderText("Enter NTN/CNIC")
        form_layout.addRow("NTN/CNIC*:", self.ntn_edit)
        
        self.address_edit = QTextEdit()
        self.address_edit.setPlaceholderText("Enter company address")
        self.address_edit.setMaximumHeight(80)
        form_layout.addRow("Address:", self.address_edit)
        
        layout.addWidget(form_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        
        save_btn = button_box.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setText("💾 Save Company")
        save_btn.setProperty("style", "success")
        
        cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("❌ Cancel")
        
        button_box.accepted.connect(self.save_company)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)

    def save_company(self):
        """Save new company to database"""
        name = self.name_edit.text().strip()
        ntn = self.ntn_edit.text().strip()
        address = self.address_edit.toPlainText().strip()
        
        # Validation
        if not name:
            QMessageBox.warning(self, "Validation Error", "Company name is required!")
            return
            
        if not ntn:
            QMessageBox.warning(self, "Validation Error", "NTN/CNIC is required!")
            return
            
        try:
            session = self.db_manager.get_session()
            
            # Check if company already exists
            existing = session.query(Company).filter_by(ntn_cnic=ntn).first()
            if existing:
                QMessageBox.warning(self, "Validation Error", 
                                  "A company with this NTN/CNIC already exists!")
                return
            
            # Create new company
            new_company = Company(
                ntn_cnic=ntn,
                name=name,
                address=address or None
            )
            
            session.add(new_company)
            session.commit()
            
            QMessageBox.information(self, "Success", 
                                  "Company added successfully!")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", 
                               f"Failed to save company: {str(e)}")


# Test the dialog
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Mock database manager for testing
    class MockDBManager:
        def get_session(self):
            # Return mock session
            return None
    
    dialog = CompanySelectionDialog(MockDBManager())
    dialog.company_selected.connect(lambda data: print("Selected company:", data))
    
    result = dialog.exec()
    print("Dialog result:", result)
    
    sys.exit(app.exec())