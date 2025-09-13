# gui/main_window.py - Updated Company-Specific Version
import sys
import json
import pandas as pd
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QLabel,
    QLineEdit, QComboBox, QGroupBox, QFormLayout, QMessageBox,
    QProgressBar, QDialog, QDialogButtonBox, QDateEdit, QFileDialog,
    QCheckBox, QFrame, QGridLayout, QHeaderView
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QDate, Qt
from PyQt6.QtGui import QFont, QPixmap, QPalette, QColor

# Import dialogs
from gui.dialogs.company_selection_dialog import CompanySelectionDialog
from gui.dialogs.invoice_dialog import FBRInvoiceDialog
from gui.dialogs.item_dialog import ItemManagementDialog

# Import core services
from fbr_core.models import DatabaseManager, Invoices, FBRQueue, FBRLogs, Item, Company
from fbr_core.fbr_service import FBRSubmissionService, FBRQueueManager


class MainWindow(QMainWindow):
    """Company-specific main window for FBR E-Invoicing System"""

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.db_manager = None
        self.current_company = None
        self.is_sandbox_mode = True  # Default to sandbox
        
        # Setup database first
        self.setup_database()
        
        # Show company selection dialog
        self.show_company_selection()
        
    def setup_database(self):
        """Setup database connection"""
        try:
            if self.config:
                connection_string = self.config.get_database_url()
            else:
                connection_string = (
                    "postgresql://neondb_owner:npg_H2hByXAgPz8n@ep-sparkling-shape-"
                    "adwmth20-pooler.c-2.us-east-1.aws.neon.tech/neondb?"
                    "sslmode=require&channel_binding=require"
                )
            
            from fbr_core.models import DatabaseManager
            self.db_manager = DatabaseManager(connection_string)
            
        except Exception as e:
            QMessageBox.critical(
                self, "Database Error", 
                f"Failed to connect to database: {str(e)}"
            )
            sys.exit(1)

    def show_company_selection(self):
        """Show company selection dialog"""
        dialog = CompanySelectionDialog(self.db_manager, self)
        dialog.company_selected.connect(self.on_company_selected)
        
        if dialog.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)  # Exit if no company selected

    def on_company_selected(self, company_data):
        """Handle company selection"""
        self.current_company = company_data
        self.setup_ui()
        self.load_company_specific_data()

    def setup_ui(self):
        """Setup the company-specific user interface"""
        self.setWindowTitle(f"FBR E-Invoicing - {self.current_company['name']}")
        self.setGeometry(100, 100, 1400, 900)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f1115;
                color: #eaeef6;
            }
            QTabWidget::pane {
                border: 1px solid #2c3b52;
                background-color: #1b2028;
            }
            QTabBar::tab {
                background-color: #1b2028;
                color: #eaeef6;
                border: 1px solid #2c3b52;
                padding: 12px 20px;
                margin-right: 2px;
                border-radius: 8px 8px 0 0;
            }
            QTabBar::tab:selected {
                background-color: #2c3b52;
                color: #ffffff;
            }
            QTabBar::tab:hover {
                background-color: #243447;
            }
            QPushButton {
                background-color: #5aa2ff;
                color: #0f1115;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #7bb6ff;
            }
            QPushButton:pressed {
                background-color: #4b92ec;
            }
            QPushButton[style="success"] {
                background-color: #28a745;
                color: white;
            }
            QPushButton[style="success"]:hover {
                background-color: #218838;
            }
            QPushButton[style="warning"] {
                background-color: #ffc107;
                color: #000;
            }
            QPushButton[style="danger"] {
                background-color: #dc3545;
                color: white;
            }
            QTableWidget {
                background-color: #1b2028;
                alternate-background-color: #243447;
                gridline-color: #2c3b52;
                color: #eaeef6;
                border: 1px solid #2c3b52;
            }
            QHeaderView::section {
                background-color: #2c3b52;
                color: #ffffff;
                border: 1px solid #334561;
                padding: 8px;
                font-weight: bold;
            }
            QGroupBox {
                background: #1b2028;
                border: 1px solid #2c3b52;
                border-radius: 10px;
                padding-top: 18px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                top: -10px;
                background: #2c3b52;
                color: #eaeef6;
                border-radius: 8px;
                padding: 2px 10px;
                font-weight: 600;
            }
            QLabel {
                color: #eaeef6;
            }
            QComboBox, QLineEdit, QDateEdit {
                background: #0f141c;
                color: #eaeef6;
                border: 1px solid #334561;
                border-radius: 6px;
                padding: 6px 10px;
                min-height: 28px;
            }
        """)

        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Company header
        self.create_company_header(layout)
        
        # Create tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # Dashboard tab
        self.dashboard_tab = self.create_dashboard_tab()
        tab_widget.addTab(self.dashboard_tab, "📊 Dashboard")

        # Invoices tab
        self.invoices_tab = self.create_invoices_tab()
        tab_widget.addTab(self.invoices_tab, "📄 Invoices")
        
        # Items Management tab
        self.items_tab = self.create_items_tab()
        tab_widget.addTab(self.items_tab, "📦 Items")

        # Queue tab
        self.queue_tab = self.create_queue_tab()
        tab_widget.addTab(self.queue_tab, "⚡ FBR Queue")

        # Logs tab
        self.logs_tab = self.create_logs_tab()
        tab_widget.addTab(self.logs_tab, "📋 FBR Logs")

        # Settings tab
        self.settings_tab = self.create_settings_tab()
        tab_widget.addTab(self.settings_tab, "⚙️ Settings")

        # Status bar
        self.statusBar().showMessage(f"Connected as: {self.current_company['name']}")
        self.statusBar().setStyleSheet("background-color: #2c3b52; color: #eaeef6; padding: 5px;")

    def create_company_header(self, parent_layout):
        """Create company information header"""
        header_frame = QFrame()
        header_frame.setMaximumHeight(100)
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #2c3b52;
                border-radius: 12px;
                margin: 5px;
            }
        """)
        
        header_layout = QHBoxLayout(header_frame)
        
        # Company info
        company_info_layout = QVBoxLayout()
        
        company_name_label = QLabel(self.current_company['name'])
        company_name_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        company_name_label.setStyleSheet("color: #ffffff; margin: 5px;")
        
        company_ntn_label = QLabel(f"NTN/CNIC: {self.current_company['ntn_cnic']}")
        company_ntn_label.setStyleSheet("color: #cccccc; margin: 2px 5px;")
        
        company_info_layout.addWidget(company_name_label)
        company_info_layout.addWidget(company_ntn_label)
        
        header_layout.addLayout(company_info_layout)
        header_layout.addStretch()
        
        # Mode toggle
        mode_layout = QVBoxLayout()
        mode_label = QLabel("Mode:")
        mode_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        
        self.sandbox_checkbox = QCheckBox("Sandbox Mode")
        self.sandbox_checkbox.setChecked(True)
        self.sandbox_checkbox.toggled.connect(self.toggle_mode)
        self.sandbox_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                color: #5aa2ff;
                font-size: 14px;
            }
            QCheckBox::indicator:checked {
                background-color: #28a745;
                border: 2px solid #28a745;
                border-radius: 4px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #dc3545;
                border: 2px solid #dc3545;
                border-radius: 4px;
            }
        """)
        
        mode_layout.addWidget(mode_label)
        mode_layout.addWidget(self.sandbox_checkbox)
        
        header_layout.addLayout(mode_layout)
        
        # Switch company button
        switch_company_btn = QPushButton("🔄 Switch Company")
        switch_company_btn.clicked.connect(self.switch_company)
        switch_company_btn.setMaximumHeight(40)
        header_layout.addWidget(switch_company_btn)
        
        parent_layout.addWidget(header_frame)

    def create_dashboard_tab(self):
        """Create company dashboard tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Stats cards
        stats_layout = QGridLayout()
        
        # Create stat cards
        stats = [
            ("Total Invoices", "0", "#5aa2ff", "📄"),
            ("Pending FBR", "0", "#ffc107", "⏳"),
            ("Successful", "0", "#28a745", "✅"),
            ("Failed", "0", "#dc3545", "❌")
        ]
        
        self.stat_labels = {}
        for i, (title, value, color, icon) in enumerate(stats):
            card = self.create_stat_card(title, value, color, icon)
            stats_layout.addWidget(card, 0, i)
            self.stat_labels[title] = card.findChild(QLabel, "value_label")
        
        layout.addLayout(stats_layout)
        
        # Recent activity
        recent_group = QGroupBox("Recent Invoice Activity")
        recent_layout = QVBoxLayout(recent_group)
        
        self.recent_table = QTableWidget()
        self.recent_table.setMaximumHeight(300)
        recent_layout.addWidget(self.recent_table)
        
        layout.addWidget(recent_group)
        
        # Quick actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QHBoxLayout(actions_group)
        
        new_invoice_btn = QPushButton("📄 New Invoice")
        new_invoice_btn.setProperty("style", "success")
        new_invoice_btn.clicked.connect(self.new_invoice)
        
        manage_items_btn = QPushButton("📦 Manage Items")
        manage_items_btn.clicked.connect(self.manage_items)
        
        process_queue_btn = QPushButton("⚡ Process Queue")
        process_queue_btn.setProperty("style", "warning")
        process_queue_btn.clicked.connect(self.process_fbr_queue)
        
        actions_layout.addWidget(new_invoice_btn)
        actions_layout.addWidget(manage_items_btn)
        actions_layout.addWidget(process_queue_btn)
        actions_layout.addStretch()
        
        layout.addWidget(actions_group)
        layout.addStretch()
        
        return widget

    def create_stat_card(self, title, value, color, icon):
        """Create a statistics card"""
        card = QFrame()
        card.setFixedHeight(120)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1b2028;
                border-left: 4px solid {color};
                border-radius: 8px;
                margin: 5px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        # Icon and title
        header_layout = QHBoxLayout()
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"color: {color}; font-size: 24px;")
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #cccccc; font-size: 12px; font-weight: bold;")
        
        header_layout.addWidget(icon_label)
        header_layout.addStretch()
        header_layout.addWidget(title_label)
        
        layout.addLayout(header_layout)
        
        # Value
        value_label = QLabel(value)
        value_label.setObjectName("value_label")
        value_label.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: bold;")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(value_label)
        layout.addStretch()
        
        return card

    def create_invoices_tab(self):
        """Create the invoices management tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Toolbar
        toolbar_layout = QHBoxLayout()

        new_invoice_btn = QPushButton("📄 New Invoice")
        new_invoice_btn.setProperty("style", "success")
        new_invoice_btn.clicked.connect(self.new_invoice)
        toolbar_layout.addWidget(new_invoice_btn)

        edit_invoice_btn = QPushButton("✏️ Edit Invoice")
        edit_invoice_btn.clicked.connect(self.edit_invoice)
        toolbar_layout.addWidget(edit_invoice_btn)

        validate_invoice_btn = QPushButton("✅ Validate Invoice")
        validate_invoice_btn.setProperty("style", "warning")
        validate_invoice_btn.clicked.connect(self.validate_invoice)
        toolbar_layout.addWidget(validate_invoice_btn)

        submit_to_fbr_btn = QPushButton("🚀 Submit to FBR")
        submit_to_fbr_btn.setProperty("style", "success")
        submit_to_fbr_btn.clicked.connect(self.submit_selected_to_fbr)
        toolbar_layout.addWidget(submit_to_fbr_btn)

        toolbar_layout.addStretch()

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_invoices_table)
        toolbar_layout.addWidget(refresh_btn)

        layout.addLayout(toolbar_layout)

        # Invoices table
        self.invoices_table = QTableWidget()
        self.invoices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.invoices_table.setAlternatingRowColors(True)
        layout.addWidget(self.invoices_table)

        return widget

    def create_items_tab(self):
        """Create items management tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        add_item_btn = QPushButton("➕ Add Item")
        add_item_btn.setProperty("style", "success")
        add_item_btn.clicked.connect(self.add_item)
        toolbar_layout.addWidget(add_item_btn)
        
        edit_item_btn = QPushButton("✏️ Edit Item")
        edit_item_btn.clicked.connect(self.edit_item)
        toolbar_layout.addWidget(edit_item_btn)
        
        delete_item_btn = QPushButton("🗑️ Delete Item")
        delete_item_btn.setProperty("style", "danger")
        delete_item_btn.clicked.connect(self.delete_item)
        toolbar_layout.addWidget(delete_item_btn)
        
        toolbar_layout.addStretch()
        
        refresh_items_btn = QPushButton("🔄 Refresh")
        refresh_items_btn.clicked.connect(self.refresh_items_table)
        toolbar_layout.addWidget(refresh_items_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Items table
        self.items_table = QTableWidget()
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.items_table.setAlternatingRowColors(True)
        layout.addWidget(self.items_table)
        
        return widget

    def create_queue_tab(self):
        """Create FBR queue tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Queue controls
        controls_layout = QHBoxLayout()

        process_queue_btn = QPushButton("⚡ Process Queue")
        process_queue_btn.setProperty("style", "success")
        process_queue_btn.clicked.connect(self.process_fbr_queue)
        controls_layout.addWidget(process_queue_btn)

        retry_failed_btn = QPushButton("🔄 Retry Failed")
        retry_failed_btn.setProperty("style", "warning")
        retry_failed_btn.clicked.connect(self.retry_failed_items)
        controls_layout.addWidget(retry_failed_btn)

        clear_completed_btn = QPushButton("🧹 Clear Completed")
        clear_completed_btn.clicked.connect(self.clear_completed_queue_items)
        controls_layout.addWidget(clear_completed_btn)

        controls_layout.addStretch()

        # Progress bar
        self.queue_progress = QProgressBar()
        self.queue_progress.setVisible(False)
        controls_layout.addWidget(self.queue_progress)

        layout.addLayout(controls_layout)

        # Queue table
        self.queue_table = QTableWidget()
        self.queue_table.setAlternatingRowColors(True)
        layout.addWidget(self.queue_table)

        return widget

    def create_logs_tab(self):
        """Create FBR logs tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Logs controls
        controls_layout = QHBoxLayout()

        filter_combo = QComboBox()
        filter_combo.addItems(["All", "Success", "Invalid", "Error", "Timeout"])
        controls_layout.addWidget(QLabel("Filter:"))
        controls_layout.addWidget(filter_combo)

        export_logs_btn = QPushButton("📊 Export Logs")
        export_logs_btn.clicked.connect(self.export_logs)
        controls_layout.addWidget(export_logs_btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Logs table
        self.logs_table = QTableWidget()
        self.logs_table.setAlternatingRowColors(True)
        layout.addWidget(self.logs_table)

        return widget

    def create_settings_tab(self):
        """Create settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # FBR API Settings
        api_group = QGroupBox("FBR API Settings")
        api_layout = QFormLayout(api_group)

        self.api_endpoint_edit = QLineEdit()
        self.api_endpoint_edit.setPlaceholderText("https://api.fbr.gov.pk/einvoicing")
        
        self.auth_token_edit = QLineEdit()
        self.auth_token_edit.setPlaceholderText("Enter your authorization token")
        
        self.login_id_edit = QLineEdit()
        self.login_id_edit.setPlaceholderText("Enter your login ID")
        
        self.login_password_edit = QLineEdit()
        self.login_password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        api_layout.addRow("API Endpoint:", self.api_endpoint_edit)
        api_layout.addRow("Authorization Token:", self.auth_token_edit)
        api_layout.addRow("Login ID:", self.login_id_edit)
        api_layout.addRow("Login Password:", self.login_password_edit)

        layout.addWidget(api_group)

        # Save button
        save_settings_btn = QPushButton("💾 Save Settings")
        save_settings_btn.setProperty("style", "success")
        save_settings_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_settings_btn)
        
        layout.addStretch()
        
        return widget

    def load_company_specific_data(self):
        """Load all company-specific data"""
        if not self.current_company:
            return
            
        try:
            # Load dashboard stats
            self.update_dashboard_stats()
            
            # Load tables
            self.refresh_invoices_table()
            self.refresh_items_table() 
            self.refresh_queue_table()
            self.refresh_logs_table()
            
            # Load settings
            self.load_settings()
            
        except Exception as e:
            QMessageBox.critical(self, "Data Load Error", 
                               f"Failed to load company data: {str(e)}")

    def update_dashboard_stats(self):
        """Update dashboard statistics"""
        try:
            session = self.db_manager.get_session()
            company_id = self.current_company['ntn_cnic']
            
            # Count invoices
            total_invoices = session.query(Invoices).filter_by(company_id=company_id).count()
            pending_fbr = session.query(Invoices).filter_by(
                company_id=company_id, 
                fbr_status=None
            ).count()
            successful = session.query(Invoices).filter_by(
                company_id=company_id, 
                fbr_status='Valid'
            ).count()
            failed = session.query(Invoices).filter_by(
                company_id=company_id, 
                fbr_status='Invalid'
            ).count()
            
            # Update stat cards
            self.stat_labels["Total Invoices"].setText(str(total_invoices))
            self.stat_labels["Pending FBR"].setText(str(pending_fbr))
            self.stat_labels["Successful"].setText(str(successful))
            self.stat_labels["Failed"].setText(str(failed))
            
        except Exception as e:
            print(f"Error updating dashboard stats: {e}")

    def toggle_mode(self, checked):
        """Toggle between Sandbox and Production mode"""
        self.is_sandbox_mode = checked
        mode_text = "Sandbox" if checked else "Production"
        self.statusBar().showMessage(
            f"Connected as: {self.current_company['name']} - Mode: {mode_text}"
        )

    def switch_company(self):
        """Switch to a different company"""
        self.show_company_selection()

    def new_invoice(self):
        """Create new invoice with seller details auto-filled"""
        mode = "sandbox" if self.is_sandbox_mode else "production"
        
        # Pre-fill seller details from selected company
        seller_data = {
            'sellerNTNCNIC': self.current_company['ntn_cnic'],
            'sellerBusinessName': self.current_company['name'],
            'sellerAddress': self.current_company['address']
        }
        
        dialog = FBRInvoiceDialog(
            self, 
            mode=mode, 
            company_data=self.current_company,
            seller_data=seller_data
        )
        dialog.invoice_saved.connect(self.on_invoice_saved)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_invoices_table()
            self.update_dashboard_stats()

    def edit_invoice(self):
        """Edit selected invoice"""
        current_row = self.invoices_table.currentRow()
        if current_row >= 0:
            invoice_id = int(self.invoices_table.item(current_row, 0).text())
            # Implementation for editing invoice
            pass
        else:
            QMessageBox.information(self, "Information", "Please select an invoice to edit")

    def validate_invoice(self):
        """Validate selected invoice using FBR API"""
        current_row = self.invoices_table.currentRow()
        if current_row >= 0:
            invoice_id = int(self.invoices_table.item(current_row, 0).text())
            self.validate_invoice_with_fbr(invoice_id)
        else:
            QMessageBox.information(self, "Information", "Please select an invoice to validate")

    def validate_invoice_with_fbr(self, invoice_id):
        """Validate invoice with FBR API"""
        try:
            # Get invoice data
            session = self.db_manager.get_session()
            invoice = session.query(Invoices).filter_by(id=invoice_id).first()
            
            if not invoice:
                QMessageBox.warning(self, "Error", "Invoice not found!")
                return
            
            # Call FBR validation endpoint
            validation_url = "https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata_sb"
            
            # Build payload (similar to submission payload)
            payload = self.build_validation_payload(invoice)
            
            # Make API call
            import requests
            headers = {
                'Authorization': f'Bearer {self.get_auth_token()}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(validation_url, json=payload, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                status = result.get('validationResponse', {}).get('status', 'Unknown')
                
                QMessageBox.information(
                    self, "Validation Result", 
                    f"Invoice validation result: {status}"
                )
                
                # Update invoice validation status if needed
                invoice.fbr_status = status
                session.commit()
                
                self.refresh_invoices_table()
                
            else:
                QMessageBox.warning(
                    self, "Validation Error", 
                    f"Validation failed: {response.status_code} - {response.text}"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Validation Error", f"Failed to validate invoice: {str(e)}")

    def build_validation_payload(self, invoice):
        """Build payload for FBR validation"""
        # This should build the same payload structure as for submission
        # Implementation depends on your invoice data structure
        return {
            "invoiceType": "Sale Invoice",
            "invoiceDate": invoice.posting_date.strftime('%Y-%m-%d'),
            # ... other fields based on your invoice structure
        }

    def get_auth_token(self):
        """Get authentication token for FBR API"""
        return self.auth_token_edit.text().strip()

    def submit_selected_to_fbr(self):
        """Submit selected invoices to FBR"""
        selected_rows = set()
        for item in self.invoices_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(self, "Warning", "Please select invoices to submit")
            return

        invoice_ids = []
        for row in selected_rows:
            invoice_id = int(self.invoices_table.item(row, 0).text())
            invoice_ids.append(invoice_id)

        mode = "Sandbox" if self.is_sandbox_mode else "Production"
        reply = QMessageBox.question(
            self,
            "Confirm Submission",
            f"Submit {len(invoice_ids)} invoice(s) to FBR in {mode} mode?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.submit_invoices_to_fbr(invoice_ids)

    def submit_invoices_to_fbr(self, invoice_ids):
        """Submit invoices to FBR"""
        # Implementation for FBR submission
        pass

    def manage_items(self):
        """Open item management dialog"""
        dialog = ItemManagementDialog(self.db_manager, self.current_company['ntn_cnic'], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_items_table()

    def add_item(self):
        """Add new item"""
        self.manage_items()

    def edit_item(self):
        """Edit selected item"""
        current_row = self.items_table.currentRow()
        if current_row >= 0:
            # Implementation for editing item
            pass

    def delete_item(self):
        """Delete selected item"""
        current_row = self.items_table.currentRow()
        if current_row >= 0:
            # Implementation for deleting item
            pass

    def refresh_invoices_table(self):
        """Refresh invoices table with company-specific data"""
        if not self.db_manager or not self.current_company:
            return

        try:
            session = self.db_manager.get_session()
            company_id = self.current_company['ntn_cnic']
            
            invoices = (
                session.query(Invoices)
                .filter_by(company_id=company_id)
                .order_by(Invoices.created_at.desc())
                .limit(100)
                .all()
            )

            self.invoices_table.setRowCount(len(invoices))
            self.invoices_table.setColumnCount(8)
            self.invoices_table.setHorizontalHeaderLabels([
                "ID", "Invoice Number", "Customer NTN", "Date",
                "Amount", "FBR Status", "FBR Invoice No", "Mode"
            ])

            for row, invoice in enumerate(invoices):
                self.invoices_table.setItem(row, 0, QTableWidgetItem(str(invoice.id)))
                self.invoices_table.setItem(row, 1, QTableWidgetItem(invoice.invoice_number or ""))
                self.invoices_table.setItem(row, 2, QTableWidgetItem(str(invoice.customer_id or "")))
                self.invoices_table.setItem(row, 3, QTableWidgetItem(
                    invoice.posting_date.strftime("%Y-%m-%d") if invoice.posting_date else ""
                ))
                self.invoices_table.setItem(row, 4, QTableWidgetItem(
                    f"{invoice.grand_total:.2f}" if invoice.grand_total else "0.00"
                ))
                
                # Color code FBR status
                status_item = QTableWidgetItem(invoice.fbr_status or "Pending")
                if invoice.fbr_status == "Valid":
                    status_item.setBackground(QColor("#28a745"))
                elif invoice.fbr_status == "Invalid":
                    status_item.setBackground(QColor("#dc3545"))
                else:
                    status_item.setBackground(QColor("#ffc107"))
                    
                self.invoices_table.setItem(row, 5, status_item)
                self.invoices_table.setItem(row, 6, QTableWidgetItem(invoice.fbr_invoice_number or ""))
                self.invoices_table.setItem(row, 7, QTableWidgetItem(
                    "Sandbox" if self.is_sandbox_mode else "Production"
                ))

            self.invoices_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"Error refreshing invoices table: {e}")

    def refresh_items_table(self):
        """Refresh items table with company-specific data"""
        if not self.db_manager or not self.current_company:
            return

        try:
            session = self.db_manager.get_session()
            company_id = self.current_company['ntn_cnic']
            
            items = (
                session.query(Item)
                .filter_by(company_id=company_id)
                .order_by(Item.created_at.desc())
                .all()
            )

            self.items_table.setRowCount(len(items))
            self.items_table.setColumnCount(5)
            self.items_table.setHorizontalHeaderLabels([
                "ID", "Name", "HS Code", "UoM", "Created"
            ])

            for row, item in enumerate(items):
                self.items_table.setItem(row, 0, QTableWidgetItem(str(item.id)))
                self.items_table.setItem(row, 1, QTableWidgetItem(item.name or ""))
                self.items_table.setItem(row, 2, QTableWidgetItem(item.hs_code or ""))
                self.items_table.setItem(row, 3, QTableWidgetItem(item.uom or ""))
                self.items_table.setItem(row, 4, QTableWidgetItem(
                    item.created_at.strftime("%Y-%m-%d") if item.created_at else ""
                ))

            self.items_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"Error refreshing items table: {e}")

    def refresh_queue_table(self):
        """Refresh queue table with company-specific data"""
        if not self.db_manager or not self.current_company:
            return

        try:
            session = self.db_manager.get_session()
            company_id = self.current_company['ntn_cnic']
            
            queue_items = (
                session.query(FBRQueue)
                .filter_by(company_id=company_id)
                .order_by(FBRQueue.created_at.desc())
                .limit(100)
                .all()
            )

            self.queue_table.setRowCount(len(queue_items))
            self.queue_table.setColumnCount(6)
            self.queue_table.setHorizontalHeaderLabels([
                "ID", "Document", "Status", "Priority", "Retries", "Created"
            ])

            for row, item in enumerate(queue_items):
                self.queue_table.setItem(row, 0, QTableWidgetItem(str(item.id)))
                self.queue_table.setItem(row, 1, QTableWidgetItem(
                    f"{item.document_type} {item.document_id}"
                ))
                
                # Color code status
                status_item = QTableWidgetItem(item.status)
                if item.status == "Completed":
                    status_item.setBackground(QColor("#28a745"))
                elif item.status == "Failed":
                    status_item.setBackground(QColor("#dc3545"))
                elif item.status == "Processing":
                    status_item.setBackground(QColor("#17a2b8"))
                else:
                    status_item.setBackground(QColor("#ffc107"))
                    
                self.queue_table.setItem(row, 2, status_item)
                self.queue_table.setItem(row, 3, QTableWidgetItem(str(item.priority)))
                self.queue_table.setItem(row, 4, QTableWidgetItem(
                    f"{item.retry_count}/{item.max_retries}"
                ))
                self.queue_table.setItem(row, 5, QTableWidgetItem(
                    item.created_at.strftime("%Y-%m-%d %H:%M") if item.created_at else ""
                ))

            self.queue_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"Error refreshing queue table: {e}")

    def refresh_logs_table(self):
        """Refresh logs table with company-specific data"""
        if not self.db_manager or not self.current_company:
            return

        try:
            session = self.db_manager.get_session()
            company_id = self.current_company['ntn_cnic']
            
            logs = (
                session.query(FBRLogs)
                .filter_by(company_id=company_id)
                .order_by(FBRLogs.submitted_at.desc())
                .limit(100)
                .all()
            )

            self.logs_table.setRowCount(len(logs))
            self.logs_table.setColumnCount(6)
            self.logs_table.setHorizontalHeaderLabels([
                "ID", "Document", "FBR Invoice No", "Status", "Submitted", "Processing Time"
            ])

            for row, log in enumerate(logs):
                self.logs_table.setItem(row, 0, QTableWidgetItem(str(log.id)))
                self.logs_table.setItem(row, 1, QTableWidgetItem(
                    f"{log.document_type} {log.document_id}"
                ))
                self.logs_table.setItem(row, 2, QTableWidgetItem(log.fbr_invoice_number or ""))
                
                # Color code status
                status_item = QTableWidgetItem(log.status)
                if log.status == "Success":
                    status_item.setBackground(QColor("#28a745"))
                elif log.status in ["Invalid", "Error"]:
                    status_item.setBackground(QColor("#dc3545"))
                else:
                    status_item.setBackground(QColor("#ffc107"))
                    
                self.logs_table.setItem(row, 3, status_item)
                self.logs_table.setItem(row, 4, QTableWidgetItem(
                    log.submitted_at.strftime("%Y-%m-%d %H:%M") if log.submitted_at else ""
                ))
                self.logs_table.setItem(row, 5, QTableWidgetItem(
                    f"{log.processing_time:.2f}ms" if log.processing_time else ""
                ))

            self.logs_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"Error refreshing logs table: {e}")

    def process_fbr_queue(self):
        """Process FBR queue for current company"""
        if not self.db_manager or not self.current_company:
            return

        try:
            queue_manager = FBRQueueManager(self.db_manager)
            # Filter by company in the queue processing
            result = queue_manager.process_queue_for_company(
                self.current_company['ntn_cnic']
            )

            message = (
                f"Queue processing completed.\n"
                f"Processed: {result.get('processed_count', 0)} items"
            )
            if "error" in result:
                message += f"\nError: {result['error']}"

            QMessageBox.information(self, "Queue Processing", message)
            self.refresh_queue_table()
            self.refresh_logs_table()
            self.update_dashboard_stats()
            
        except Exception as e:
            QMessageBox.critical(self, "Queue Error", f"Failed to process queue: {str(e)}")

    def retry_failed_items(self):
        """Retry failed queue items"""
        # Implementation for retrying failed items
        pass

    def clear_completed_queue_items(self):
        """Clear completed queue items"""
        # Implementation for clearing completed items
        pass

    def export_logs(self):
        """Export logs to CSV"""
        # Implementation for exporting logs
        pass

    def load_settings(self):
        """Load FBR settings for current company"""
        if not self.db_manager or not self.current_company:
            return
            
        try:
            session = self.db_manager.get_session()
            from fbr_core.models import FBRSettings
            
            settings = (
                session.query(FBRSettings)
                .filter_by(company_id=self.current_company['ntn_cnic'])
                .first()
            )
            
            if settings:
                self.api_endpoint_edit.setText(settings.api_endpoint or "")
                self.auth_token_edit.setText(settings.pral_authorization_token or "")
                self.login_id_edit.setText(settings.pral_login_id or "")
                self.login_password_edit.setText(settings.pral_login_password or "")
                
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self):
        """Save FBR settings for current company"""
        if not self.db_manager or not self.current_company:
            QMessageBox.warning(self, "Warning", "No company selected")
            return
            
        try:
            session = self.db_manager.get_session()
            from fbr_core.models import FBRSettings
            
            settings = (
                session.query(FBRSettings)
                .filter_by(company_id=self.current_company['ntn_cnic'])
                .first()
            )
            
            if not settings:
                settings = FBRSettings(company_id=self.current_company['ntn_cnic'])
                session.add(settings)
            
            # Update settings
            settings.api_endpoint = self.api_endpoint_edit.text().strip()
            settings.pral_authorization_token = self.auth_token_edit.text().strip()
            settings.pral_login_id = self.login_id_edit.text().strip()
            settings.pral_login_password = self.login_password_edit.text().strip()
            settings.updated_at = datetime.now()
            
            session.commit()
            
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

    def on_invoice_saved(self, invoice_data):
        """Handle when an invoice is saved"""
        try:
            # Save to database with company_id
            invoice_data['company_id'] = self.current_company['ntn_cnic']
            
            # Implementation for saving invoice
            self.refresh_invoices_table()
            self.update_dashboard_stats()
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save invoice: {str(e)}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("FBR E-Invoicing System")
    app.setApplicationVersion("1.0.0")

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()