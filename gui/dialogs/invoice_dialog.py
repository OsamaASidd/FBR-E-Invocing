# gui/dialogs/invoice_dialog.py - Updated Company-Specific Version
import sys
import requests
from datetime import datetime, date
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFormLayout, QWidget, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QLineEdit, QComboBox, QGroupBox, QDateEdit, QCheckBox,
    QSpinBox, QDoubleSpinBox, QTextEdit, QHeaderView, QMessageBox,
    QDialogButtonBox, QTabWidget, QScrollArea, QSplitter, QProgressBar,
    QFrame
)
from PyQt6.QtCore import QDate, Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor

# Import dialogs and services
from gui.dialogs.item_dialog import ItemSelectionDialog
from fbr_core.models import Item

# Import the FBR API service
try:
    from fbr_core.fbr_api_service import FBRDropdownManager, FBRDateUtils, DropdownDataFormatter
except ImportError as e:
    print(f"Warning: Could not import FBR API service: {e}")
    # Fallback classes for when API service is not available
    class FBRDropdownManager:
        def __init__(self, db_manager): pass
        def load_dropdown_data(self, *args, **kwargs): pass
        def format_data_for_dropdown(self, key, data): return []
        def cleanup_threads(self): pass
    
    class FBRDateUtils:
        @staticmethod
        def format_date_for_fbr(date_obj): return date_obj.strftime('%d-%b-%Y')
        @staticmethod 
        def format_date_iso(date_obj): return date_obj.strftime('%Y-%m-%d')
    
    class DropdownDataFormatter:
        @staticmethod
        def extract_hs_code_from_dropdown_text(text): 
            try: return text.split(' - ')[0].strip()
            except: return ""
        @staticmethod
        def extract_id_from_dropdown_text(text, position=-1):
            try: return text.split(' - ')[position].strip()  
            except: return ""


