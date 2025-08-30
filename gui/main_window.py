import sys
import json
import pandas as pd
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QLabel,
    QLineEdit,
    QComboBox,
    QGroupBox,
    QFormLayout,
    QMessageBox,
    QProgressBar,
    QDialog,
    QDialogButtonBox,
    QDateEdit,
    QFileDialog,
    QCheckBox,
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QDate
from PyQt6.QtGui import QFont

from fbr_core.models import DatabaseManager, SalesInvoice, FBRQueue, FBRLogs
from fbr_core.fbr_service import FBRSubmissionService, FBRQueueManager


class ExcelTemplateGenerator:
    """Generates Excel template for invoice upload"""
    
    @staticmethod
    def create_template(file_path, mode="sandbox"):
        """Create Excel template file"""
        try:
            # Create sample data based on mode
            if mode.lower() == "sandbox":
                data = {
                    'invoiceType': ['Sale Invoice'],
                    'invoiceDate': ['2025-04-21'],
                    'sellerNTNCNIC': ['0786909'],
                    'sellerBusinessName': ['Company 8'],
                    'sellerProvince': ['Sindh'],
                    'sellerAddress': ['Karachi'],
                    'buyerNTNCNIC': ['1000000000000'],
                    'buyerBusinessName': ['FERTILIZER MANUFAC IRS NEW'],
                    'buyerProvince': ['Sindh'],
                    'buyerAddress': ['Karachi'],
                    'buyerRegistrationType': ['Registered'],
                    'invoiceRefNo': [''],
                    'scenarioId': ['SN001'],
                    # Item fields
                    'hsCode': ['0101.2100'],
                    'productDescription': ['product Description'],
                    'rate': ['18%'],
                    'uoM': ['Numbers, pieces, units'],
                    'quantity': [1],
                    'totalValues': [0],
                    'valueSalesExcludingST': [1000],
                    'fixedNotifiedValueOrRetailPrice': [0],
                    'salesTaxApplicable': [18],
                    'salesTaxWithheldAtSource': [0],
                    'extraTax': [''],
                    'furtherTax': [120],
                    'sroScheduleNo': [''],
                    'fedPayable': [0],
                    'discount': [0],
                    'saleType': ['Goods at standard rate (default)'],
                    'sroItemSerialNo': ['']
                }
            else:  # production
                data = {
                    'invoiceType': ['Sale Invoice'],
                    'invoiceDate': ['2025-04-21'],
                    'sellerNTNCNIC': ['0786909'],
                    'sellerBusinessName': ['Company 8'],
                    'sellerProvince': ['Sindh'],
                    'sellerAddress': ['Karachi'],
                    'buyerNTNCNIC': ['1000000000000'],
                    'buyerBusinessName': ['FERTILIZER MANUFAC IRS NEW'],
                    'buyerProvince': ['Sindh'],
                    'buyerAddress': ['Karachi'],
                    'buyerRegistrationType': ['Unregistered'],
                    'invoiceRefNo': [''],
                    'scenarioId': [''],  # Empty for production
                    # Item fields
                    'hsCode': ['0101.2100'],
                    'productDescription': ['product Description'],
                    'rate': ['18%'],
                    'uoM': ['Numbers, pieces, units'],
                    'quantity': [1],
                    'totalValues': [0],
                    'valueSalesExcludingST': [1000],
                    'fixedNotifiedValueOrRetailPrice': [0],
                    'salesTaxApplicable': [180],
                    'salesTaxWithheldAtSource': [0],
                    'extraTax': [''],
                    'furtherTax': [120],
                    'sroScheduleNo': [''],
                    'fedPayable': [0],
                    'discount': [0],
                    'saleType': ['Goods at standard rate (default)'],
                    'sroItemSerialNo': ['']
                }

            # Create DataFrame
            df = pd.DataFrame(data)
            
            # Write to Excel with formatting
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # Write main sheet
                df.to_excel(writer, sheet_name='Invoice_Template', index=False)
                
                # Get workbook and worksheet
                workbook = writer.book
                worksheet = writer.sheets['Invoice_Template']
                
                # Add instructions sheet
                instructions = pd.DataFrame({
                    'Field Name': list(data.keys()),
                    'Description': [
                        'Type of invoice (Sale Invoice, etc.)',
                        'Invoice date (YYYY-MM-DD format)',
                        'Seller NTN/CNIC number',
                        'Seller business name',
                        'Seller province',
                        'Seller address',
                        'Buyer NTN/CNIC number',
                        'Buyer business name',
                        'Buyer province',
                        'Buyer address',
                        'Registered or Unregistered',
                        'Invoice reference number',
                        'Scenario ID (Sandbox only)',
                        'HS Code for the product',
                        'Product description',
                        'Tax rate (e.g., 18%)',
                        'Unit of measurement',
                        'Product quantity',
                        'Total values',
                        'Value excluding sales tax',
                        'Fixed/notified value or retail price',
                        'Sales tax applicable amount',
                        'Sales tax withheld at source',
                        'Extra tax',
                        'Further tax',
                        'SRO schedule number',
                        'FED payable',
                        'Discount amount',
                        'Sale type',
                        'SRO item serial number'
                    ],
                    'Required': ['Yes'] * len(data),
                    'Sample Value': [str(v[0]) if v else '' for v in data.values()]
                })
                
                instructions.to_excel(writer, sheet_name='Instructions', index=False)
                
                # Format headers
                for worksheet in writer.sheets.values():
                    for cell in worksheet[1]:  # Header row
                        cell.font = workbook.create_font(bold=True)
                        
            return True
            
        except Exception as e:
            print(f"Error creating template: {e}")
            return False


