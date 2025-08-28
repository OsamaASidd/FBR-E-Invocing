import sys
import json
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QTableWidget, QTableWidgetItem, 
                             QTabWidget, QLabel, QLineEdit, QComboBox, QTextEdit,
                             QGroupBox, QFormLayout, QMessageBox, QProgressBar,
                             QDialog, QDialogButtonBox, QGridLayout, QDateEdit,
                             QSpinBox, QDoubleSpinBox)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt, QDate
from PyQt6.QtGui import QFont, QIcon

from fbr_core.models import DatabaseManager, SalesInvoice, FBRQueue, FBRLogs
from fbr_core.fbr_service import FBRSubmissionService, FBRQueueManager

class FBRSubmissionThread(QThread):
    """Background thread for FBR submissions"""
    progress_updated = pyqtSignal(str)
    submission_completed = pyqtSignal(dict)
    
    def __init__(self, db_manager, invoice_ids, document_type):
        super().__init__()
        self.db_manager = db_manager
        self.invoice_ids = invoice_ids
        self.document_type = document_type
        self.submission_service = FBRSubmissionService(db_manager)
    
    def run(self):
        results = {"successful": 0, "failed": 0, "errors": []}
        
        for invoice_id in self.invoice_ids:
            self.progress_updated.emit(f"Processing invoice {invoice_id}...")
            
            result = self.submission_service.submit_invoice(invoice_id, self.document_type)
            
            if result["success"]:
                results["successful"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"Invoice {invoice_id}: {result.get('error', 'Unknown error')}")
        
        self.submission_completed.emit(results)