class FBRInvoiceDialog(QDialog):
    """Company-specific FBR Invoice Dialog with seller auto-filled"""
    
    invoice_saved = pyqtSignal(dict)  # Signal when invoice is saved
    
    def __init__(self, parent=None, invoice_data=None, mode="sandbox", company_data=None, seller_data=None):
        super().__init__(parent)
        self.invoice_data = invoice_data
        self.mode = mode.lower()
        self.is_editing = invoice_data is not None
        self.company_data = company_data
        self.seller_data = seller_data or {}
        
        # Initialize API service
        self.db_manager = getattr(parent, 'db_manager', None) if parent else None
        self.dropdown_manager = FBRDropdownManager(self.db_manager) if self.db_manager else None
        self.formatter = DropdownDataFormatter()
        
        # Loading state tracking
        self.loading_dropdowns = set()
        self.dropdown_data_cache = {}
        
        self.setWindowTitle("FBR Invoice Details")
        self.setModal(True)
        self.resize(1400, 900)
        
        self.setStyleSheet("""
            QDialog { background-color: #0f1115; }
            QLabel { color: #eaeef6; font-size: 13px; }
            QGroupBox {
                background: #1b2028;
                border: 1px solid #2c3b52;
                border-radius: 10px;
                padding-top: 18px;
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

            /* Inputs: consistent 34px height, clear focus, rounded */
            QLineEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {
                background: #0f141c;
                color: #eaeef6;
                border: 1px solid #334561;
                border-radius: 6px;
                padding: 6px 10px;
                min-height: 34px;
            }
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus,
            QSpinBox:focus, QDoubleSpinBox:focus {
                border: 1px solid #5aa2ff;
                box-shadow: 0 0 0 2px rgba(90,162,255,0.18);
            }
            QLineEdit:read-only {
                background: #2c3b52;
                color: #cccccc;
            }

            /* Table styling */
            QTableWidget { background: #0f141c; color:#eaeef6; border: 1px solid #334561; }
            QHeaderView::section {
                background: #17202b; color: #cfe2ff; border: 1px solid #334561; padding: 6px; font-weight: 600;
            }

            /* Buttons */
            QPushButton {
                background-color: #5aa2ff; color: #0f1115; border: none;
                padding: 8px 14px; border-radius: 6px; font-weight: 700;
            }
            QPushButton:hover { background:#7bb6ff; }
            QPushButton:pressed { background:#4b92ec; }
            QPushButton:disabled { background:#333; color:#666; }
            QPushButton[style="success"] { background-color: #28a745; color: white; }
            QPushButton[style="warning"] { background-color: #ffc107; color: #000; }
            QPushButton[style="danger"] { background-color: #dc3545; color: white; }

            /* Progress bar for loading */
            QProgressBar {
                border: 2px solid #334561;
                border-radius: 5px;
                text-align: center;
                background: #0f141c;
                color: #eaeef6;
            }
            QProgressBar::chunk {
                background-color: #5aa2ff;
                border-radius: 3px;
            }
        """)

        self.setup_ui()
        self.setup_signals()
        
        # Load dropdown data from APIs
        self.populate_dropdowns_from_api()
        
        # Pre-fill seller data
        self.pre_fill_seller_data()
        
        if self.is_editing and invoice_data:
            self.load_invoice_data()

    def setup_ui(self):
        """Setup the user interface"""
        main_layout = QVBoxLayout(self)
        
        # Create scroll area for the form
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Header with mode indicator and loading status
        header_layout = QHBoxLayout()
        
        # Company info
        if self.company_data:
            company_label = QLabel(f"Company: {self.company_data['name']}")
            company_label.setStyleSheet("color: #5aa2ff; font-weight: bold; font-size: 14px;")
            header_layout.addWidget(company_label)
        
        # Loading indicator
        self.loading_label = QLabel("Loading dropdown data...")
        self.loading_label.setStyleSheet("color: #ffc107; font-weight: bold;")
        self.loading_progress = QProgressBar()
        self.loading_progress.setRange(0, 0)  # Indeterminate
        self.loading_progress.setMaximumHeight(4)
        
        header_layout.addWidget(self.loading_label)
        header_layout.addWidget(self.loading_progress)
        
        mode_label = QLabel(f"Mode: {self.mode.title()}")
        mode_bg = "#28a745" if self.mode == "production" else "#ffc107"
        mode_label.setStyleSheet(
            f"background-color: {mode_bg};"
            "color: white;"
            "padding: 8px 16px;"
            "border-radius: 4px;"
            "font-weight: bold;"
            "font-size: 14px;"
        )
        header_layout.addStretch()
        header_layout.addWidget(mode_label)
        scroll_layout.addLayout(header_layout)
                
        # Create main sections
        self.create_seller_buyer_section(scroll_layout)
        self.create_item_selection_section(scroll_layout)
        self.create_items_list_section(scroll_layout)
        
        # Setup scroll area
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        main_layout.addWidget(scroll_area)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        
        validate_btn = QPushButton("✅ Validate Invoice")
        validate_btn.setProperty("style", "warning")
        validate_btn.clicked.connect(self.validate_invoice)
        button_layout.addWidget(validate_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setProperty("style", "danger")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("💾 Save Invoice")
        save_btn.setProperty("style", "success")
        save_btn.clicked.connect(self.save_invoice)
        button_layout.addWidget(save_btn)
        
        self.save_btn = save_btn  # Keep reference for enabling/disabling
        
        main_layout.addLayout(button_layout)

    def create_seller_buyer_section(self, parent_layout):
        """Create seller + buyer information section with seller auto-filled"""
        section_group = QGroupBox("Invoice Details")
        section_layout = QGridLayout(section_group)
        section_layout.setContentsMargins(14, 10, 14, 12)
        section_layout.setHorizontalSpacing(18)
        section_layout.setVerticalSpacing(10)

        self._req_lbl = lambda t: f"{t}<span style='color:#1e90ff'>*</span>"

        # -------- Row 0: Invoice metadata --------
        section_layout.addWidget(QLabel(self._req_lbl("Invoice Type")), 0, 0)
        self.invoice_type_combo = QComboBox()
        self.invoice_type_combo.addItems(["Sale Invoice", "Debit Note"])
        section_layout.addWidget(self.invoice_type_combo, 0, 1)

        section_layout.addWidget(QLabel("Invoice No.:"), 0, 2)
        self.invoice_no_edit = QLineEdit()
        self.invoice_no_edit.setPlaceholderText("Auto-generated")
        self.invoice_no_edit.setReadOnly(True)
        section_layout.addWidget(self.invoice_no_edit, 0, 3)

        section_layout.addWidget(QLabel(self._req_lbl("Invoice Date")), 0, 4)
        self.invoice_date_edit = QDateEdit(QDate.currentDate())
        self.invoice_date_edit.setCalendarPopup(True)
        self.invoice_date_edit.setDisplayFormat("d/M/yyyy")
        section_layout.addWidget(self.invoice_date_edit, 0, 5)

        # -------- Row 1: SELLER (Auto-filled, Read-only) --------
        seller_label = QLabel("SELLER (Company Details)")
        seller_label.setStyleSheet("font-weight: bold; color: #5aa2ff; font-size: 14px;")
        section_layout.addWidget(seller_label, 1, 0, 1, 6)

        section_layout.addWidget(QLabel("Seller NTN/CNIC:"), 2, 0)
        self.seller_reg_no_edit = QLineEdit()
        self.seller_reg_no_edit.setReadOnly(True)
        section_layout.addWidget(self.seller_reg_no_edit, 2, 1)

        section_layout.addWidget(QLabel("Seller Name:"), 2, 2)
        self.seller_name_edit = QLineEdit()
        self.seller_name_edit.setReadOnly(True)
        section_layout.addWidget(self.seller_name_edit, 2, 3, 1, 2)

        section_layout.addWidget(QLabel("Seller Province:"), 3, 0)
        self.seller_province_combo = QComboBox()
        self.seller_province_combo.setEnabled(False)  # Will be set based on company
        section_layout.addWidget(self.seller_province_combo, 3, 1)

        section_layout.addWidget(QLabel("Seller Address:"), 3, 2)
        self.seller_address_edit = QLineEdit()
        self.seller_address_edit.setReadOnly(True)
        section_layout.addWidget(self.seller_address_edit, 3, 3, 1, 2)

        # -------- Row 4: BUYER --------
        buyer_label = QLabel("BUYER (Customer Details)")
        buyer_label.setStyleSheet("font-weight: bold; color: #ffc107; font-size: 14px;")
        section_layout.addWidget(buyer_label, 4, 0, 1, 6)

        section_layout.addWidget(QLabel(self._req_lbl("Buyer Registration No.")), 5, 0)
        self.buyer_reg_no_edit = QLineEdit()
        self.buyer_reg_no_edit.setPlaceholderText("Enter buyer NTN/CNIC")
        section_layout.addWidget(self.buyer_reg_no_edit, 5, 1)

        section_layout.addWidget(QLabel(self._req_lbl("Buyer Name")), 5, 2)
        self.buyer_name_edit = QLineEdit()
        self.buyer_name_edit.setPlaceholderText("Enter buyer name")
        section_layout.addWidget(self.buyer_name_edit, 5, 3)

        section_layout.addWidget(QLabel("Buyer Type:"), 5, 4)
        self.buyer_type_combo = QComboBox()
        self.buyer_type_combo.addItems(["Registered", "Unregistered"])
        section_layout.addWidget(self.buyer_type_combo, 5, 5)

        section_layout.addWidget(QLabel(self._req_lbl("Buyer Province")), 6, 0)
        self.buyer_province_combo = QComboBox()
        self.buyer_province_combo.setProperty("loading", "true")
        section_layout.addWidget(self.buyer_province_combo, 6, 1)

        section_layout.addWidget(QLabel("Buyer Address:"), 6, 2)
        self.buyer_address_edit = QLineEdit()
        self.buyer_address_edit.setPlaceholderText("Street/area, city, district")
        section_layout.addWidget(self.buyer_address_edit, 6, 3, 1, 2)

        # -------- Row 7: Transaction details --------
        section_layout.addWidget(QLabel(self._req_lbl("Transaction Type")), 7, 0)
        self.transaction_type_combo = QComboBox()
        self.transaction_type_combo.setProperty("loading", "true")
        section_layout.addWidget(self.transaction_type_combo, 7, 1)

        section_layout.addWidget(QLabel(self._req_lbl("Sale Origination Province")), 7, 2)
        self.sale_origination_combo = QComboBox()
        self.sale_origination_combo.setProperty("loading", "true")
        section_layout.addWidget(self.sale_origination_combo, 7, 3)

        section_layout.addWidget(QLabel(self._req_lbl("Destination of Supply")), 7, 4)
        self.destination_supply_combo = QComboBox()
        self.destination_supply_combo.setProperty("loading", "true")
        section_layout.addWidget(self.destination_supply_combo, 7, 5)

        parent_layout.addWidget(section_group)

    def create_item_selection_section(self, parent_layout):
        """Create item selection section with company items"""
        item_group = QGroupBox("📦 Add Items to Invoice")
        item_layout = QGridLayout(item_group)
        
        # Row 1: Item selection
        item_layout.addWidget(QLabel("Select Item*:"), 0, 0)
        
        select_item_layout = QHBoxLayout()
        self.select_item_btn = QPushButton("🔍 Select from Company Items")
        self.select_item_btn.clicked.connect(self.select_item_from_company)
        select_item_layout.addWidget(self.select_item_btn)
        
        self.add_new_item_btn = QPushButton("➕ Add New Item")
        self.add_new_item_btn.setProperty("style", "success")
        self.add_new_item_btn.clicked.connect(self.add_new_item_to_company)
        select_item_layout.addWidget(self.add_new_item_btn)
        
        select_item_layout.addStretch()
        item_layout.addLayout(select_item_layout, 0, 1, 1, 5)
        
        # Selected item display
        self.selected_item_frame = QFrame()
        self.selected_item_frame.setVisible(False)
        self.selected_item_frame.setStyleSheet("""
            QFrame {
                background: #2c3b52;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }
        """)
        
        selected_layout = QGridLayout(self.selected_item_frame)
        
        self.selected_item_label = QLabel("No item selected")
        self.selected_item_label.setStyleSheet("font-weight: bold; color: #5aa2ff;")
        selected_layout.addWidget(self.selected_item_label, 0, 0, 1, 2)
        
        selected_layout.addWidget(QLabel("HS Code:"), 1, 0)
        self.selected_hs_code_label = QLabel("-")
        selected_layout.addWidget(self.selected_hs_code_label, 1, 1)
        
        selected_layout.addWidget(QLabel("UoM:"), 1, 2)
        self.selected_uom_label = QLabel("-")
        selected_layout.addWidget(self.selected_uom_label, 1, 3)
        
        item_layout.addWidget(self.selected_item_frame, 1, 0, 1, 6)
        
        # Row 2: Sale Type and Rate (Auto-populated based on transaction type)
        item_layout.addWidget(QLabel("Sale Type:"), 2, 0)
        self.sale_type_combo = QComboBox()
        self.sale_type_combo.setProperty("loading", "true")
        item_layout.addWidget(self.sale_type_combo, 2, 1)
        
        item_layout.addWidget(QLabel("Rate*:"), 2, 2)
        self.rate_combo = QComboBox()
        self.rate_combo.setEditable(True)
        self.rate_combo.setProperty("loading", "true")
        item_layout.addWidget(self.rate_combo, 2, 3)
        
        item_layout.addWidget(QLabel("Quantity*:"), 2, 4)
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.001, 999999.999)
        self.quantity_spin.setDecimals(3)
        self.quantity_spin.setValue(1.000)
        item_layout.addWidget(self.quantity_spin, 2, 5)
        
        # Row 3: Financial fields
        item_layout.addWidget(QLabel("Value of Sales Excl. ST*:"), 3, 0)
        self.value_excl_st_spin = QDoubleSpinBox()
        self.value_excl_st_spin.setRange(0.00, 99999999.99)
        self.value_excl_st_spin.setDecimals(2)
        item_layout.addWidget(self.value_excl_st_spin, 3, 1)
        
        item_layout.addWidget(QLabel("Sales Tax:"), 3, 2)
        self.sales_tax_spin = QDoubleSpinBox()
        self.sales_tax_spin.setRange(0.00, 99999999.99)
        self.sales_tax_spin.setDecimals(2)
        self.sales_tax_spin.setReadOnly(True)  # Auto-calculated
        item_layout.addWidget(self.sales_tax_spin, 3, 3)
        
        item_layout.addWidget(QLabel("Extra Tax:"), 3, 4)
        self.extra_tax_spin = QDoubleSpinBox()
        self.extra_tax_spin.setRange(0.00, 99999999.99)
        self.extra_tax_spin.setDecimals(2)
        item_layout.addWidget(self.extra_tax_spin, 3, 5)
        
        # Row 4: Additional fields
        item_layout.addWidget(QLabel("ST withheld at Source:"), 4, 0)
        self.st_withheld_spin = QDoubleSpinBox()
        self.st_withheld_spin.setRange(0.00, 99999999.99)
        self.st_withheld_spin.setDecimals(2)
        item_layout.addWidget(self.st_withheld_spin, 4, 1)
        
        item_layout.addWidget(QLabel("Further Tax:"), 4, 2)
        self.further_tax_spin = QDoubleSpinBox()
        self.further_tax_spin.setRange(0.00, 99999999.99)
        self.further_tax_spin.setDecimals(2)
        item_layout.addWidget(self.further_tax_spin, 4, 3)
        
        item_layout.addWidget(QLabel("Discount:"), 4, 4)
        self.discount_spin = QDoubleSpinBox()
        self.discount_spin.setRange(0.00, 99999999.99)
        self.discount_spin.setDecimals(2)
        item_layout.addWidget(self.discount_spin, 4, 5)
        
        # Row 5: Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.add_item_btn = QPushButton("➕ Add Item to Invoice")
        self.add_item_btn.setProperty("style", "success")
        self.add_item_btn.clicked.connect(self.add_item_to_invoice)
        self.add_item_btn.setEnabled(False)  # Enabled when item is selected
        button_layout.addWidget(self.add_item_btn)
        
        self.clear_item_btn = QPushButton("🗑️ Clear")
        self.clear_item_btn.clicked.connect(self.clear_item_fields)
        button_layout.addWidget(self.clear_item_btn)
        
        item_layout.addLayout(button_layout, 5, 0, 1, 6)
        
        parent_layout.addWidget(item_group)
        
        # Store selected item data
        self.selected_item_data = None

    def create_items_list_section(self, parent_layout):
        """Create items list table section"""
        list_group = QGroupBox("📋 Invoice Items")
        list_layout = QVBoxLayout(list_group)
        
        # Items table
        self.items_table = QTableWidget(0, 14)
        self.items_table.setHorizontalHeaderLabels([
            "Sr.", "Item Name", "HS Code", "UoM", "Sale Type", "Rate", "Quantity",
            "Value Excl. ST", "Sales Tax", "Extra Tax", "ST Withheld", "Further Tax",
            "Discount", "Total"
        ])
        
        # Set column widths
        header = self.items_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Set some fixed widths for certain columns
        self.items_table.setColumnWidth(0, 50)   # Sr.
        self.items_table.setColumnWidth(6, 80)   # Quantity
        
        # Enable alternating row colors
        self.items_table.setAlternatingRowColors(True)
        
        list_layout.addWidget(self.items_table)
        
        # Table action buttons
        table_buttons = QHBoxLayout()
        
        self.edit_item_btn = QPushButton("✏️ Edit Selected")
        self.edit_item_btn.clicked.connect(self.edit_selected_item)
        self.edit_item_btn.setEnabled(False)
        table_buttons.addWidget(self.edit_item_btn)
        
        self.delete_item_btn = QPushButton("🗑️ Delete Selected")
        self.delete_item_btn.setProperty("style", "danger")
        self.delete_item_btn.clicked.connect(self.delete_selected_item)
        self.delete_item_btn.setEnabled(False)
        table_buttons.addWidget(self.delete_item_btn)
        
        table_buttons.addStretch()
        
        # Total summary
        self.total_label = QLabel("Total: PKR 0.00")
        self.total_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #28a745;
                background-color: #2c3b52;
                padding: 8px;
                border-radius: 4px;
            }
        """)
        table_buttons.addWidget(self.total_label)
        
        list_layout.addLayout(table_buttons)
        
        # Connect table selection changed
        self.items_table.selectionModel().selectionChanged.connect(self.on_item_selection_changed)
        
        parent_layout.addWidget(list_group)

    def pre_fill_seller_data(self):
        """Pre-fill seller data from company information"""
        if self.company_data and self.seller_data:
            self.seller_reg_no_edit.setText(self.seller_data.get('sellerNTNCNIC', ''))
            self.seller_name_edit.setText(self.seller_data.get('sellerBusinessName', ''))
            self.seller_address_edit.setText(self.seller_data.get('sellerAddress', ''))
            
            # Set seller province when provinces are loaded
            self.seller_province_to_set = self.seller_data.get('sellerProvince', '')

    def setup_signals(self):
        """Setup signal connections for form interactions"""
        
        # Connect dropdown change events for cascading updates
        self.transaction_type_combo.currentTextChanged.connect(self.on_transaction_type_changed)
        self.sale_type_combo.currentTextChanged.connect(self.on_sale_type_changed)
        self.invoice_date_edit.dateChanged.connect(self.on_date_changed)
        self.sale_origination_combo.currentTextChanged.connect(self.on_origination_changed)
        
        # Connect calculation events
        self.quantity_spin.valueChanged.connect(self.calculate_amounts)
        self.value_excl_st_spin.valueChanged.connect(self.calculate_amounts)
        self.rate_combo.currentTextChanged.connect(self.calculate_tax)

    def populate_dropdowns_from_api(self):
        """Populate dropdowns using FBR API data"""
        if not self.dropdown_manager:
            self._populate_fallback_dropdowns()
            return
        
        # Show loading state
        self.show_loading_state(True)
        
        # Track which dropdowns need to be loaded
        dropdowns_to_load = [
            'provinces',
            'transaction_types'
        ]
        
        self.loading_dropdowns = set(dropdowns_to_load)
        
        # Load each dropdown
        for dropdown_key in dropdowns_to_load:
            self.dropdown_manager.load_dropdown_data(
                dropdown_key, 
                callback=self.on_dropdown_data_loaded
            )

    def on_dropdown_data_loaded(self, dropdown_key: str, data: list):
        """Handle dropdown data loaded from API"""
        try:
            # Format the data for display
            formatted_items = self.dropdown_manager.format_data_for_dropdown(dropdown_key, data)
            
            # Cache the data
            self.dropdown_data_cache[dropdown_key] = {
                'raw_data': data,
                'formatted_items': formatted_items
            }
            
            # Populate the appropriate dropdowns
            self._populate_dropdown_widgets(dropdown_key, formatted_items)
            
            # Remove from loading set
            self.loading_dropdowns.discard(dropdown_key)
            
            # Update loading state
            if not self.loading_dropdowns:
                self.show_loading_state(False)
                
        except Exception as e:
            print(f"Error loading dropdown {dropdown_key}: {e}")
            self.loading_dropdowns.discard(dropdown_key)
            
            if not self.loading_dropdowns:
                self.show_loading_state(False)

    def _populate_dropdown_widgets(self, dropdown_key: str, items: list):
        """Populate specific dropdown widgets with data"""
        
        if dropdown_key == 'provinces':
            self._populate_combo_widget(self.buyer_province_combo, items)
            self._populate_combo_widget(self.sale_origination_combo, items)
            self._populate_combo_widget(self.destination_supply_combo, items)
            
            # Also populate seller province (read-only)
            self.seller_province_combo.clear()
            self.seller_province_combo.addItems(items)
            if hasattr(self, 'seller_province_to_set'):
                index = self.seller_province_combo.findText(self.seller_province_to_set)
                if index >= 0:
                    self.seller_province_combo.setCurrentIndex(index)
            
        elif dropdown_key == 'transaction_types':
            self._populate_combo_widget(self.transaction_type_combo, items)

    def _populate_combo_widget(self, combo_widget: QComboBox, items: list):
        """Populate a combo widget with items and remove loading state"""
        combo_widget.clear()
        combo_widget.addItems(items)
        combo_widget.setProperty("loading", "false")
        combo_widget.setEnabled(True)
        combo_widget.style().polish(combo_widget)  # Refresh styling

    def show_loading_state(self, is_loading: bool):
        """Show or hide loading state"""
        self.loading_label.setVisible(is_loading)
        self.loading_progress.setVisible(is_loading)
        
        if is_loading:
            self.loading_label.setText(f"Loading dropdown data... ({len(self.loading_dropdowns)} remaining)")
            self.save_btn.setEnabled(False)
        else:
            self.loading_label.setText("✅ All data loaded")
            self.save_btn.setEnabled(True)
            
            # Auto-hide after 2 seconds
            QTimer.singleShot(2000, lambda: self.loading_label.setVisible(False))

    def _populate_fallback_dropdowns(self):
        """Fallback method with default values when API is not available"""
        # Fallback province list
        provinces = [
            "Punjab", "Sindh", "Khyber Pakhtunkhwa", "Balochistan",
            "Gilgit-Baltistan", "Azad Kashmir", "Islamabad Capital Territory"
        ]
        
        self.buyer_province_combo.addItems(provinces)
        self.sale_origination_combo.addItems(provinces)
        self.destination_supply_combo.addItems(provinces)
        
        # Fallback transaction types
        self.transaction_type_combo.addItems(["Goods at standard rate (default)"])
        
        # Hide loading state
        self.show_loading_state(False)

    def select_item_from_company(self):
        """Open dialog to select item from company inventory"""
        if not self.db_manager or not self.company_data:
            QMessageBox.warning(self, "Warning", "Company data not available")
            return
            
        dialog = ItemSelectionDialog(
            self.db_manager, 
            self.company_data['ntn_cnic'], 
            self
        )
        dialog.item_selected.connect(self.on_item_selected)
        dialog.exec()

    def add_new_item_to_company(self):
        """Open dialog to add new item to company"""
        if not self.db_manager or not self.company_data:
            QMessageBox.warning(self, "Warning", "Company data not available")
            return
            
        from gui.dialogs.item_dialog import ItemManagementDialog
        dialog = ItemManagementDialog(
            self.db_manager, 
            self.company_data['ntn_cnic'], 
            self
        )
        dialog.exec()

    def on_item_selected(self, item_data):
        """Handle when an item is selected from company inventory"""
        self.selected_item_data = item_data
        
        # Update UI
        self.selected_item_label.setText(f"Selected: {item_data['name']}")
        self.selected_hs_code_label.setText(item_data['hs_code'])
        self.selected_uom_label.setText(item_data['uom'])
        
        self.selected_item_frame.setVisible(True)
        self.add_item_btn.setEnabled(True)
        
        # Load sale type based on current transaction type
        self.load_sale_type_for_item()

    def load_sale_type_for_item(self):
        """Load sale type dropdown based on selected transaction type"""
        transaction_type_text = self.transaction_type_combo.currentText()
        if transaction_type_text and self.selected_item_data:
            # For now, use default sale type
            # In a real implementation, this should query the API based on transaction type
            self.sale_type_combo.clear()
            self.sale_type_combo.addItem("Goods at standard rate (default)")

    def on_transaction_type_changed(self):
        """Handle transaction type change"""
        # Refresh sale type options
        if self.selected_item_data:
            self.load_sale_type_for_item()
        
        # Load rates based on new transaction type
        self.load_rates_for_sale_type()

    def on_sale_type_changed(self):
        """Handle sale type change - update rates"""
        self.load_rates_for_sale_type()

    def load_rates_for_sale_type(self):
        """Load rate dropdown based on sale type and other parameters"""
        if not self.dropdown_manager:
            # Fallback rates
            self.rate_combo.clear()
            self.rate_combo.addItems(["18%", "17%", "16%", "10%", "5%", "0%"])
            return
        
        sale_type_text = self.sale_type_combo.currentText()
        transaction_type_text = self.transaction_type_combo.currentText()
        origination_text = self.sale_origination_combo.currentText()
        
        if not all([sale_type_text, transaction_type_text, origination_text]):
            return
        
        try:
            # Extract IDs from dropdown text
            trans_type_id = self.formatter.extract_id_from_dropdown_text(transaction_type_text, -1)
            origination_id = self._get_province_id_from_text(origination_text)
            
            if trans_type_id and origination_id:
                current_date = FBRDateUtils.format_date_for_fbr(self.invoice_date_edit.date())
                
                # Show loading state for rate combo
                self.rate_combo.setProperty("loading", "true")
                self.rate_combo.setEnabled(False)
                self.rate_combo.style().polish(self.rate_combo)
                
                # Load rate options
                self.dropdown_manager.load_dropdown_data(
                    'sale_type_rates',
                    callback=self.on_sale_type_rates_loaded,
                    date=current_date,
                    trans_type_id=int(trans_type_id),
                    origination_supplier=origination_id
                )
                
        except Exception as e:
            print(f"Error loading rates: {e}")

    def on_sale_type_rates_loaded(self, dropdown_key: str, data: list):
        """Handle sale type rates data loaded"""
        if dropdown_key == 'sale_type_rates':
            formatted_items = self.dropdown_manager.format_data_for_dropdown(dropdown_key, data)
            self._populate_combo_widget(self.rate_combo, formatted_items)

    def _get_province_id_from_text(self, province_text: str):
        """Get province ID from province text"""
        # This should map to actual province data from API
        province_map = {
            'PUNJAB': 7,
            'SINDH': 8,
            'KHYBER PAKHTUNKHWA': 9,
            'BALOCHISTAN': 10,
            'GILGIT-BALTISTAN': 11,
            'AZAD KASHMIR': 12,
            'ISLAMABAD CAPITAL TERRITORY': 13
        }
        return province_map.get(province_text.upper(), 8)  # Default to Sindh

    def on_date_changed(self):
        """Handle date change - refresh date-dependent dropdowns"""
        self.load_rates_for_sale_type()

    def on_origination_changed(self):
        """Handle origination province change - refresh rates"""
        self.load_rates_for_sale_type()

    def calculate_tax(self):
        """Calculate tax based on rate and value"""
        try:
            rate_text = self.rate_combo.currentText()
            if not rate_text:
                return
                
            # Extract rate value from formatted text
            rate_value = 0.0
            if '%' in rate_text:
                # Handle percentage format
                parts = rate_text.split(' - ')
                if len(parts) >= 3:
                    rate_str = parts[2].replace('%', '').strip()
                else:
                    rate_str = rate_text.replace('%', '').strip()
                rate_value = float(rate_str)
            
            value_excl_st = self.value_excl_st_spin.value()
            tax_amount = (value_excl_st * rate_value) / 100
            self.sales_tax_spin.setValue(tax_amount)
            
        except (ValueError, IndexError) as e:
            print(f"Error calculating tax: {e}")

    def calculate_amounts(self):
        """Calculate amounts based on quantity and value"""
        try:
            quantity = self.quantity_spin.value()
            
            # If quantity changed, don't auto-update value
            # Let user enter value per unit
            
            self.calculate_tax()
        except Exception as e:
            print(f"Error calculating amounts: {e}")

    def add_item_to_invoice(self):
        """Add current item to the invoice items list"""
        if not self.selected_item_data:
            QMessageBox.warning(self, "Warning", "Please select an item first!")
            return
            
        # Validate fields
        if self.quantity_spin.value() <= 0:
            QMessageBox.warning(self, "Validation Error", "Quantity must be greater than 0!")
            return
            
        if self.value_excl_st_spin.value() <= 0:
            QMessageBox.warning(self, "Validation Error", "Value of Sales must be greater than 0!")
            return
        
        # Add row to table
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        
        # Calculate total for this item
        value_excl_st = self.value_excl_st_spin.value()
        sales_tax = self.sales_tax_spin.value()
        extra_tax = self.extra_tax_spin.value()
        further_tax = self.further_tax_spin.value()
        discount = self.discount_spin.value()
        
        item_total = value_excl_st + sales_tax + extra_tax + further_tax - discount
        
        # Populate row data
        self.items_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))  # Sr.
        self.items_table.setItem(row, 1, QTableWidgetItem(self.selected_item_data['name']))
        self.items_table.setItem(row, 2, QTableWidgetItem(self.selected_item_data['hs_code']))
        self.items_table.setItem(row, 3, QTableWidgetItem(self.selected_item_data['uom']))
        self.items_table.setItem(row, 4, QTableWidgetItem(self.sale_type_combo.currentText()))
        self.items_table.setItem(row, 5, QTableWidgetItem(self.rate_combo.currentText()))
        self.items_table.setItem(row, 6, QTableWidgetItem(str(self.quantity_spin.value())))
        self.items_table.setItem(row, 7, QTableWidgetItem(f"{value_excl_st:.2f}"))
        self.items_table.setItem(row, 8, QTableWidgetItem(f"{sales_tax:.2f}"))
        self.items_table.setItem(row, 9, QTableWidgetItem(f"{extra_tax:.2f}"))
        self.items_table.setItem(row, 10, QTableWidgetItem(f"{self.st_withheld_spin.value():.2f}"))
        self.items_table.setItem(row, 11, QTableWidgetItem(f"{further_tax:.2f}"))
        self.items_table.setItem(row, 12, QTableWidgetItem(f"{discount:.2f}"))
        self.items_table.setItem(row, 13, QTableWidgetItem(f"{item_total:.2f}"))
        
        # Clear form after adding
        self.clear_item_fields()
        
        # Update totals
        self.update_totals()
        
        # Show success message
        QMessageBox.information(self, "Success", "Item added to invoice successfully!")

    def clear_item_fields(self):
        """Clear item input fields"""
        self.selected_item_data = None
        self.selected_item_frame.setVisible(False)
        self.add_item_btn.setEnabled(False)
        
        self.sale_type_combo.clear()
        self.rate_combo.clear()
        self.quantity_spin.setValue(1.000)
        self.value_excl_st_spin.setValue(0.00)
        self.sales_tax_spin.setValue(0.00)
        self.extra_tax_spin.setValue(0.00)
        self.st_withheld_spin.setValue(0.00)
        self.further_tax_spin.setValue(0.00)
        self.discount_spin.setValue(0.00)

    def edit_selected_item(self):
        """Edit selected item in table"""
        current_row = self.items_table.currentRow()
        if current_row >= 0:
            # Implementation for editing item
            pass
        else:
            QMessageBox.information(self, "Information", "Please select an item to edit")

    def delete_selected_item(self):
        """Delete selected item from table"""
        current_row = self.items_table.currentRow()
        if current_row >= 0:
            reply = QMessageBox.question(
                self, "Confirm Delete",
                "Are you sure you want to delete this item?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.items_table.removeRow(current_row)
                self.update_totals()
                # Update serial numbers
                for i in range(self.items_table.rowCount()):
                    self.items_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
        else:
            QMessageBox.information(self, "Information", "Please select an item to delete")

    def on_item_selection_changed(self):
        """Handle item selection changes in table"""
        has_selection = self.items_table.currentRow() >= 0
        self.edit_item_btn.setEnabled(has_selection)
        self.delete_item_btn.setEnabled(has_selection)

    def update_totals(self):
        """Update total calculations"""
        total_value = 0.0
        total_tax = 0.0
        
        for row in range(self.items_table.rowCount()):
            try:
                item_total = float(self.items_table.item(row, 13).text())
                total_value += item_total
            except:
                continue
        
        self.total_label.setText(f"Invoice Total: PKR {total_value:,.2f}")

    def validate_invoice(self):
        """Validate invoice using FBR API"""
        # Validate form first
        errors = self.validate_form()
        if errors:
            QMessageBox.warning(
                self, "Validation Errors",
                "Please fix the following errors:\n\n" + "\n".join(errors)
            )
            return
        
        try:
            # Build invoice data
            invoice_data = self.get_invoice_data()
            
            # Call FBR validation endpoint
            validation_url = "https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata_sb"
            
            headers = {
                'Authorization': f'Bearer {self.get_auth_token()}',
                'Content-Type': 'application/json'
            }
            
            self.statusBar().showMessage("Validating invoice with FBR...")
            
            response = requests.post(validation_url, json=invoice_data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                validation_response = result.get('validationResponse', {})
                status = validation_response.get('status', 'Unknown')
                error_msg = validation_response.get('error', '')
                
                if status.lower() == 'valid':
                    QMessageBox.information(
                        self, "Validation Result", 
                        "✅ Invoice validation successful!\n\nThe invoice is valid and ready for submission to FBR."
                    )
                else:
                    QMessageBox.warning(
                        self, "Validation Result", 
                        f"❌ Invoice validation failed!\n\nStatus: {status}\nError: {error_msg}"
                    )
            else:
                QMessageBox.warning(
                    self, "Validation Error", 
                    f"Validation failed: {response.status_code}\n{response.text}"
                )
                
        except requests.exceptions.Timeout:
            QMessageBox.critical(self, "Timeout Error", "Request timed out. Please check your connection and try again.")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect to FBR API: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Validation Error", f"Failed to validate invoice: {str(e)}")
        finally:
            if hasattr(self, 'statusBar'):
                self.statusBar().showMessage("Ready")

    def get_auth_token(self):
        """Get authentication token for FBR API"""
        # This should be retrieved from settings or parent window
        if hasattr(self.parent(), 'auth_token_edit'):
            return self.parent().auth_token_edit.text().strip()
        return ""

    def get_invoice_data(self):
        """Get all invoice data from the form"""
        # Collect items from table
        items = []
        for row in range(self.items_table.rowCount()):
            try:
                item = {
                    "hsCode": self.items_table.item(row, 2).text(),
                    "productDescription": self.items_table.item(row, 1).text(),
                    "rate": self.items_table.item(row, 5).text(),
                    "uoM": self.items_table.item(row, 3).text(),
                    "quantity": float(self.items_table.item(row, 6).text()),
                    "totalValues": 0.0,
                    "valueSalesExcludingST": float(self.items_table.item(row, 7).text()),
                    "fixedNotifiedValueOrRetailPrice": 0.0,
                    "salesTaxApplicable": float(self.items_table.item(row, 8).text()),
                    "salesTaxWithheldAtSource": float(self.items_table.item(row, 10).text()),
                    "extraTax": float(self.items_table.item(row, 9).text()),
                    "furtherTax": float(self.items_table.item(row, 11).text()),
                    "sroScheduleNo": "",
                    "fedPayable": 0.0,
                    "discount": float(self.items_table.item(row, 12).text()),
                    "saleType": self.items_table.item(row, 4).text(),
                    "sroItemSerialNo": ""
                }
                items.append(item)
            except Exception as e:
                print(f"Error processing item row {row}: {e}")
                continue
        
        # Build main invoice data
        invoice_data = {
            "invoiceType": self.invoice_type_combo.currentText(),
            "invoiceDate": self.invoice_date_edit.date().toString("yyyy-MM-dd"),
            "sellerNTNCNIC": self.seller_reg_no_edit.text(),
            "sellerBusinessName": self.seller_name_edit.text(),
            "sellerProvince": self.seller_province_combo.currentText(),
            "sellerAddress": self.seller_address_edit.text(),
            "buyerNTNCNIC": self.buyer_reg_no_edit.text(),
            "buyerBusinessName": self.buyer_name_edit.text(),
            "buyerProvince": self.buyer_province_combo.currentText(),
            "buyerAddress": self.buyer_address_edit.text(),
            "buyerRegistrationType": self.buyer_type_combo.currentText(),
            "invoiceRefNo": "",
            "items": items
        }
        
        # Add scenario ID for sandbox mode
        if self.mode == "sandbox":
            invoice_data["scenarioId"] = "SN001"  # Default scenario ID
        
        return invoice_data

    def validate_form(self):
        """Validate the form data"""
        errors = []
        
        # Check required fields
        if not self.buyer_name_edit.text().strip():
            errors.append("Buyer Name is required")
            
        if not self.buyer_reg_no_edit.text().strip():
            errors.append("Buyer Registration Number is required")
            
        if self.items_table.rowCount() == 0:
            errors.append("At least one item is required")
            
        if not self.buyer_province_combo.currentText():
            errors.append("Buyer Province is required")
        
        return errors

    def save_invoice(self):
        """Save the invoice"""
        # Validate form
        errors = self.validate_form()
        if errors:
            QMessageBox.warning(
                self, "Validation Errors",
                "Please fix the following errors:\n\n" + "\n".join(errors)
            )
            return
        
        # Get invoice data
        invoice_data = self.get_invoice_data()
        
        # Add company ID
        if self.company_data:
            invoice_data['company_id'] = self.company_data['ntn_cnic']
        
        # Emit signal with invoice data
        self.invoice_saved.emit(invoice_data)
        
        # Show success message
        QMessageBox.information(
            self, "Success",
            f"Invoice saved successfully!\n"
            f"Mode: {self.mode.title()}\n"
            f"Items: {len(invoice_data['items'])}\n"
            f"Company: {self.company_data['name'] if self.company_data else 'Unknown'}"
        )
        
        # Accept dialog
        self.accept()

    def load_invoice_data(self):
        """Load existing invoice data into the form"""
        if not self.invoice_data:
            return
            
        # Load basic information
        self.buyer_name_edit.setText(self.invoice_data.get('buyerBusinessName', ''))
        self.buyer_reg_no_edit.setText(self.invoice_data.get('buyerNTNCNIC', ''))
        
        # Load dates
        if 'invoiceDate' in self.invoice_data:
            try:
                date_obj = datetime.strptime(self.invoice_data['invoiceDate'], '%Y-%m-%d').date()
                self.invoice_date_edit.setDate(QDate(date_obj))
            except:
                pass
        
        # Load other fields
        if self.invoice_type_combo.count() > 0:
            self.invoice_type_combo.setCurrentText(self.invoice_data.get('invoiceType', 'Sale Invoice'))
        
        # Load items would require more complex logic to match with company items

    def closeEvent(self, event):
        """Clean up when dialog is closed"""
        if self.dropdown_manager:
            self.dropdown_manager.cleanup_threads()
        event.accept()


# Test the dialog
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Test company data
    company_data = {
        'ntn_cnic': '1234567890123',
        'name': 'Test Company Ltd',
        'address': 'Test Address, Karachi'
    }
    
    seller_data = {
        'sellerNTNCNIC': '1234567890123',
        'sellerBusinessName': 'Test Company Ltd',
        'sellerAddress': 'Test Address, Karachi',
        'sellerProvince': 'Sindh'
    }
    
    dialog = CompanySpecificInvoiceDialog(
        mode="sandbox", 
        company_data=company_data, 
        seller_data=seller_data
    )
    dialog.invoice_saved.connect(lambda data: print("Invoice saved:", data))
    
    result = dialog.exec()
    print("Dialog result:", result)
    
    sys.exit(app.exec())