class ExcelProcessor:
    """Processes uploaded Excel files"""
    
    @staticmethod
    def process_excel_file(file_path, mode="sandbox"):
        """Process uploaded Excel file and convert to FBR format"""
        try:
            # Read Excel file
            df = pd.read_excel(file_path, sheet_name='Invoice_Template')
            
            invoices = []
            
            for index, row in df.iterrows():
                # Build invoice payload
                invoice_payload = {
                    "invoiceType": row.get('invoiceType', 'Sale Invoice'),
                    "invoiceDate": str(row.get('invoiceDate', datetime.now().strftime('%Y-%m-%d'))),
                    "sellerNTNCNIC": str(row.get('sellerNTNCNIC', '')),
                    "sellerBusinessName": str(row.get('sellerBusinessName', '')),
                    "sellerProvince": str(row.get('sellerProvince', '')),
                    "sellerAddress": str(row.get('sellerAddress', '')),
                    "buyerNTNCNIC": str(row.get('buyerNTNCNIC', '')),
                    "buyerBusinessName": str(row.get('buyerBusinessName', '')),
                    "buyerProvince": str(row.get('buyerProvince', '')),
                    "buyerAddress": str(row.get('buyerAddress', '')),
                    "buyerRegistrationType": str(row.get('buyerRegistrationType', 'Unregistered')),
                    "invoiceRefNo": str(row.get('invoiceRefNo', '')),
                    "items": [
                        {
                            "hsCode": str(row.get('hsCode', '')),
                            "productDescription": str(row.get('productDescription', '')),
                            "rate": str(row.get('rate', '18%')),
                            "uoM": str(row.get('uoM', 'Numbers, pieces, units')),
                            "quantity": float(row.get('quantity', 1)),
                            "totalValues": float(row.get('totalValues', 0)),
                            "valueSalesExcludingST": float(row.get('valueSalesExcludingST', 0)),
                            "fixedNotifiedValueOrRetailPrice": float(row.get('fixedNotifiedValueOrRetailPrice', 0)),
                            "salesTaxApplicable": float(row.get('salesTaxApplicable', 0)),
                            "salesTaxWithheldAtSource": float(row.get('salesTaxWithheldAtSource', 0)),
                            "extraTax": str(row.get('extraTax', '')),
                            "furtherTax": float(row.get('furtherTax', 0)),
                            "sroScheduleNo": str(row.get('sroScheduleNo', '')),
                            "fedPayable": float(row.get('fedPayable', 0)),
                            "discount": float(row.get('discount', 0)),
                            "saleType": str(row.get('saleType', 'Goods at standard rate (default)')),
                            "sroItemSerialNo": str(row.get('sroItemSerialNo', ''))
                        }
                    ]
                }
                
                # Add scenarioId for sandbox mode
                if mode.lower() == "sandbox":
                    invoice_payload["scenarioId"] = str(row.get('scenarioId', 'SN001'))
                
                invoices.append(invoice_payload)
            
            return {"success": True, "invoices": invoices}
            
        except Exception as e:
            return {"success": False, "error": str(e)}


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

            result = self.submission_service.submit_invoice(
                invoice_id, self.document_type
            )

            if result["success"]:
                results["successful"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(
                    f"Invoice {invoice_id}: {result.get('error', 'Unknown error')}"
                )

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
        self.items_table.setHorizontalHeaderLabels(
            ["Item", "Quantity", "Rate", "Amount", "Tax Rate", "HS Code"]
        )
        items_layout.addWidget(self.items_table)

        # Add item button
        add_item_btn = QPushButton("Add Item")
        add_item_btn.clicked.connect(self.add_item_row)
        items_layout.addWidget(add_item_btn)

        layout.addWidget(items_group)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
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

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.db_manager = None
        self.is_sandbox_mode = True  # Default to sandbox
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

        # Invoices tab (renamed from Sales Invoices)
        self.invoices_tab = self.create_invoices_tab()
        tab_widget.addTab(self.invoices_tab, "Invoices")

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

        # Top toolbar with mode toggle
        top_toolbar = QHBoxLayout()
        
        # Sandbox/Production Toggle
        mode_group = QGroupBox("Mode")
        mode_layout = QHBoxLayout(mode_group)
        
        self.sandbox_checkbox = QCheckBox("Sandbox Mode")
        self.sandbox_checkbox.setChecked(True)  # Default to sandbox
        self.sandbox_checkbox.toggled.connect(self.toggle_mode)
        
        # Style the checkbox to look like a toggle
        self.sandbox_checkbox.setStyleSheet("""
            QCheckBox {
                font-weight: bold;
                color: #0078d4;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border: 2px solid #0078d4;
            }
            QCheckBox::indicator:unchecked {
                background-color: #f0f0f0;
                border: 2px solid #cccccc;
            }
        """)
        
        mode_layout.addWidget(self.sandbox_checkbox)
        top_toolbar.addWidget(mode_group)
        
        top_toolbar.addStretch()
        
        # Download template and upload buttons
        download_template_btn = QPushButton("📥 Download Template")
        download_template_btn.clicked.connect(self.download_template)
        download_template_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        top_toolbar.addWidget(download_template_btn)
        
        upload_excel_btn = QPushButton("📤 Upload Excel")
        upload_excel_btn.clicked.connect(self.upload_excel)
        upload_excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        top_toolbar.addWidget(upload_excel_btn)
        
        layout.addLayout(top_toolbar)

        # Regular toolbar
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
        self.invoices_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        layout.addWidget(self.invoices_table)

        return widget

    def toggle_mode(self, checked):
        """Toggle between Sandbox and Production mode"""
        self.is_sandbox_mode = checked
        mode_text = "Sandbox" if checked else "Production"
        self.statusBar().showMessage(f"Mode switched to: {mode_text}")
        
        # Update checkbox text
        self.sandbox_checkbox.setText(f"{mode_text} Mode")

    def download_template(self):
        """Download Excel template"""
        try:
            mode = "sandbox" if self.is_sandbox_mode else "production"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                f"Save {mode.title()} Template",
                f"fbr_invoice_template_{mode}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                "Excel files (*.xlsx)"
            )
            
            if file_path:
                success = ExcelTemplateGenerator.create_template(file_path, mode)
                
                if success:
                    QMessageBox.information(
                        self,
                        "Template Downloaded",
                        f"Excel template for {mode.title()} mode has been saved to:\n{file_path}"
                    )
                else:
                    QMessageBox.critical(
                        self,
                        "Download Failed",
                        "Failed to create Excel template. Please try again."
                    )
                    
        except Exception as e:
            QMessageBox.critical(
                self,
                "Download Error",
                f"Error downloading template: {str(e)}"
            )

    def upload_excel(self):
        """Upload and process Excel file"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Excel File",
                "",
                "Excel files (*.xlsx *.xls)"
            )
            
            if file_path:
                mode = "sandbox" if self.is_sandbox_mode else "production"
                
                # Show processing message
                self.statusBar().showMessage("Processing Excel file...")
                
                # Process the Excel file
                result = ExcelProcessor.process_excel_file(file_path, mode)
                
                if result["success"]:
                    invoices = result["invoices"]
                    
                    # Show confirmation dialog
                    reply = QMessageBox.question(
                        self,
                        "Upload Confirmation",
                        f"Found {len(invoices)} invoice(s) in the Excel file.\n"
                        f"Mode: {mode.title()}\n"
                        f"Do you want to submit these invoices to FBR?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        # Process invoices for FBR submission
                        self.process_uploaded_invoices(invoices, mode)
                    else:
                        self.statusBar().showMessage("Upload cancelled")
                        
                else:
                    QMessageBox.critical(
                        self,
                        "Processing Error",
                        f"Error processing Excel file:\n{result['error']}"
                    )
                    
        except Exception as e:
            QMessageBox.critical(
                self,
                "Upload Error",
                f"Error uploading Excel file: {str(e)}"
            )

    def process_uploaded_invoices(self, invoices, mode):
        """Process uploaded invoices for FBR submission"""
        try:
            success_count = 0
            error_count = 0
            errors = []
            
            # Initialize services
            submission_service = FBRSubmissionService(self.db_manager)
            queue_manager = FBRQueueManager(self.db_manager)
            
            for i, invoice_data in enumerate(invoices):
                try:
                    self.statusBar().showMessage(f"Processing invoice {i+1} of {len(invoices)}...")
                    self.repaint()  # Force GUI update
                    
                    # 1. Save invoice to database first
                    invoice_id = self._save_invoice_to_database(invoice_data)
                    
                    # 2. Add to FBR queue
                    queue_manager.add_to_queue("Sales Invoice", invoice_id, priority=1)
                    
                    # 3. Submit to FBR (real API call)
                    result = submission_service.submit_invoice(invoice_id, "Sales Invoice")
                    
                    if result["success"]:
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(f"Invoice {i+1}: {result.get('error', 'Unknown error')}")
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Invoice {i+1}: {str(e)}")
            
            # Show results
            result_message = (
                f"Upload processing completed!\n\n"
                f"Successful: {success_count}\n"
                f"Failed: {error_count}\n"
                f"Mode: {mode.title()}"
            )
            
            if errors:
                result_message += f"\n\nErrors:\n" + "\n".join(errors[:5])
                if len(errors) > 5:
                    result_message += f"\n... and {len(errors) - 5} more errors"
            
            QMessageBox.information(self, "Upload Complete", result_message)
            
            # Refresh tables
            self.refresh_invoices_table()
            self.refresh_queue_table()
            self.refresh_logs_table()
            
        except Exception as e:
            QMessageBox.critical(self, "Processing Error", f"Error processing uploaded invoices: {str(e)}")
        finally:
            self.statusBar().showMessage("Ready")


    def _save_invoice_to_database(self, invoice_data):
        """Save invoice data to database and return invoice ID"""
        session = self.db_manager.get_session()
        
        # Create invoice record
        invoice = SalesInvoice(
            invoice_number=f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(str(invoice_data)) % 1000:03d}",
            posting_date=datetime.strptime(invoice_data['invoiceDate'], '%Y-%m-%d'),
            total_amount=sum(item['valueSalesExcludingST'] for item in invoice_data['items']),
            tax_amount=sum(item['salesTaxApplicable'] for item in invoice_data['items']),
            grand_total=sum(item['valueSalesExcludingST'] + item['salesTaxApplicable'] for item in invoice_data['items']),
            province=invoice_data.get('buyerProvince', ''),
            submit_to_fbr=True,
            created_at=datetime.now()
        )
        
        session.add(invoice)
        session.commit()
        
        return invoice.id


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

        # FBR API Settings Group
        api_group = QGroupBox("FBR API Settings")
        api_group.setMinimumHeight(300)  # Ensure minimum height
        api_layout = QFormLayout(api_group)

        self.api_endpoint_edit = QLineEdit()
        self.api_endpoint_edit.setPlaceholderText("https://api.fbr.gov.pk/einvoicing")
        
        self.auth_token_edit = QLineEdit()
        self.auth_token_edit.setPlaceholderText("Enter your authorization token")
        
        self.login_id_edit = QLineEdit()
        self.login_id_edit.setPlaceholderText("Enter your login ID")
        
        self.login_password_edit = QLineEdit()
        self.login_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password_edit.setPlaceholderText("Enter your password")

        # Add rows with proper spacing
        api_layout.addRow("API Endpoint:", self.api_endpoint_edit)
        api_layout.addRow("Authorization Token:", self.auth_token_edit)
        api_layout.addRow("Login ID:", self.login_id_edit)
        api_layout.addRow("Login Password:", self.login_password_edit)

        layout.addWidget(api_group)

        # Database Settings Group
        db_group = QGroupBox("Database Settings")
        db_layout = QFormLayout(db_group)
        
        self.connection_status_label = QLabel("Not Connected")
        self.connection_status_label.setStyleSheet("color: red;")
        
        test_connection_btn = QPushButton("Test Connection")
        test_connection_btn.clicked.connect(self.test_database_connection)
        
        db_layout.addRow("Connection Status:", self.connection_status_label)
        db_layout.addRow("", test_connection_btn)
        
        layout.addWidget(db_group)

        # Button layout
        button_layout = QHBoxLayout()
        
        load_settings_btn = QPushButton("Load Settings")
        load_settings_btn.clicked.connect(self.load_settings)
        button_layout.addWidget(load_settings_btn)
        
        save_settings_btn = QPushButton("Save Settings")
        save_settings_btn.clicked.connect(self.save_settings)
        save_settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        button_layout.addWidget(save_settings_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        return widget

    def load_settings(self):
        """Load settings from database"""
        if not self.db_manager:
            QMessageBox.warning(self, "Warning", "Database not connected")
            return
            
        try:
            session = self.db_manager.get_session()
            from fbr_core.models import FBRSettings
            
            settings = session.query(FBRSettings).first()
            
            if settings:
                self.api_endpoint_edit.setText(settings.api_endpoint or "")
                self.auth_token_edit.setText(settings.pral_authorization_token or "")
                self.login_id_edit.setText(settings.pral_login_id or "")
                self.login_password_edit.setText(settings.pral_login_password or "")
                
                self.statusBar().showMessage("Settings loaded successfully")
            else:
                # Create default settings
                default_settings = FBRSettings(
                    api_endpoint="https://api.fbr.gov.pk/einvoicing",
                    pral_authorization_token="",
                    pral_login_id="",
                    pral_login_password=""
                )
                session.add(default_settings)
                session.commit()
                
                self.statusBar().showMessage("Default settings created")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load settings: {str(e)}")


    def setup_database(self):
        """Setup database connection - UPDATED VERSION"""
        try:
            # Use connection string from config if available
            if self.config:
                connection_string = self.config.get_database_url()
            else:
                # Fallback to hardcoded connection string
                connection_string = (
                    "postgresql://neondb_owner:npg_H2hByXAgPz8n@ep-sparkling-shape-"
                    "adwmth20-pooler.c-2.us-east-1.aws.neon.tech/neondb?"
                    "sslmode=require&channel_binding=require"
                )
            
            from fbr_core.models import DatabaseManager
            self.db_manager = DatabaseManager(connection_string)
            self.statusBar().showMessage("Database connected successfully")

            # Load initial data
            self.refresh_invoices_table()
            self.refresh_queue_table()
            self.refresh_logs_table()
            
            # Load settings automatically
            self.load_settings()
            
            # Update connection status if on settings tab
            if hasattr(self, 'connection_status_label'):
                self.connection_status_label.setText("Connected ✓")
                self.connection_status_label.setStyleSheet("color: green; font-weight: bold;")

        except Exception as e:
            QMessageBox.critical(
                self, "Database Error", f"Failed to connect to database: {str(e)}"
            )
            if hasattr(self, 'connection_status_label'):
                self.connection_status_label.setText("Connection Failed ✗")
                self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")

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

        mode = "Sandbox" if self.is_sandbox_mode else "Production"
        reply = QMessageBox.question(
            self,
            "Confirm Submission",
            f"Submit {len(invoice_ids)} invoice(s) to FBR in {mode} mode?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return

        # Start background submission
        self.submission_thread = FBRSubmissionThread(
            self.db_manager, invoice_ids, "Sales Invoice"
        )
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

        message = (
            f"Submission completed:\nSuccessful: {results['successful']}"
            f"\nFailed: {results['failed']}"
        )
        if results["errors"]:
            message += "\n\nErrors:\n" + "\n".join(
                results["errors"][:5]
            )  # Show first 5 errors

        QMessageBox.information(self, "Submission Complete", message)
        self.refresh_invoices_table()
        self.refresh_queue_table()

    def process_fbr_queue(self):
        """Process FBR queue"""
        if not self.db_manager:
            return

        queue_manager = FBRQueueManager(self.db_manager)
        result = queue_manager.process_queue()

        message = (
            f"Queue processing completed.\n"
            f"Processed: {result.get('processed_count', 0)} items"
        )
        if "error" in result:
            message += f"\nError: {result['error']}"

        QMessageBox.information(self, "Queue Processing", message)
        self.refresh_queue_table()
        self.refresh_logs_table()

    def refresh_invoices_table(self):
        """Refresh invoices table"""
        if not self.db_manager:
            return

        session = self.db_manager.get_session()
        invoices = (
            session.query(SalesInvoice)
            .order_by(SalesInvoice.created_at.desc())
            .limit(100)
            .all()
        )

        self.invoices_table.setRowCount(len(invoices))
        self.invoices_table.setColumnCount(8)  # Added mode column
        self.invoices_table.setHorizontalHeaderLabels(
            [
                "ID",
                "Invoice Number",
                "Customer",
                "Date",
                "Amount",
                "FBR Status",
                "FBR Invoice No",
                "Mode"
            ]
        )

        for row, invoice in enumerate(invoices):
            self.invoices_table.setItem(row, 0, QTableWidgetItem(str(invoice.id)))
            self.invoices_table.setItem(
                row, 1, QTableWidgetItem(invoice.invoice_number)
            )
            self.invoices_table.setItem(
                row, 2, QTableWidgetItem(str(invoice.customer_id))
            )  # Get customer name
            self.invoices_table.setItem(
                row,
                3,
                QTableWidgetItem(
                    invoice.posting_date.strftime("%Y-%m-%d")
                    if invoice.posting_date
                    else ""
                ),
            )
            self.invoices_table.setItem(
                row,
                4,
                QTableWidgetItem(
                    f"{invoice.grand_total:.2f}" if invoice.grand_total else "0.00"
                ),
            )
            self.invoices_table.setItem(
                row, 5, QTableWidgetItem(invoice.fbr_status or "")
            )
            self.invoices_table.setItem(
                row, 6, QTableWidgetItem(invoice.fbr_invoice_number or "")
            )
            self.invoices_table.setItem(
                row, 7, QTableWidgetItem("Sandbox" if self.is_sandbox_mode else "Production")
            )

        self.invoices_table.resizeColumnsToContents()

    def refresh_queue_table(self):
        """Refresh queue table"""
        if not self.db_manager:
            return

        session = self.db_manager.get_session()
        queue_items = (
            session.query(FBRQueue)
            .order_by(FBRQueue.created_at.desc())
            .limit(100)
            .all()
        )

        self.queue_table.setRowCount(len(queue_items))
        self.queue_table.setColumnCount(6)
        self.queue_table.setHorizontalHeaderLabels(
            ["ID", "Document", "Status", "Priority", "Retries", "Created"]
        )

        for row, item in enumerate(queue_items):
            self.queue_table.setItem(row, 0, QTableWidgetItem(str(item.id)))
            self.queue_table.setItem(
                row, 1, QTableWidgetItem(f"{item.document_type} {item.document_id}")
            )
            self.queue_table.setItem(row, 2, QTableWidgetItem(item.status))
            self.queue_table.setItem(row, 3, QTableWidgetItem(str(item.priority)))
            self.queue_table.setItem(
                row, 4, QTableWidgetItem(f"{item.retry_count}/{item.max_retries}")
            )
            self.queue_table.setItem(
                row,
                5,
                QTableWidgetItem(
                    item.created_at.strftime("%Y-%m-%d %H:%M")
                    if item.created_at
                    else ""
                ),
            )

        self.queue_table.resizeColumnsToContents()

    def refresh_logs_table(self):
        """Refresh logs table"""
        if not self.db_manager:
            return

        session = self.db_manager.get_session()
        logs = (
            session.query(FBRLogs)
            .order_by(FBRLogs.submitted_at.desc())
            .limit(100)
            .all()
        )

        self.logs_table.setRowCount(len(logs))
        self.logs_table.setColumnCount(6)
        self.logs_table.setHorizontalHeaderLabels(
            [
                "ID",
                "Document",
                "FBR Invoice No",
                "Status",
                "Submitted",
                "Processing Time",
            ]
        )

        for row, log in enumerate(logs):
            self.logs_table.setItem(row, 0, QTableWidgetItem(str(log.id)))
            self.logs_table.setItem(
                row, 1, QTableWidgetItem(f"{log.document_type} {log.document_id}")
            )
            self.logs_table.setItem(
                row, 2, QTableWidgetItem(log.fbr_invoice_number or "")
            )
            self.logs_table.setItem(row, 3, QTableWidgetItem(log.status))
            self.logs_table.setItem(
                row,
                4,
                QTableWidgetItem(
                    log.submitted_at.strftime("%Y-%m-%d %H:%M")
                    if log.submitted_at
                    else ""
                ),
            )
            self.logs_table.setItem(
                row,
                5,
                QTableWidgetItem(
                    f"{log.processing_time:.2f}ms" if log.processing_time else ""
                ),
            )

        self.logs_table.resizeColumnsToContents()

    def test_database_connection(self):
        """Test database connection"""
        try:
            if self.db_manager:
                session = self.db_manager.get_session()
                session.execute("SELECT 1")
                
                self.connection_status_label.setText("Connected ✓")
                self.connection_status_label.setStyleSheet("color: green; font-weight: bold;")
                QMessageBox.information(self, "Success", "Database connection successful!")
            else:
                self.connection_status_label.setText("Not Connected ✗")
                self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
                QMessageBox.warning(self, "Warning", "Database manager not initialized")
                
        except Exception as e:
            self.connection_status_label.setText("Connection Failed ✗")
            self.connection_status_label.setStyleSheet("color: red; font-weight: bold;")
            QMessageBox.critical(self, "Error", f"Database connection failed: {str(e)}")



    def save_settings(self):
        """Save FBR settings to database"""
        if not self.db_manager:
            QMessageBox.warning(self, "Warning", "Database not connected")
            return
            
        try:
            session = self.db_manager.get_session()
            from fbr_core.models import FBRSettings
            
            settings = session.query(FBRSettings).first()
            
            if not settings:
                settings = FBRSettings()
                session.add(settings)
            
            # Update settings
            settings.api_endpoint = self.api_endpoint_edit.text().strip()
            settings.pral_authorization_token = self.auth_token_edit.text().strip()
            settings.pral_login_id = self.login_id_edit.text().strip()
            settings.pral_login_password = self.login_password_edit.text().strip()
            settings.updated_at = datetime.now()
            
            session.commit()
            
            QMessageBox.information(self, "Success", "Settings saved successfully!")
            self.statusBar().showMessage("Settings saved")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")

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