class InvoiceDialog(QDialog):
    """Dialog for creating/editing invoices"""
    
    def __init__(self, db_manager, parent=None, invoice_id=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.invoice_id = invoice_id
        self.setWindowTitle("Invoice Details")
        self.setModal(True)
        self.resize(600, 500)
        self.setup_ui()
        
        if invoice_id:
            self.load_invoice_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Form layout for invoice details
        form_group = QGroupBox("Invoice Information")
        form_layout = QFormLayout(form_group)
        
        self.invoice_number_edit = QLineEdit()
        self.customer_combo = QComboBox()
        self.company_combo = QComboBox()
        self.posting_date_edit = QDateEdit(QDate.currentDate())
        self.due_date_edit = QDateEdit(QDate.currentDate().addDays(30))
        self.province_combo = QComboBox()
        
        # Populate combos
        self.populate_combos()
        
        form_layout.addRow("Invoice Number:", self.invoice_number_edit)
        form_layout.addRow("Customer:", self.customer_combo)
        form_layout.addRow("Company:", self.company_combo)
        form_layout.addRow("Posting Date:", self.posting_date_edit)
        form_layout.addRow("Due Date:", self.due_date_edit)
        form_layout.addRow("Province:", self.province_combo)
        
        layout.addWidget(form_group)
        
        # Items section
        items_group = QGroupBox("Items")
        items_layout = QVBoxLayout(items_group)
        
        # Items table
        self.items_table = QTableWidget(0, 6)
        self.items_table.setHorizontalHeaderLabels([
            "Item", "Quantity", "Rate", "Amount", "Tax Rate", "HS Code"
        ])
        items_layout.addWidget(self.items_table)
        
        # Add item button
        add_item_btn = QPushButton("Add Item")
        add_item_btn.clicked.connect(self.add_item_row)
        items_layout.addWidget(add_item_btn)
        
        layout.addWidget(items_group)
        
        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                  QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def populate_combos(self):
        # In a real application, populate from database
        self.customer_combo.addItems(["Customer 1", "Customer 2", "Customer 3"])
        self.company_combo.addItems(["Company A", "Company B"])
        self.province_combo.addItems(["Punjab", "Sindh", "KPK", "Balochistan"])
    
    def add_item_row(self):
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        
        # Add default values
        self.items_table.setItem(row, 0, QTableWidgetItem(""))  # Item
        self.items_table.setItem(row, 1, QTableWidgetItem("1"))  # Quantity
        self.items_table.setItem(row, 2, QTableWidgetItem("0.00"))  # Rate
        self.items_table.setItem(row, 3, QTableWidgetItem("0.00"))  # Amount
        self.items_table.setItem(row, 4, QTableWidgetItem("0.00"))  # Tax Rate
        self.items_table.setItem(row, 5, QTableWidgetItem(""))  # HS Code
    
    def load_invoice_data(self):
        # Load existing invoice data
        session = self.db_manager.get_session()
        invoice = session.query(SalesInvoice).filter_by(id=self.invoice_id).first()
        
        if invoice:
            self.invoice_number_edit.setText(invoice.invoice_number)
            # Set other fields...

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.db_manager = None
        self.setup_ui()
        self.setup_database()
        self.setup_timers()
        
    def setup_ui(self):
        self.setWindowTitle("FBR E-Invoicing System")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # Invoices tab
        self.invoices_tab = self.create_invoices_tab()
        tab_widget.addTab(self.invoices_tab, "Sales Invoices")
        
        # Queue tab
        self.queue_tab = self.create_queue_tab()
        tab_widget.addTab(self.queue_tab, "FBR Queue")
        
        # Logs tab
        self.logs_tab = self.create_logs_tab()
        tab_widget.addTab(self.logs_tab, "FBR Logs")
        
        # Settings tab
        self.settings_tab = self.create_settings_tab()
        tab_widget.addTab(self.settings_tab, "Settings")
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def create_invoices_tab(self):
        """Create the invoices tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        new_invoice_btn = QPushButton("New Invoice")
        new_invoice_btn.clicked.connect(self.new_invoice)
        toolbar_layout.addWidget(new_invoice_btn)
        
        edit_invoice_btn = QPushButton("Edit Invoice")
        edit_invoice_btn.clicked.connect(self.edit_invoice)
        toolbar_layout.addWidget(edit_invoice_btn)
        
        submit_to_fbr_btn = QPushButton("Submit to FBR")
        submit_to_fbr_btn.clicked.connect(self.submit_selected_to_fbr)
        toolbar_layout.addWidget(submit_to_fbr_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_invoices_table)
        toolbar_layout.addWidget(refresh_btn)
        
        toolbar_layout.addStretch()
        layout.addLayout(toolbar_layout)
        
        # Invoices table
        self.invoices_table = QTableWidget()
        self.invoices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.invoices_table)
        
        return widget
    
    def create_queue_tab(self):
        """Create the queue management tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Queue controls
        controls_layout = QHBoxLayout()
        
        process_queue_btn = QPushButton("Process Queue")
        process_queue_btn.clicked.connect(self.process_fbr_queue)
        controls_layout.addWidget(process_queue_btn)
        
        retry_failed_btn = QPushButton("Retry Failed")
        retry_failed_btn.clicked.connect(self.retry_failed_items)
        controls_layout.addWidget(retry_failed_btn)
        
        clear_completed_btn = QPushButton("Clear Completed")
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
        layout.addWidget(self.queue_table)
        
        return widget
    
    def create_logs_tab(self):
        """Create the logs tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Logs controls
        controls_layout = QHBoxLayout()
        
        filter_combo = QComboBox()
        filter_combo.addItems(["All", "Success", "Invalid", "Error", "Timeout"])
        controls_layout.addWidget(QLabel("Filter:"))
        controls_layout.addWidget(filter_combo)
        
        export_logs_btn = QPushButton("Export Logs")
        export_logs_btn.clicked.connect(self.export_logs)
        controls_layout.addWidget(export_logs_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Logs table
        self.logs_table = QTableWidget()
        layout.addWidget(self.logs_table)
        
        return widget
    
    def create_settings_tab(self):
        """Create the settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # FBR API Settings
        api_group = QGroupBox("FBR API Settings")
        api_layout = QFormLayout(api_group)
        
        self.api_endpoint_edit = QLineEdit()
        self.auth_token_edit = QLineEdit()
        self.login_id_edit = QLineEdit()
        self.login_password_edit = QLineEdit()
        self.login_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        
        api_layout.addRow("API Endpoint:", self.api_endpoint_edit)
        api_layout.addRow("Authorization Token:", self.auth_token_edit)
        api_layout.addRow("Login ID:", self.login_id_edit)
        api_layout.addRow("Login Password:", self.login_password_edit)
        
        layout.addWidget(api_group)
        
        # Save settings button
        save_settings_btn = QPushButton("Save Settings")
        save_settings_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_settings_btn)
        
        layout.addStretch()
        return widget
    
    def setup_database(self):
        """Setup database connection"""
        try:
            # Use Neon PostgreSQL connection
            connection_string = "postgresql://neondb_owner:npg_H2hByXAgPz8n@ep-sparkling-shape-adwmth20-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
            self.db_manager = DatabaseManager(connection_string)
            self.statusBar().showMessage("Database connected successfully")
            
            # Load initial data
            self.refresh_invoices_table()
            self.refresh_queue_table()
            self.refresh_logs_table()
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to connect to database: {str(e)}")
    
    def setup_timers(self):
        """Setup auto-refresh timers"""
        # Refresh tables every 30 seconds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh)
        self.refresh_timer.start(30000)  # 30 seconds
    
    def auto_refresh(self):
        """Auto refresh tables"""
        self.refresh_queue_table()
        self.refresh_logs_table()
    
    def new_invoice(self):
        """Create new invoice"""
        dialog = InvoiceDialog(self.db_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Save invoice logic here
            self.refresh_invoices_table()
    
    def edit_invoice(self):
        """Edit selected invoice"""
        current_row = self.invoices_table.currentRow()
        if current_row >= 0:
            invoice_id = self.invoices_table.item(current_row, 0).text()
            dialog = InvoiceDialog(self.db_manager, self, invoice_id)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.refresh_invoices_table()
    
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
        
        # Start background submission
        self.submission_thread = FBRSubmissionThread(self.db_manager, invoice_ids, "Sales Invoice")
        self.submission_thread.progress_updated.connect(self.update_submission_progress)
        self.submission_thread.submission_completed.connect(self.submission_completed)
        self.submission_thread.start()
        
        # Show progress
        self.queue_progress.setVisible(True)
        self.queue_progress.setRange(0, 0)  # Indeterminate progress
    
    def update_submission_progress(self, message):
        """Update submission progress"""
        self.statusBar().showMessage(message)
    
    def submission_completed(self, results):
        """Handle submission completion"""
        self.queue_progress.setVisible(False)
        self.statusBar().showMessage("Submission completed")
        
        message = f"Submission completed:\nSuccessful: {results['successful']}\nFailed: {results['failed']}"
        if results['errors']:
            message += f"\n\nErrors:\n" + "\n".join(results['errors'][:5])  # Show first 5 errors
        
        QMessageBox.information(self, "Submission Complete", message)
        self.refresh_invoices_table()
        self.refresh_queue_table()
    
    def process_fbr_queue(self):
        """Process FBR queue"""
        if not self.db_manager:
            return
        
        queue_manager = FBRQueueManager(self.db_manager)
        result = queue_manager.process_queue()
        
        message = f"Queue processing completed.\nProcessed: {result.get('processed_count', 0)} items"
        if 'error' in result:
            message += f"\nError: {result['error']}"
        
        QMessageBox.information(self, "Queue Processing", message)
        self.refresh_queue_table()
        self.refresh_logs_table()
    
    def refresh_invoices_table(self):
        """Refresh invoices table"""
        if not self.db_manager:
            return
        
        session = self.db_manager.get_session()
        invoices = session.query(SalesInvoice).order_by(SalesInvoice.created_at.desc()).limit(100).all()
        
        self.invoices_table.setRowCount(len(invoices))
        self.invoices_table.setColumnCount(7)
        self.invoices_table.setHorizontalHeaderLabels([
            "ID", "Invoice Number", "Customer", "Date", "Amount", "FBR Status", "FBR Invoice No"
        ])
        
        for row, invoice in enumerate(invoices):
            self.invoices_table.setItem(row, 0, QTableWidgetItem(str(invoice.id)))
            self.invoices_table.setItem(row, 1, QTableWidgetItem(invoice.invoice_number))
            self.invoices_table.setItem(row, 2, QTableWidgetItem(str(invoice.customer_id)))  # Get customer name
            self.invoices_table.setItem(row, 3, QTableWidgetItem(invoice.posting_date.strftime('%Y-%m-%d') if invoice.posting_date else ""))
            self.invoices_table.setItem(row, 4, QTableWidgetItem(f"{invoice.grand_total:.2f}" if invoice.grand_total else "0.00"))
            self.invoices_table.setItem(row, 5, QTableWidgetItem(invoice.fbr_status or ""))
            self.invoices_table.setItem(row, 6, QTableWidgetItem(invoice.fbr_invoice_number or ""))
        
        self.invoices_table.resizeColumnsToContents()
    
    def refresh_queue_table(self):
        """Refresh queue table"""
        if not self.db_manager:
            return
        
        session = self.db_manager.get_session()
        queue_items = session.query(FBRQueue).order_by(FBRQueue.created_at.desc()).limit(100).all()
        
        self.queue_table.setRowCount(len(queue_items))
        self.queue_table.setColumnCount(6)
        self.queue_table.setHorizontalHeaderLabels([
            "ID", "Document", "Status", "Priority", "Retries", "Created"
        ])
        
        for row, item in enumerate(queue_items):
            self.queue_table.setItem(row, 0, QTableWidgetItem(str(item.id)))
            self.queue_table.setItem(row, 1, QTableWidgetItem(f"{item.document_type} {item.document_id}"))
            self.queue_table.setItem(row, 2, QTableWidgetItem(item.status))
            self.queue_table.setItem(row, 3, QTableWidgetItem(str(item.priority)))
            self.queue_table.setItem(row, 4, QTableWidgetItem(f"{item.retry_count}/{item.max_retries}"))
            self.queue_table.setItem(row, 5, QTableWidgetItem(item.created_at.strftime('%Y-%m-%d %H:%M') if item.created_at else ""))
        
        self.queue_table.resizeColumnsToContents()
    
    def refresh_logs_table(self):
        """Refresh logs table"""
        if not self.db_manager:
            return
        
        session = self.db_manager.get_session()
        logs = session.query(FBRLogs).order_by(FBRLogs.submitted_at.desc()).limit(100).all()
        
        self.logs_table.setRowCount(len(logs))
        self.logs_table.setColumnCount(6)
        self.logs_table.setHorizontalHeaderLabels([
            "ID", "Document", "FBR Invoice No", "Status", "Submitted", "Processing Time"
        ])
        
        for row, log in enumerate(logs):
            self.logs_table.setItem(row, 0, QTableWidgetItem(str(log.id)))
            self.logs_table.setItem(row, 1, QTableWidgetItem(f"{log.document_type} {log.document_id}"))
            self.logs_table.setItem(row, 2, QTableWidgetItem(log.fbr_invoice_number or ""))
            self.logs_table.setItem(row, 3, QTableWidgetItem(log.status))
            self.logs_table.setItem(row, 4, QTableWidgetItem(log.submitted_at.strftime('%Y-%m-%d %H:%M') if log.submitted_at else ""))
            self.logs_table.setItem(row, 5, QTableWidgetItem(f"{log.processing_time:.2f}ms" if log.processing_time else ""))
        
        self.logs_table.resizeColumnsToContents()
    
    def save_settings(self):
        """Save FBR settings"""
        # Implementation for saving settings
        QMessageBox.information(self, "Settings", "Settings saved successfully")
    
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

def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("FBR E-Invoicing System")
    app.setApplicationVersion("1.0.0")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()