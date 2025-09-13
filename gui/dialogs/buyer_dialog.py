# gui/dialogs/buyer_dialog.py
import sys
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QTextEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QGroupBox, QMessageBox, QDialogButtonBox,
    QHeaderView, QFrame, QApplication, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from fbr_core.models import Buyer


class BuyerManagementDialog(QDialog):
    """Dialog for managing company-specific buyers/customers"""
    
    def __init__(self, db_manager, company_data, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.company_data = company_data
        self.company_id = company_data['ntn_cnic']
        
        self.setWindowTitle(f"Buyer Management - {company_data['name']}")
        self.setModal(True)
        self.resize(1000, 700)
        
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
                padding: 28px 12px 12px 12px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 12px;
                top: 0px;
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
                min-height: 28px;
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
            QPushButton[style="danger"] { background-color: #dc3545; }
            QPushButton[style="danger"]:hover { background-color: #c82333; }
            QTableWidget { 
                background: #0f141c; 
                color:#eaeef6; 
                border: 1px solid #334561; 
            }
            QHeaderView::section {
                background: #17202b; 
                color: #cfe2ff; 
                border: 1px solid #334561; 
                padding: 6px; 
                font-weight: 600;
            }
            QCheckBox {
                color: #eaeef6;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background: #0f141c;
                border: 2px solid #334561;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background: #28a745;
                border: 2px solid #28a745;
                border-radius: 4px;
            }
        """)
        
        self.setup_ui()
        self.load_buyers()
        
        # Store for edit mode
        self.editing_buyer_id = None

    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #2c3b52;
                border-radius: 12px;
                margin: 5px;
                padding: 15px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        
        # Company info
        company_label = QLabel(f"Managing buyers for: {self.company_data['name']}")
        company_font = QFont()
        company_font.setPointSize(14)
        company_font.setBold(True)
        company_label.setFont(company_font)
        company_label.setStyleSheet("color: #5aa2ff;")
        header_layout.addWidget(company_label)
        
        header_layout.addStretch()
        
        # Company NTN
        ntn_label = QLabel(f"NTN: {self.company_id}")
        ntn_label.setStyleSheet("color: #cccccc; font-weight: bold;")
        header_layout.addWidget(ntn_label)
        
        layout.addWidget(header_frame)
        
        # Create buyer form
        self.create_buyer_form(layout)
        
        # Buyers table
        self.create_buyers_table(layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.accept)
        
        close_btn = button_box.button(QDialogButtonBox.StandardButton.Close)
        close_btn.setText("✅ Done")
        close_btn.setProperty("style", "success")
        
        layout.addWidget(button_box)

    def create_buyer_form(self, parent_layout):
        """Create buyer entry form"""
        form_group = QGroupBox("Add/Edit Buyer")
        form_layout = QGridLayout(form_group)
        
        # Row 1: Name and NTN
        form_layout.addWidget(QLabel("Buyer Name*:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter buyer/customer name")
        form_layout.addWidget(self.name_edit, 0, 1)
        
        form_layout.addWidget(QLabel("NTN/CNIC*:"), 0, 2)
        self.ntn_edit = QLineEdit()
        self.ntn_edit.setPlaceholderText("Enter 13-digit NTN/CNIC")
        self.ntn_edit.setMaxLength(13)
        form_layout.addWidget(self.ntn_edit, 0, 3)
        
        # Row 2: Buyer Type and Province
        form_layout.addWidget(QLabel("Buyer Type*:"), 1, 0)
        self.buyer_type_combo = QComboBox()
        self.buyer_type_combo.addItems(["Registered", "Unregistered"])
        form_layout.addWidget(self.buyer_type_combo, 1, 1)
        
        form_layout.addWidget(QLabel("Province:"), 1, 2)
        self.province_combo = QComboBox()
        self.province_combo.addItems([
            "", "Punjab", "Sindh", "Khyber Pakhtunkhwa", "Balochistan",
            "Gilgit-Baltistan", "Azad Kashmir", "Islamabad Capital Territory"
        ])
        form_layout.addWidget(self.province_combo, 1, 3)
        
        # Row 3: City and Phone
        form_layout.addWidget(QLabel("City:"), 2, 0)
        self.city_edit = QLineEdit()
        self.city_edit.setPlaceholderText("Enter city")
        form_layout.addWidget(self.city_edit, 2, 1)
        
        form_layout.addWidget(QLabel("Phone:"), 2, 2)
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("e.g., +92-21-1234567")
        form_layout.addWidget(self.phone_edit, 2, 3)
        
        # Row 4: Email and Active status
        form_layout.addWidget(QLabel("Email:"), 3, 0)
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("buyer@example.com")
        form_layout.addWidget(self.email_edit, 3, 1)
        
        form_layout.addWidget(QLabel("Status:"), 3, 2)
        self.is_active_check = QCheckBox("Active")
        self.is_active_check.setChecked(True)
        form_layout.addWidget(self.is_active_check, 3, 3)
        
        # Row 5: Address (full width)
        form_layout.addWidget(QLabel("Address:"), 4, 0)
        self.address_edit = QTextEdit()
        self.address_edit.setMaximumHeight(80)
        self.address_edit.setPlaceholderText("Enter complete address")
        form_layout.addWidget(self.address_edit, 4, 1, 1, 3)
        
        # Row 6: Buttons
        button_layout = QHBoxLayout()
        
        self.save_buyer_btn = QPushButton("💾 Save Buyer")
        self.save_buyer_btn.setProperty("style", "success")
        self.save_buyer_btn.clicked.connect(self.save_buyer)
        button_layout.addWidget(self.save_buyer_btn)
        
        self.clear_form_btn = QPushButton("🧹 Clear Form")
        self.clear_form_btn.clicked.connect(self.clear_form)
        button_layout.addWidget(self.clear_form_btn)
        
        button_layout.addStretch()
        
        self.edit_mode_label = QLabel("")
        self.edit_mode_label.setStyleSheet("color: #ffc107; font-weight: bold;")
        button_layout.addWidget(self.edit_mode_label)
        
        form_layout.addLayout(button_layout, 5, 0, 1, 4)
        
        parent_layout.addWidget(form_group)

    def create_buyers_table(self, parent_layout):
        """Create buyers display table"""
        table_group = QGroupBox("Company Buyers")
        table_layout = QVBoxLayout(table_group)
        
        # Table toolbar
        toolbar_layout = QHBoxLayout()
        
        self.edit_selected_btn = QPushButton("✏️ Edit Selected")
        self.edit_selected_btn.clicked.connect(self.edit_selected_buyer)
        self.edit_selected_btn.setEnabled(False)
        toolbar_layout.addWidget(self.edit_selected_btn)
        
        self.delete_selected_btn = QPushButton("🗑️ Delete Selected")
        self.delete_selected_btn.setProperty("style", "danger")
        self.delete_selected_btn.clicked.connect(self.delete_selected_buyer)
        self.delete_selected_btn.setEnabled(False)
        toolbar_layout.addWidget(self.delete_selected_btn)
        
        self.toggle_active_btn = QPushButton("🔄 Toggle Active")
        self.toggle_active_btn.setProperty("style", "warning")
        self.toggle_active_btn.clicked.connect(self.toggle_buyer_active)
        self.toggle_active_btn.setEnabled(False)
        toolbar_layout.addWidget(self.toggle_active_btn)
        
        toolbar_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.load_buyers)
        toolbar_layout.addWidget(self.refresh_btn)
        
        # Search box
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search buyers...")
        self.search_edit.textChanged.connect(self.filter_buyers)
        toolbar_layout.addWidget(self.search_edit)
        
        table_layout.addLayout(toolbar_layout)
        
        # Buyers table
        self.buyers_table = QTableWidget()
        self.buyers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.buyers_table.setAlternatingRowColors(True)
        self.buyers_table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        table_layout.addWidget(self.buyers_table)
        
        parent_layout.addWidget(table_group)

    def load_buyers(self):
        """Load buyers for the current company"""
        try:
            session = self.db_manager.get_session()
            self.buyers = (
                session.query(Buyer)
                .filter_by(company_id=self.company_id)
                .order_by(Buyer.name.asc())
                .all()
            )
            
            self.populate_table(self.buyers)
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load buyers: {str(e)}")

    def populate_table(self, buyers):
        """Populate table with buyers"""
        self.buyers_table.setRowCount(len(buyers))
        self.buyers_table.setColumnCount(8)
        self.buyers_table.setHorizontalHeaderLabels([
            "ID", "Name", "NTN/CNIC", "Type", "Province", "Phone", "Status", "Created"
        ])
        
        for row, buyer in enumerate(buyers):
            self.buyers_table.setItem(row, 0, QTableWidgetItem(str(buyer.id)))
            self.buyers_table.setItem(row, 1, QTableWidgetItem(buyer.name or ""))
            self.buyers_table.setItem(row, 2, QTableWidgetItem(buyer.ntn_cnic or ""))
            self.buyers_table.setItem(row, 3, QTableWidgetItem(buyer.buyer_type or ""))
            self.buyers_table.setItem(row, 4, QTableWidgetItem(buyer.province or ""))
            self.buyers_table.setItem(row, 5, QTableWidgetItem(buyer.phone or ""))
            
            # Status with color coding
            status_item = QTableWidgetItem("Active" if buyer.is_active else "Inactive")
            if buyer.is_active:
                status_item.setBackground(QColor("#28a745"))
            else:
                status_item.setBackground(QColor("#dc3545"))
            self.buyers_table.setItem(row, 6, status_item)
            
            self.buyers_table.setItem(row, 7, QTableWidgetItem(
                buyer.created_at.strftime("%Y-%m-%d") if buyer.created_at else ""
            ))
        
        # Resize columns
        self.buyers_table.resizeColumnsToContents()
        header = self.buyers_table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name column

    def filter_buyers(self, text):
        """Filter buyers based on search text"""
        if not text:
            self.populate_table(self.buyers)
            return
        
        filtered_buyers = [
            buyer for buyer in self.buyers
            if text.lower() in (buyer.name or "").lower() or
               text.lower() in (buyer.ntn_cnic or "").lower() or
               text.lower() in (buyer.province or "").lower() or
               text.lower() in (buyer.buyer_type or "").lower()
        ]
        
        self.populate_table(filtered_buyers)

    def save_buyer(self):
        """Save buyer to database with validation"""
        # Validate form
        name = self.name_edit.text().strip()
        ntn_cnic = self.ntn_edit.text().strip()
        buyer_type = self.buyer_type_combo.currentText().strip()
        province = self.province_combo.currentText().strip()
        city = self.city_edit.text().strip()
        phone = self.phone_edit.text().strip()
        email = self.email_edit.text().strip()
        address = self.address_edit.toPlainText().strip()
        is_active = self.is_active_check.isChecked()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Buyer name is required!")
            self.name_edit.setFocus()
            return
            
        if not ntn_cnic:
            QMessageBox.warning(self, "Validation Error", "NTN/CNIC is required!")
            self.ntn_edit.setFocus()
            return
        
        # Validate NTN format for registered buyers
        if buyer_type == "Registered":
            if not ntn_cnic.isdigit() or len(ntn_cnic) != 13:
                QMessageBox.warning(self, "Validation Error", 
                                  "For registered buyers, NTN/CNIC must be exactly 13 digits!")
                self.ntn_edit.setFocus()
                return
        
        # Validate email format if provided
        if email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                QMessageBox.warning(self, "Validation Error", "Please enter a valid email address!")
                self.email_edit.setFocus()
                return
        
        try:
            session = self.db_manager.get_session()
            
            if self.editing_buyer_id:
                # Edit existing buyer
                buyer = session.query(Buyer).filter_by(id=self.editing_buyer_id).first()
                if not buyer:
                    QMessageBox.warning(self, "Error", "Buyer not found for editing!")
                    return
                    
                action = "updated"
            else:
                # Check if buyer with same NTN already exists for this company
                existing = session.query(Buyer).filter_by(
                    company_id=self.company_id,
                    ntn_cnic=ntn_cnic
                ).first()
                
                if existing:
                    QMessageBox.warning(self, "Validation Error", 
                                      f"A buyer with NTN/CNIC {ntn_cnic} already exists for this company!")
                    self.ntn_edit.setFocus()
                    return
                
                # Create new buyer
                buyer = Buyer(company_id=self.company_id)
                session.add(buyer)
                action = "created"
            
            # Update buyer fields
            buyer.name = name
            buyer.ntn_cnic = ntn_cnic
            buyer.buyer_type = buyer_type
            buyer.province = province or None
            buyer.city = city or None
            buyer.phone = phone or None
            buyer.email = email or None
            buyer.address = address or None
            buyer.is_active = is_active
            buyer.updated_at = datetime.now()
            
            if not self.editing_buyer_id:
                buyer.created_at = datetime.now()
            
            session.commit()
            
            QMessageBox.information(
                self, "Success", 
                f"Buyer '{name}' {action} successfully!"
            )
            
            self.clear_form()
            self.load_buyers()
            
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Database Error", f"Failed to save buyer: {str(e)}")

    def clear_form(self):
        """Clear the form fields"""
        self.name_edit.clear()
        self.ntn_edit.clear()
        self.buyer_type_combo.setCurrentIndex(0)
        self.province_combo.setCurrentIndex(0)
        self.city_edit.clear()
        self.phone_edit.clear()
        self.email_edit.clear()
        self.address_edit.clear()
        self.is_active_check.setChecked(True)
        
        self.editing_buyer_id = None
        self.edit_mode_label.setText("")
        self.save_buyer_btn.setText("💾 Save Buyer")

    def on_selection_changed(self):
        """Handle table selection changes"""
        has_selection = len(self.buyers_table.selectedItems()) > 0
        self.edit_selected_btn.setEnabled(has_selection)
        self.delete_selected_btn.setEnabled(has_selection)
        self.toggle_active_btn.setEnabled(has_selection)

    def edit_selected_buyer(self):
        """Edit the selected buyer"""
        current_row = self.buyers_table.currentRow()
        if current_row < 0:
            return
            
        try:
            buyer_id = int(self.buyers_table.item(current_row, 0).text())
            
            session = self.db_manager.get_session()
            buyer = session.query(Buyer).filter_by(id=buyer_id).first()
            
            if not buyer:
                QMessageBox.warning(self, "Error", "Buyer not found!")
                return
            
            # Populate form with buyer data
            self.name_edit.setText(buyer.name or "")
            self.ntn_edit.setText(buyer.ntn_cnic or "")
            
            buyer_type_index = self.buyer_type_combo.findText(buyer.buyer_type or "Registered")
            if buyer_type_index >= 0:
                self.buyer_type_combo.setCurrentIndex(buyer_type_index)
            
            province_index = self.province_combo.findText(buyer.province or "")
            if province_index >= 0:
                self.province_combo.setCurrentIndex(province_index)
            
            self.city_edit.setText(buyer.city or "")
            self.phone_edit.setText(buyer.phone or "")
            self.email_edit.setText(buyer.email or "")
            self.address_edit.setText(buyer.address or "")
            self.is_active_check.setChecked(buyer.is_active)
            
            # Set edit mode
            self.editing_buyer_id = buyer_id
            self.edit_mode_label.setText(f"Editing: {buyer.name}")
            self.save_buyer_btn.setText("💾 Update Buyer")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load buyer for editing: {str(e)}")

    def delete_selected_buyer(self):
        """Delete the selected buyer"""
        current_row = self.buyers_table.currentRow()
        if current_row < 0:
            return
            
        try:
            buyer_id = int(self.buyers_table.item(current_row, 0).text())
            buyer_name = self.buyers_table.item(current_row, 1).text()
            
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete the buyer '{buyer_name}'?\n\n"
                "This will also affect any invoices associated with this buyer.\n"
                "This action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                session = self.db_manager.get_session()
                
                # Check if buyer is used in any invoices
                from fbr_core.models import Invoices
                invoice_count = session.query(Invoices).filter_by(buyer_id=buyer_id).count()
                
                if invoice_count > 0:
                    final_reply = QMessageBox.question(
                        self, "Buyer Has Invoices",
                        f"This buyer is associated with {invoice_count} invoice(s).\n\n"
                        "Deleting this buyer will not delete the invoices, but will remove "
                        "the buyer reference from them.\n\n"
                        "Do you still want to proceed?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    
                    if final_reply != QMessageBox.StandardButton.Yes:
                        return
                
                buyer = session.query(Buyer).filter_by(id=buyer_id).first()
                
                if buyer:
                    session.delete(buyer)
                    session.commit()
                    
                    QMessageBox.information(
                        self, "Success", 
                        f"Buyer '{buyer_name}' deleted successfully!"
                    )
                    
                    self.load_buyers()
                    
                    # Clear form if we were editing this buyer
                    if self.editing_buyer_id == buyer_id:
                        self.clear_form()
                else:
                    QMessageBox.warning(self, "Error", "Buyer not found!")
                    
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete buyer: {str(e)}")

    def toggle_buyer_active(self):
        """Toggle active status of selected buyer"""
        current_row = self.buyers_table.currentRow()
        if current_row < 0:
            return
            
        try:
            buyer_id = int(self.buyers_table.item(current_row, 0).text())
            buyer_name = self.buyers_table.item(current_row, 1).text()
            
            session = self.db_manager.get_session()
            buyer = session.query(Buyer).filter_by(id=buyer_id).first()
            
            if buyer:
                new_status = not buyer.is_active
                buyer.is_active = new_status
                buyer.updated_at = datetime.now()
                
                session.commit()
                
                status_text = "activated" if new_status else "deactivated"
                QMessageBox.information(
                    self, "Success", 
                    f"Buyer '{buyer_name}' {status_text} successfully!"
                )
                
                self.load_buyers()
            else:
                QMessageBox.warning(self, "Error", "Buyer not found!")
                
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to toggle buyer status: {str(e)}")


class BuyerSelectionDialog(QDialog):
    """Dialog for selecting buyers from company inventory"""
    
    buyer_selected = pyqtSignal(dict)  # Emits selected buyer data
    
    def __init__(self, db_manager, company_id, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.company_id = company_id
        
        self.setWindowTitle("Select Buyer")
        self.setModal(True)
        self.resize(800, 500)
        
        self.setStyleSheet(parent.styleSheet() if parent else "")
        
        self.setup_ui()
        self.load_buyers()

    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Search and filters
        search_layout = QHBoxLayout()
        
        search_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type to search buyers...")
        self.search_edit.textChanged.connect(self.filter_buyers)
        search_layout.addWidget(self.search_edit)
        
        search_layout.addWidget(QLabel("Type:"))
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItems(["All", "Registered", "Unregistered"])
        self.type_filter_combo.currentTextChanged.connect(self.filter_buyers)
        search_layout.addWidget(self.type_filter_combo)
        
        search_layout.addWidget(QLabel("Status:"))
        self.status_filter_combo = QComboBox()
        self.status_filter_combo.addItems(["Active Only", "All", "Inactive Only"])
        self.status_filter_combo.currentTextChanged.connect(self.filter_buyers)
        search_layout.addWidget(self.status_filter_combo)
        
        layout.addLayout(search_layout)
        
        # Buyers table
        self.buyers_table = QTableWidget()
        self.buyers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.buyers_table.setAlternatingRowColors(True)
        self.buyers_table.doubleClicked.connect(self.select_buyer)
        layout.addWidget(self.buyers_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_new_btn = QPushButton("➕ Add New Buyer")
        add_new_btn.clicked.connect(self.add_new_buyer)
        button_layout.addWidget(add_new_btn)
        
        button_layout.addStretch()
        
        select_btn = QPushButton("✅ Select")
        select_btn.setProperty("style", "success")
        select_btn.clicked.connect(self.select_buyer)
        button_layout.addWidget(select_btn)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)

    def load_buyers(self):
        """Load buyers for selection"""
        try:
            session = self.db_manager.get_session()
            self.buyers = (
                session.query(Buyer)
                .filter_by(company_id=self.company_id)
                .order_by(Buyer.name)
                .all()
            )
            
            self.populate_table(self.buyers)
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load buyers: {str(e)}")

    def populate_table(self, buyers):
        """Populate table with buyers"""
        self.buyers_table.setRowCount(len(buyers))
        self.buyers_table.setColumnCount(6)
        self.buyers_table.setHorizontalHeaderLabels([
            "ID", "Name", "NTN/CNIC", "Type", "Province", "Status"
        ])
        
        for row, buyer in enumerate(buyers):
            self.buyers_table.setItem(row, 0, QTableWidgetItem(str(buyer.id)))
            self.buyers_table.setItem(row, 1, QTableWidgetItem(buyer.name or ""))
            self.buyers_table.setItem(row, 2, QTableWidgetItem(buyer.ntn_cnic or ""))
            self.buyers_table.setItem(row, 3, QTableWidgetItem(buyer.buyer_type or ""))
            self.buyers_table.setItem(row, 4, QTableWidgetItem(buyer.province or ""))
            self.buyers_table.setItem(row, 5, QTableWidgetItem(
                "Active" if buyer.is_active else "Inactive"
            ))
        
        self.buyers_table.resizeColumnsToContents()

    def filter_buyers(self):
        """Filter buyers based on search text and filters"""
        search_text = self.search_edit.text().lower()
        type_filter = self.type_filter_combo.currentText()
        status_filter = self.status_filter_combo.currentText()
        
        filtered_buyers = []
        
        for buyer in self.buyers:
            # Search filter
            if search_text and not any([
                search_text in (buyer.name or "").lower(),
                search_text in (buyer.ntn_cnic or "").lower(),
                search_text in (buyer.province or "").lower()
            ]):
                continue
            
            # Type filter
            if type_filter != "All" and buyer.buyer_type != type_filter:
                continue
            
            # Status filter
            if status_filter == "Active Only" and not buyer.is_active:
                continue
            elif status_filter == "Inactive Only" and buyer.is_active:
                continue
            
            filtered_buyers.append(buyer)
        
        self.populate_table(filtered_buyers)

    def select_buyer(self):
        """Select the current buyer"""
        current_row = self.buyers_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Information", "Please select a buyer")
            return
            
        try:
            buyer_id = int(self.buyers_table.item(current_row, 0).text())
            buyer_name = self.buyers_table.item(current_row, 1).text()
            buyer_ntn = self.buyers_table.item(current_row, 2).text()
            buyer_type = self.buyers_table.item(current_row, 3).text()
            buyer_province = self.buyers_table.item(current_row, 4).text()
            
            # Get full buyer data from database
            session = self.db_manager.get_session()
            buyer = session.query(Buyer).filter_by(id=buyer_id).first()
            
            if buyer:
                buyer_data = {
                    'id': buyer.id,
                    'name': buyer.name,
                    'ntn_cnic': buyer.ntn_cnic,
                    'buyer_type': buyer.buyer_type,
                    'province': buyer.province,
                    'city': buyer.city,
                    'phone': buyer.phone,
                    'email': buyer.email,
                    'address': buyer.address
                }
                
                self.buyer_selected.emit(buyer_data)
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "Buyer not found!")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to select buyer: {str(e)}")

    def add_new_buyer(self):
        """Add a new buyer"""
        company_data = {'ntn_cnic': self.company_id, 'name': 'Current Company'}
        dialog = BuyerManagementDialog(self.db_manager, company_data, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_buyers()  # Refresh the list


# Test the dialogs
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Mock database manager for testing
    class MockDBManager:
        def get_session(self):
            return None
    
    company_data = {
        'ntn_cnic': '1234567890123',
        'name': 'Test Company Ltd'
    }
    
    dialog = BuyerManagementDialog(MockDBManager(), company_data)
    result = dialog.exec()
    
    sys.exit(app.exec())