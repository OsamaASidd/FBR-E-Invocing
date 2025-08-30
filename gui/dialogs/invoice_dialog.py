# gui/dialogs/invoice_dialog.py - Updated with FBR API integration
import sys
from datetime import datetime, date
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFormLayout, QWidget, QPushButton, QTableWidget, QTableWidgetItem,
    QLabel, QLineEdit, QComboBox, QGroupBox, QDateEdit, QCheckBox,
    QSpinBox, QDoubleSpinBox, QTextEdit, QHeaderView, QMessageBox,
    QDialogButtonBox, QTabWidget, QScrollArea, QSplitter, QProgressBar
)
from PyQt6.QtCore import QDate, Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor

# Import the new FBR API service
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
    """Enhanced FBR Invoice Dialog with API integration for dropdowns"""
    
    invoice_saved = pyqtSignal(dict)  # Signal when invoice is saved
    
    def __init__(self, parent=None, invoice_data=None, mode="sandbox"):
        super().__init__(parent)
        self.invoice_data = invoice_data
        self.mode = mode.lower()
        self.is_editing = invoice_data is not None
        
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

            /* Combobox styling */
            QComboBox::drop-down, QDateEdit::drop-down {
                width: 26px;
                border-left: 1px solid #334561;
            }
            QComboBox::down-arrow, QDateEdit::down-arrow {
                image: none;
                width: 0; height: 0; margin: 0;
            }

            /* Loading state styling */
            QComboBox[loading="true"] {
                background: #1a1a1a;
                color: #888;
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
        self.create_buyer_seller_section(scroll_layout)
        self.create_item_details_section(scroll_layout)
        self.create_items_list_section(scroll_layout)
        
        # Setup scroll area
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        main_layout.addWidget(scroll_area)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_invoice)
        button_box.rejected.connect(self.reject)
        
        # Customize buttons
        save_btn = button_box.button(QDialogButtonBox.StandardButton.Save)
        save_btn.setText("💾 Save Invoice")
        save_btn.setStyleSheet("background-color: #28a745;")
        self.save_btn = save_btn  # Keep reference for enabling/disabling
        
        cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("❌ Cancel")
        cancel_btn.setStyleSheet("background-color: #dc3545;")
        
        main_layout.addWidget(button_box)

    def create_buyer_seller_section(self, parent_layout):
        """Create seller + buyer information section with API-populated dropdowns"""
        section_group = QGroupBox("FBR Invoice Details")
        section_layout = QGridLayout(section_group)
        section_layout.setContentsMargins(14, 10, 14, 12)
        section_layout.setHorizontalSpacing(18)
        section_layout.setVerticalSpacing(10)

        self._req_lbl = lambda t: f"{t}<span style='color:#1e90ff'>*</span>"

        # -------- Row 0: SELLER --------
        section_layout.addWidget(QLabel(self._req_lbl("Seller NTN/CNIC")), 0, 1)
        self.seller_reg_no_edit = QLineEdit()
        section_layout.addWidget(self.seller_reg_no_edit, 0, 2)

        section_layout.addWidget(QLabel(self._req_lbl("Seller Name")), 0, 3)
        self.seller_name_edit = QLineEdit()
        section_layout.addWidget(self.seller_name_edit, 0, 4)

        section_layout.addWidget(QLabel(self._req_lbl("Seller Province")), 0, 5)
        self.seller_province_combo = QComboBox()
        self.seller_province_combo.setProperty("loading", "true")
        section_layout.addWidget(self.seller_province_combo, 0, 6)

        section_layout.addWidget(QLabel("Seller Address:"), 1, 1)
        self.seller_address_edit = QLineEdit()
        self.seller_address_edit.setPlaceholderText("Company address / branch")
        section_layout.addWidget(self.seller_address_edit, 1, 2, 1, 2)

        # -------- Row 2: BUYER --------
        section_layout.addWidget(QLabel(self._req_lbl("Buyer Registration No.")), 2, 1)
        self.buyer_reg_no_edit = QLineEdit()
        section_layout.addWidget(self.buyer_reg_no_edit, 2, 2)

        section_layout.addWidget(QLabel(self._req_lbl("Buyer Name")), 2, 3)
        self.buyer_name_edit = QLineEdit()
        self.buyer_name_edit.setPlaceholderText("Enter buyer name")
        section_layout.addWidget(self.buyer_name_edit, 2, 4)

        section_layout.addWidget(QLabel("Buyer Type:"), 2, 5)
        self.buyer_type_combo = QComboBox()
        self.buyer_type_combo.addItems(["Registered", "Unregistered"])
        section_layout.addWidget(self.buyer_type_combo, 2, 6)

        # -------- Row 3: BUYER Province --------
        section_layout.addWidget(QLabel(self._req_lbl("Buyer Province")), 3, 1)
        self.buyer_province_combo = QComboBox()
        self.buyer_province_combo.setProperty("loading", "true")
        section_layout.addWidget(self.buyer_province_combo, 3, 2)

        section_layout.addWidget(QLabel("Buyer Address:"), 3, 3)
        self.buyer_address_edit = QLineEdit()
        self.buyer_address_edit.setPlaceholderText("Street/area, city, district")
        section_layout.addWidget(self.buyer_address_edit, 3, 4)

        # -------- Row 4: Invoice meta --------
        section_layout.addWidget(QLabel(self._req_lbl("Invoice Type")), 4, 1)
        self.invoice_type_combo = QComboBox()
        self.invoice_type_combo.setProperty("loading", "true")
        section_layout.addWidget(self.invoice_type_combo, 4, 2)

        section_layout.addWidget(QLabel("Invoice No.:"), 4, 3)
        self.invoice_no_edit = QLineEdit()
        self.invoice_no_edit.setPlaceholderText("Auto-generated")
        self.invoice_no_edit.setReadOnly(True)
        section_layout.addWidget(self.invoice_no_edit, 4, 4)

        section_layout.addWidget(QLabel(self._req_lbl("Invoice Date")), 4, 5)
        self.invoice_date_edit = QDateEdit(QDate.currentDate())
        self.invoice_date_edit.setCalendarPopup(True)
        self.invoice_date_edit.setDisplayFormat("d/M/yyyy")
        section_layout.addWidget(self.invoice_date_edit, 4, 6)

        # -------- Row 5: Supply info --------
        section_layout.addWidget(QLabel(self._req_lbl("Sale Origination Province of Supplier")), 5, 1)
        self.sale_origination_combo = QComboBox()
        self.sale_origination_combo.setProperty("loading", "true")
        section_layout.addWidget(self.sale_origination_combo, 5, 2)

        section_layout.addWidget(QLabel(self._req_lbl("Destination of Supply")), 5, 3)
        self.destination_supply_combo = QComboBox()
        self.destination_supply_combo.setProperty("loading", "true")
        section_layout.addWidget(self.destination_supply_combo, 5, 4)

        section_layout.addWidget(QLabel(self._req_lbl("Sale Type")), 5, 5)
        self.sale_type_combo = QComboBox()
        self.sale_type_combo.setProperty("loading", "true")
        section_layout.addWidget(self.sale_type_combo, 5, 6)

        # Column sizing
        section_layout.setColumnStretch(0, 1)
        section_layout.setColumnStretch(1, 0)
        section_layout.setColumnStretch(2, 2)
        section_layout.setColumnStretch(3, 0)
        section_layout.setColumnStretch(4, 2)
        section_layout.setColumnStretch(5, 0)
        section_layout.setColumnStretch(6, 2)

        parent_layout.addWidget(section_group)

    def create_item_details_section(self, parent_layout):
        """Create item detail entry section with API-populated dropdowns"""
        item_group = QGroupBox("📦 Item Detail")
        item_layout = QGridLayout(item_group)
        
        # Row 1: HS Code, Product Description
        item_layout.addWidget(QLabel("HS Code Description*:"), 0, 0)
        self.hs_code_combo = QComboBox()
        self.hs_code_combo.setEditable(True)
        self.hs_code_combo.setProperty("loading", "true")
        item_layout.addWidget(self.hs_code_combo, 0, 1, 1, 2)
        
        item_layout.addWidget(QLabel("Product Description*:"), 0, 3)
        self.product_desc_edit = QLineEdit()
        self.product_desc_edit.setPlaceholderText("Enter product description")
        item_layout.addWidget(self.product_desc_edit, 0, 4, 1, 3)
        
        # Row 2: Rate, UoM, Quantity
        item_layout.addWidget(QLabel("Rate*:"), 1, 0)
        self.rate_combo = QComboBox()
        self.rate_combo.setEditable(True)
        self.rate_combo.setProperty("loading", "true")
        item_layout.addWidget(self.rate_combo, 1, 1)
        
        item_layout.addWidget(QLabel("UoM*:"), 1, 2)
        self.uom_combo = QComboBox()
        self.uom_combo.setProperty("loading", "true")
        item_layout.addWidget(self.uom_combo, 1, 3)
        
        item_layout.addWidget(QLabel("Quantity/Electricity Units*:"), 1, 4)
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.001, 999999.999)
        self.quantity_spin.setDecimals(3)
        self.quantity_spin.setValue(1.000)
        item_layout.addWidget(self.quantity_spin, 1, 5, 1, 2)
        
        # Row 3: Financial fields
        item_layout.addWidget(QLabel("Value of Sales Excl. ST*:"), 2, 0)
        self.value_excl_st_spin = QDoubleSpinBox()
        self.value_excl_st_spin.setRange(0.00, 99999999.99)
        self.value_excl_st_spin.setDecimals(2)
        item_layout.addWidget(self.value_excl_st_spin, 2, 1)
        
        item_layout.addWidget(QLabel("Sales Tax:"), 2, 2)
        self.sales_tax_spin = QDoubleSpinBox()
        self.sales_tax_spin.setRange(0.00, 99999999.99)
        self.sales_tax_spin.setDecimals(2)
        item_layout.addWidget(self.sales_tax_spin, 2, 3)
        
        item_layout.addWidget(QLabel("Fixed/Notified Value or Retail Price:"), 2, 4)
        self.fixed_value_spin = QDoubleSpinBox()
        self.fixed_value_spin.setRange(0.00, 99999999.99)
        self.fixed_value_spin.setDecimals(2)
        item_layout.addWidget(self.fixed_value_spin, 2, 5, 1, 2)
        
        # Row 4: Tax fields
        item_layout.addWidget(QLabel("ST withheld at Source:"), 3, 0)
        self.st_withheld_spin = QDoubleSpinBox()
        self.st_withheld_spin.setRange(0.00, 99999999.99)
        self.st_withheld_spin.setDecimals(2)
        item_layout.addWidget(self.st_withheld_spin, 3, 1)
        
        item_layout.addWidget(QLabel("Extra Tax:"), 3, 2)
        self.extra_tax_spin = QDoubleSpinBox()
        self.extra_tax_spin.setRange(0.00, 99999999.99)
        self.extra_tax_spin.setDecimals(2)
        item_layout.addWidget(self.extra_tax_spin, 3, 3)
        
        item_layout.addWidget(QLabel("Further Tax:"), 3, 4)
        self.further_tax_spin = QDoubleSpinBox()
        self.further_tax_spin.setRange(0.00, 99999999.99)
        self.further_tax_spin.setDecimals(2)
        item_layout.addWidget(self.further_tax_spin, 3, 5)
        
        # Row 5: Additional fields
        item_layout.addWidget(QLabel("Total Value of Sales (in case of PFAD only):"), 4, 0, 1, 2)
        self.total_value_pfad_spin = QDoubleSpinBox()
        self.total_value_pfad_spin.setRange(0.00, 99999999.99)
        self.total_value_pfad_spin.setDecimals(2)
        item_layout.addWidget(self.total_value_pfad_spin, 4, 2)
        
        item_layout.addWidget(QLabel("SRO/Schedule No:"), 4, 3)
        self.sro_schedule_combo = QComboBox()
        self.sro_schedule_combo.setEditable(True)
        self.sro_schedule_combo.setProperty("loading", "true")
        item_layout.addWidget(self.sro_schedule_combo, 4, 4)
        
        item_layout.addWidget(QLabel("Item Sr. No:"), 4, 5)
        self.item_sr_combo = QComboBox()
        self.item_sr_combo.setProperty("loading", "true")
        item_layout.addWidget(self.item_sr_combo, 4, 6)
        
        # Row 6: Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.add_item_btn = QPushButton("➕ Add Item")
        self.add_item_btn.clicked.connect(self.add_item_to_list)
        self.add_item_btn.setStyleSheet("background-color: #28a745;")
        button_layout.addWidget(self.add_item_btn)
        
        self.clear_item_btn = QPushButton("🗑️ Clear")
        self.clear_item_btn.clicked.connect(self.clear_item_fields)
        self.clear_item_btn.setStyleSheet("background-color: #6c757d;")
        button_layout.addWidget(self.clear_item_btn)
        
        item_layout.addLayout(button_layout, 5, 0, 1, 7)
        
        parent_layout.addWidget(item_group)

    def create_items_list_section(self, parent_layout):
        """Create items list table section"""
        list_group = QGroupBox("📋 Item(s) List")
        list_layout = QVBoxLayout(list_group)
        
        # Items table
        self.items_table = QTableWidget(0, 17)
        self.items_table.setHorizontalHeaderLabels([
            "Sr. No.", "Action", "Status", "Remarks", "Invoice Type",
            "Invoice No.", "Description", "Product Description",
            "HS Code Description", "Sale Type", "Rate", "Quantity",
            "UoM", "Value of Sales Excl. ST", "Sales Tax", "Extra Tax", "ST with Source"
        ])
        
        # Set column widths
        header = self.items_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Set some fixed widths for certain columns
        self.items_table.setColumnWidth(0, 60)   # Sr. No.
        self.items_table.setColumnWidth(1, 80)   # Action
        self.items_table.setColumnWidth(2, 80)   # Status
        self.items_table.setColumnWidth(11, 80)  # Quantity
        self.items_table.setColumnWidth(12, 60)  # UoM
        
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
        self.delete_item_btn.clicked.connect(self.delete_selected_item)
        self.delete_item_btn.setEnabled(False)
        self.delete_item_btn.setStyleSheet("background-color: #dc3545;")
        table_buttons.addWidget(self.delete_item_btn)
        
        table_buttons.addStretch()
        
        # Total summary
        self.total_label = QLabel("Total: PKR 0.00")
        self.total_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #28a745;
                background-color: #f8f9fa;
                padding: 8px;
                border-radius: 4px;
            }
        """)
        table_buttons.addWidget(self.total_label)
        
        list_layout.addLayout(table_buttons)
        
        # Connect table selection changed
        self.items_table.selectionModel().selectionChanged.connect(self.on_item_selection_changed)
        
        parent_layout.addWidget(list_group)

    def setup_signals(self):
        """Setup signal connections for form interactions"""
        
        # Connect dropdown change events for cascading updates
        self.hs_code_combo.currentTextChanged.connect(self.on_hs_code_changed)
        self.sale_type_combo.currentTextChanged.connect(self.on_sale_type_changed)
        self.sro_schedule_combo.currentTextChanged.connect(self.on_sro_schedule_changed)
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
            'document_types', 
            'hs_codes',
            'sro_item_codes',
            'transaction_types',
            'uom_types'
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
        
        # Remove loading state from widgets
        if dropdown_key == 'provinces':
            self._populate_combo_widget(self.seller_province_combo, items)
            self._populate_combo_widget(self.buyer_province_combo, items)
            self._populate_combo_widget(self.sale_origination_combo, items)
            self._populate_combo_widget(self.destination_supply_combo, items)
            
        elif dropdown_key == 'document_types':
            self._populate_combo_widget(self.invoice_type_combo, items)
            
        elif dropdown_key == 'hs_codes':
            self._populate_combo_widget(self.hs_code_combo, items)
            
        elif dropdown_key == 'sro_item_codes':
            self._populate_combo_widget(self.item_sr_combo, items)
            
        elif dropdown_key == 'transaction_types':
            self._populate_combo_widget(self.sale_type_combo, items)
            
        elif dropdown_key == 'uom_types':
            self._populate_combo_widget(self.uom_combo, items)

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

    def on_hs_code_changed(self):
        """Handle HS code change - filter UOM options"""
        if not self.dropdown_manager:
            return
            
        hs_code_text = self.hs_code_combo.currentText()
        if not hs_code_text:
            return
            
        # Extract HS code from formatted text
        hs_code = self.formatter.extract_hs_code_from_dropdown_text(hs_code_text)
        
        if hs_code:
            # Show loading state for UOM combo
            self.uom_combo.setProperty("loading", "true")
            self.uom_combo.setEnabled(False)
            self.uom_combo.style().polish(self.uom_combo)
            
            # Load filtered UOM options
            self.dropdown_manager.load_dropdown_data(
                'hs_uom',
                callback=self.on_hs_uom_loaded,
                hs_code=hs_code,
                annexure_id=3
            )

    def on_hs_uom_loaded(self, dropdown_key: str, data: list):
        """Handle HS-filtered UOM data loaded"""
        if dropdown_key == 'hs_uom':
            formatted_items = self.dropdown_manager.format_data_for_dropdown(dropdown_key, data)
            self._populate_combo_widget(self.uom_combo, formatted_items)

    def on_sale_type_changed(self):
        """Handle sale type change - update rates"""
        if not self.dropdown_manager:
            return
            
        sale_type_text = self.sale_type_combo.currentText()
        if not sale_type_text:
            return
        
        # Extract transaction type ID
        trans_type_id = self.formatter.extract_id_from_dropdown_text(sale_type_text, -1)
        
        # Get current date and origination province
        current_date = FBRDateUtils.format_date_for_fbr(self.invoice_date_edit.date())
        origination_text = self.sale_origination_combo.currentText()
        
        if trans_type_id and origination_text:
            # For now, use province index as ID (this should be mapped properly)
            origination_id = self._get_province_id_from_text(origination_text)
            
            if origination_id:
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

    def on_sale_type_rates_loaded(self, dropdown_key: str, data: list):
        """Handle sale type rates data loaded"""
        if dropdown_key == 'sale_type_rates':
            formatted_items = self.dropdown_manager.format_data_for_dropdown(dropdown_key, data)
            self._populate_combo_widget(self.rate_combo, formatted_items)

    def on_sro_schedule_changed(self):
        """Handle SRO schedule change - update item serial numbers"""
        if not self.dropdown_manager:
            return
            
        sro_text = self.sro_schedule_combo.currentText()
        if not sro_text:
            return
        
        # Extract SRO ID
        sro_id = self.formatter.extract_id_from_dropdown_text(sro_text, -1)
        current_date = FBRDateUtils.format_date_iso(self.invoice_date_edit.date())
        
        if sro_id:
            # Load SRO items
            self.dropdown_manager.load_dropdown_data(
                'sro_items',
                callback=self.on_sro_items_loaded,
                date=current_date,
                sro_id=int(sro_id)
            )

    def on_sro_items_loaded(self, dropdown_key: str, data: list):
        """Handle SRO items data loaded"""
        if dropdown_key == 'sro_items':
            formatted_items = self.dropdown_manager.format_data_for_dropdown(dropdown_key, data)
            self._populate_combo_widget(self.item_sr_combo, formatted_items)

    def on_date_changed(self):
        """Handle date change - refresh date-dependent dropdowns"""
        # This could trigger refresh of rate and SRO data if needed
        pass

    def on_origination_changed(self):
        """Handle origination province change - refresh rates"""
        # This could trigger refresh of rate data
        pass

    def _get_province_id_from_text(self, province_text: str):
        """Get province ID from province text (this should map to actual API data)"""
        # This is a simplified mapping - you should use the actual province data from API
        province_map = {
            'PUNJAB': 7,
            'SINDH': 8,
            # Add other provinces as needed
        }
        return province_map.get(province_text.upper())

    def _populate_fallback_dropdowns(self):
        """Fallback method with default values when API is not available"""
        # Fallback province list
        provinces = [
            "Punjab", "Sindh", "Khyber Pakhtunkhwa", "Balochistan",
            "Gilgit-Baltistan", "Azad Kashmir", "Islamabad Capital Territory"
        ]
        
        self.seller_province_combo.addItems(provinces)
        self.buyer_province_combo.addItems(provinces)
        self.sale_origination_combo.addItems(provinces)
        self.destination_supply_combo.addItems(provinces)
        
        # Fallback invoice types
        self.invoice_type_combo.addItems(["Sale Invoice", "Debit Note"])
        
        # Fallback HS codes
        self.hs_code_combo.addItems(["9999.0000 - General/Other"])
        
        # Fallback UOM
        self.uom_combo.addItems(["Numbers, pieces, units", "Kg", "Meter"])
        
        # Fallback rates
        self.rate_combo.addItems(["18%", "17%", "16%", "10%", "5%", "0%"])
        
        # Hide loading state
        self.show_loading_state(False)

    def calculate_tax(self):
        """Calculate tax based on rate and value"""
        try:
            rate_text = self.rate_combo.currentText()
            if not rate_text:
                return
                
            # Extract rate value from formatted text
            parts = rate_text.split(' - ')
            if len(parts) >= 3:
                rate_str = parts[2].replace('%', '').strip()
                rate = float(rate_str)
                
                value_excl_st = self.value_excl_st_spin.value()
                tax_amount = (value_excl_st * rate) / 100
                self.sales_tax_spin.setValue(tax_amount)
                
        except (ValueError, IndexError):
            pass

    def calculate_amounts(self):
        """Calculate amounts based on quantity and value"""
        try:
            quantity = self.quantity_spin.value()
            value_per_unit = self.value_excl_st_spin.value()
            
            if quantity > 0 and value_per_unit > 0:
                total_value = quantity * value_per_unit
                self.value_excl_st_spin.setValue(total_value)
                self.calculate_tax()
        except:
            pass

    def add_item_to_list(self):
        """Add current item details to the items list"""
        # Validate required fields
        if not self.product_desc_edit.text().strip():
            QMessageBox.warning(self, "Validation Error", "Product Description is required!")
            return
            
        if not self.hs_code_combo.currentText().strip():
            QMessageBox.warning(self, "Validation Error", "HS Code is required!")
            return
            
        if self.quantity_spin.value() <= 0:
            QMessageBox.warning(self, "Validation Error", "Quantity must be greater than 0!")
            return
            
        if self.value_excl_st_spin.value() <= 0:
            QMessageBox.warning(self, "Validation Error", "Value of Sales must be greater than 0!")
            return
        
        # Add row to table
        row = self.items_table.rowCount()
        self.items_table.insertRow(row)
        
        # Populate row data
        self.items_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))  # Sr. No.
        
        # Action buttons
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(2, 2, 2, 2)
        
        edit_btn = QPushButton("✏️")
        edit_btn.setMaximumSize(25, 25)
        edit_btn.clicked.connect(lambda: self.edit_item_row(row))
        action_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️")
        delete_btn.setMaximumSize(25, 25)
        delete_btn.setStyleSheet("background-color: #dc3545;")
        delete_btn.clicked.connect(lambda: self.delete_item_row(row))
        action_layout.addWidget(delete_btn)
        
        self.items_table.setCellWidget(row, 1, action_widget)
        
        # Other fields
        self.items_table.setItem(row, 2, QTableWidgetItem("Pending"))  # Status
        self.items_table.setItem(row, 3, QTableWidgetItem(""))  # Remarks
        self.items_table.setItem(row, 4, QTableWidgetItem(self.invoice_type_combo.currentText()))
        self.items_table.setItem(row, 5, QTableWidgetItem(self.invoice_no_edit.text()))
        self.items_table.setItem(row, 6, QTableWidgetItem(self.product_desc_edit.text()))
        self.items_table.setItem(row, 7, QTableWidgetItem(self.product_desc_edit.text()))
        self.items_table.setItem(row, 8, QTableWidgetItem(self.hs_code_combo.currentText()))
        self.items_table.setItem(row, 9, QTableWidgetItem(self.sale_type_combo.currentText()))
        self.items_table.setItem(row, 10, QTableWidgetItem(self.rate_combo.currentText()))
        self.items_table.setItem(row, 11, QTableWidgetItem(str(self.quantity_spin.value())))
        self.items_table.setItem(row, 12, QTableWidgetItem(self.uom_combo.currentText()))
        self.items_table.setItem(row, 13, QTableWidgetItem(f"{self.value_excl_st_spin.value():.2f}"))
        self.items_table.setItem(row, 14, QTableWidgetItem(f"{self.sales_tax_spin.value():.2f}"))
        self.items_table.setItem(row, 15, QTableWidgetItem(f"{self.extra_tax_spin.value():.2f}"))
        self.items_table.setItem(row, 16, QTableWidgetItem(f"{self.st_withheld_spin.value():.2f}"))
        
        # Clear form after adding
        self.clear_item_fields()
        
        # Update totals
        self.update_totals()
        
        # Show success message
        QMessageBox.information(self, "Success", "Item added successfully!")

    def clear_item_fields(self):
        """Clear all item input fields"""
        self.product_desc_edit.clear()
        if self.hs_code_combo.count() > 0:
            self.hs_code_combo.setCurrentIndex(0)
        if self.rate_combo.count() > 0:
            self.rate_combo.setCurrentText("18%")
        if self.uom_combo.count() > 0:
            self.uom_combo.setCurrentIndex(0)
        self.quantity_spin.setValue(1.000)
        self.value_excl_st_spin.setValue(0.00)
        self.sales_tax_spin.setValue(0.00)
        self.fixed_value_spin.setValue(0.00)
        self.st_withheld_spin.setValue(0.00)
        self.extra_tax_spin.setValue(0.00)
        self.further_tax_spin.setValue(0.00)
        self.total_value_pfad_spin.setValue(0.00)
        if self.sro_schedule_combo.count() > 0:
            self.sro_schedule_combo.setCurrentIndex(0)

    def edit_item_row(self, row):
        """Edit specific item row"""
        # Load item data back into form
        try:
            self.product_desc_edit.setText(self.items_table.item(row, 6).text())
            self.hs_code_combo.setCurrentText(self.items_table.item(row, 8).text())
            self.rate_combo.setCurrentText(self.items_table.item(row, 10).text())
            self.quantity_spin.setValue(float(self.items_table.item(row, 11).text()))
            self.uom_combo.setCurrentText(self.items_table.item(row, 12).text())
            self.value_excl_st_spin.setValue(float(self.items_table.item(row, 13).text()))
            self.sales_tax_spin.setValue(float(self.items_table.item(row, 14).text()))
            
            # Delete the row
            self.items_table.removeRow(row)
            
            # Update totals
            self.update_totals()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to edit item: {str(e)}")

    def delete_item_row(self, row):
        """Delete specific item row"""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this item?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.items_table.removeRow(row)
            self.update_totals()
            # Update serial numbers
            for i in range(self.items_table.rowCount()):
                self.items_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))

    def edit_selected_item(self):
        """Edit currently selected item"""
        current_row = self.items_table.currentRow()
        if current_row >= 0:
            self.edit_item_row(current_row)

    def delete_selected_item(self):
        """Delete currently selected item"""
        current_row = self.items_table.currentRow()
        if current_row >= 0:
            self.delete_item_row(current_row)

    def on_item_selection_changed(self):
        """Handle item selection changes"""
        has_selection = self.items_table.currentRow() >= 0
        self.edit_item_btn.setEnabled(has_selection)
        self.delete_item_btn.setEnabled(has_selection)

    def update_totals(self):
        """Update total calculations"""
        total_value = 0.0
        total_tax = 0.0
        
        for row in range(self.items_table.rowCount()):
            try:
                value = float(self.items_table.item(row, 13).text())
                tax = float(self.items_table.item(row, 14).text())
                total_value += value
                total_tax += tax
            except:
                continue
        
        grand_total = total_value + total_tax
        self.total_label.setText(f"Total: PKR {grand_total:,.2f} (Value: {total_value:,.2f} + Tax: {total_tax:,.2f})")

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
        if hasattr(self, 'invoice_type_combo') and self.invoice_type_combo.count() > 0:
            self.invoice_type_combo.setCurrentText(self.invoice_data.get('invoiceType', 'Sale Invoice'))
        
        # Load items
        items = self.invoice_data.get('items', [])
        for item in items:
            self.load_item_into_form(item)
            self.add_item_to_list()

    def load_item_into_form(self, item):
        """Load item data into the form fields"""
        self.product_desc_edit.setText(item.get('productDescription', ''))
        if self.hs_code_combo.count() > 0:
            self.hs_code_combo.setCurrentText(item.get('hsCode', ''))
        if self.rate_combo.count() > 0:
            self.rate_combo.setCurrentText(item.get('rate', '18%'))
        self.quantity_spin.setValue(item.get('quantity', 1.0))
        if self.uom_combo.count() > 0:
            self.uom_combo.setCurrentText(item.get('uoM', ''))
        self.value_excl_st_spin.setValue(item.get('valueSalesExcludingST', 0.0))
        self.sales_tax_spin.setValue(item.get('salesTaxApplicable', 0.0))

    def get_invoice_data(self):
        """Get all invoice data from the form"""
        # Collect items from table
        items = []
        for row in range(self.items_table.rowCount()):
            try:
                item = {
                    "hsCode": self.formatter.extract_hs_code_from_dropdown_text(self.items_table.item(row, 8).text()),
                    "productDescription": self.items_table.item(row, 6).text(),
                    "rate": self.items_table.item(row, 10).text(),
                    "uoM": self.items_table.item(row, 12).text(),
                    "quantity": float(self.items_table.item(row, 11).text()),
                    "totalValues": 0.0,
                    "valueSalesExcludingST": float(self.items_table.item(row, 13).text()),
                    "fixedNotifiedValueOrRetailPrice": 0.0,
                    "salesTaxApplicable": float(self.items_table.item(row, 14).text()),
                    "salesTaxWithheldAtSource": float(self.items_table.item(row, 16).text()),
                    "extraTax": float(self.items_table.item(row, 15).text()),
                    "furtherTax": 0.0,
                    "sroScheduleNo": "",
                    "fedPayable": 0.0,
                    "discount": 0.0,
                    "saleType": self.items_table.item(row, 9).text(),
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
            
        # Check items for required fields
        for row in range(self.items_table.rowCount()):
            try:
                if not self.items_table.item(row, 6) or not self.items_table.item(row, 6).text().strip():
                    errors.append(f"Product Description is required for item {row + 1}")
                    
                if not self.items_table.item(row, 8) or not self.items_table.item(row, 8).text().strip():
                    errors.append(f"HS Code is required for item {row + 1}")
                    
                quantity = float(self.items_table.item(row, 11).text())
                if quantity <= 0:
                    errors.append(f"Quantity must be greater than 0 for item {row + 1}")
                    
                value = float(self.items_table.item(row, 13).text())
                if value <= 0:
                    errors.append(f"Value must be greater than 0 for item {row + 1}")
                    
            except Exception as e:
                errors.append(f"Invalid data in item {row + 1}: {str(e)}")
        
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
        
        # Emit signal with invoice data
        self.invoice_saved.emit(invoice_data)
        
        # Show success message
        QMessageBox.information(
            self, "Success",
            f"Invoice saved successfully!\n"
            f"Mode: {self.mode.title()}\n"
            f"Items: {len(invoice_data['items'])}"
        )
        
        # Accept dialog
        self.accept()

    def closeEvent(self, event):
        """Clean up when dialog is closed"""
        if self.dropdown_manager:
            self.dropdown_manager.cleanup_threads()
        event.accept()


# Test the dialog
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Test with sample data
    sample_data = {
        "invoiceType": "Sale Invoice",
        "invoiceDate": "2025-04-21",
        "buyerBusinessName": "Test Customer",
        "buyerNTNCNIC": "1234567890123",
        "items": [
            {
                "hsCode": "9999.0000",
                "productDescription": "Test Product",
                "rate": "18%",
                "uoM": "Numbers, pieces, units",
                "quantity": 2.0,
                "valueSalesExcludingST": 1000.0,
                "salesTaxApplicable": 180.0
            }
        ]
    }
    
    # Test in sandbox mode
    dialog = FBRInvoiceDialog(mode="sandbox", invoice_data=sample_data)
    dialog.invoice_saved.connect(lambda data: print("Invoice saved:", data))
    
    result = dialog.exec()
    print("Dialog result:", result)
    
    sys.exit(app.exec())