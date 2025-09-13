# gui/dialogs/item_dialog.py - Updated with FBR API Integration
import sys
import requests
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QTextEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QGroupBox, QMessageBox, QDialogButtonBox,
    QHeaderView, QFrame, QApplication, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont

from fbr_core.models import Item

# Import the FBR API service
try:
    from fbr_core.fbr_api_service import FBRDropdownManager, DropdownDataFormatter
except ImportError as e:
    print(f"Warning: Could not import FBR API service: {e}")
    # Fallback classes for when API service is not available
    class FBRDropdownManager:
        def __init__(self, db_manager): pass
        def load_dropdown_data(self, *args, **kwargs): pass
        def format_data_for_dropdown(self, key, data): return []
        def cleanup_threads(self): pass
    
    class DropdownDataFormatter:
        @staticmethod
        def extract_hs_code_from_dropdown_text(text): 
            try: return text.split(' - ')[0].strip()
            except: return ""


class FBRAPIThread(QThread):
    """Background thread for FBR API calls"""
    
    data_received = pyqtSignal(str, list)  # endpoint_key, data
    error_occurred = pyqtSignal(str, str)  # endpoint_key, error_message
    
    def __init__(self, endpoint_key, api_url, headers=None, params=None):
        super().__init__()
        self.endpoint_key = endpoint_key
        self.api_url = api_url
        self.headers = headers or {}
        self.params = params or {}
    
    def run(self):
        """Execute the API call in background thread"""
        try:
            response = requests.get(
                self.api_url, 
                headers=self.headers, 
                params=self.params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            if data and isinstance(data, list):
                self.data_received.emit(self.endpoint_key, data)
            else:
                self.error_occurred.emit(self.endpoint_key, "No data received from API")
                
        except requests.exceptions.Timeout:
            self.error_occurred.emit(self.endpoint_key, "Request timed out")
        except requests.exceptions.HTTPError as e:
            self.error_occurred.emit(self.endpoint_key, f"HTTP error: {e}")
        except requests.exceptions.RequestException as e:
            self.error_occurred.emit(self.endpoint_key, f"Request error: {e}")
        except Exception as e:
            self.error_occurred.emit(self.endpoint_key, f"Unexpected error: {e}")


class ItemManagementDialog(QDialog):
    """Dialog for managing company-specific items with FBR API integration"""
    
    def __init__(self, db_manager, company_id, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.company_id = company_id
        self.parent_window = parent
        
        # API integration
        self.dropdown_manager = FBRDropdownManager(self.db_manager) if self.db_manager else None
        self.formatter = DropdownDataFormatter()
        self.loading_threads = {}
        
        self.setWindowTitle("Item Management")
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
                min-height: 34px;
            }
            QComboBox:focus, QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #5aa2ff;
                box-shadow: 0 0 0 2px rgba(90,162,255,0.18);
            }
            QLineEdit:read-only {
                background: #2c3b52;
                color: #cccccc;
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
        
        # Load FBR data
        self.load_fbr_dropdown_data()
        
        # Load existing items
        self.load_items()

    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Title with loading indicator
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Item Management")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #5aa2ff; margin: 10px 0;")
        header_layout.addWidget(title_label)
        
        # Loading indicator
        self.loading_label = QLabel("Loading FBR data...")
        self.loading_label.setStyleSheet("color: #ffc107; font-weight: bold;")
        self.loading_progress = QProgressBar()
        self.loading_progress.setRange(0, 0)  # Indeterminate
        self.loading_progress.setMaximumHeight(4)
        
        header_layout.addWidget(self.loading_label)
        header_layout.addWidget(self.loading_progress)
        
        layout.addLayout(header_layout)
        
        # Create item form
        self.create_item_form(layout)
        
        # Items table
        self.create_items_table(layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.accept)
        
        close_btn = button_box.button(QDialogButtonBox.StandardButton.Close)
        close_btn.setText("✅ Done")
        close_btn.setProperty("style", "success")
        
        layout.addWidget(button_box)

    def create_item_form(self, parent_layout):
        """Create item entry form with FBR API integration"""
        form_group = QGroupBox("Add/Edit Item")
        form_layout = QGridLayout(form_group)
        
        # Row 1: Name and HS Code
        form_layout.addWidget(QLabel("Item Name*:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter item name")
        form_layout.addWidget(self.name_edit, 0, 1)
        
        form_layout.addWidget(QLabel("HS Code*:"), 0, 2)
        self.hs_code_combo = QComboBox()
        self.hs_code_combo.setEditable(True)
        self.hs_code_combo.setPlaceholderText("Loading HS codes...")
        self.hs_code_combo.setEnabled(False)
        form_layout.addWidget(self.hs_code_combo, 0, 3)
        
        # Row 2: UoM (read-only, auto-populated) and Category
        form_layout.addWidget(QLabel("Unit of Measurement*:"), 1, 0)
        self.uom_edit = QLineEdit()
        self.uom_edit.setPlaceholderText("Auto-populated from HS code")
        self.uom_edit.setReadOnly(True)
        form_layout.addWidget(self.uom_edit, 1, 1)
        
        form_layout.addWidget(QLabel("Category:"), 1, 2)
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "General", "Products", "Services", "Materials", 
            "Equipment", "Software", "Consumables"
        ])
        form_layout.addWidget(self.category_combo, 1, 3)
        
        # Row 3: Pricing information
        form_layout.addWidget(QLabel("Standard Rate (PKR):"), 2, 0)
        self.standard_rate_edit = QLineEdit()
        self.standard_rate_edit.setPlaceholderText("0.00")
        form_layout.addWidget(self.standard_rate_edit, 2, 1)
        
        form_layout.addWidget(QLabel("Tax Rate (%):"), 2, 2)
        self.tax_rate_edit = QLineEdit()
        self.tax_rate_edit.setPlaceholderText("18.0")
        form_layout.addWidget(self.tax_rate_edit, 2, 3)
        
        # Row 4: Description
        form_layout.addWidget(QLabel("Description:"), 3, 0)
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Optional item description")
        form_layout.addWidget(self.description_edit, 3, 1, 1, 3)
        
        # Row 5: UoM loading indicator
        self.uom_loading_label = QLabel("")
        self.uom_loading_label.setStyleSheet("color: #ffc107; font-style: italic;")
        self.uom_loading_label.setVisible(False)
        form_layout.addWidget(self.uom_loading_label, 4, 0, 1, 4)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.save_item_btn = QPushButton("💾 Save Item")
        self.save_item_btn.setProperty("style", "success")
        self.save_item_btn.clicked.connect(self.save_item)
        button_layout.addWidget(self.save_item_btn)
        
        self.clear_form_btn = QPushButton("🧹 Clear Form")
        self.clear_form_btn.clicked.connect(self.clear_form)
        button_layout.addWidget(self.clear_form_btn)
        
        button_layout.addStretch()
        
        self.edit_mode_label = QLabel("")
        self.edit_mode_label.setStyleSheet("color: #ffc107; font-weight: bold;")
        button_layout.addWidget(self.edit_mode_label)
        
        form_layout.addLayout(button_layout, 5, 0, 1, 4)
        
        parent_layout.addWidget(form_group)
        
        # Store for edit mode
        self.editing_item_id = None

    def create_items_table(self, parent_layout):
        """Create items display table"""
        table_group = QGroupBox("Company Items")
        table_layout = QVBoxLayout(table_group)
        
        # Table toolbar
        toolbar_layout = QHBoxLayout()
        
        self.edit_selected_btn = QPushButton("✏️ Edit Selected")
        self.edit_selected_btn.clicked.connect(self.edit_selected_item)
        self.edit_selected_btn.setEnabled(False)
        toolbar_layout.addWidget(self.edit_selected_btn)
        
        self.delete_selected_btn = QPushButton("🗑️ Delete Selected")
        self.delete_selected_btn.setProperty("style", "danger")
        self.delete_selected_btn.clicked.connect(self.delete_selected_item)
        self.delete_selected_btn.setEnabled(False)
        toolbar_layout.addWidget(self.delete_selected_btn)
        
        toolbar_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self.load_items)
        toolbar_layout.addWidget(self.refresh_btn)
        
        table_layout.addLayout(toolbar_layout)
        
        # Items table
        self.items_table = QTableWidget()
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.selectionModel().selectionChanged.connect(self.on_selection_changed)
        table_layout.addWidget(self.items_table)
        
        parent_layout.addWidget(table_group)

    def setup_signals(self):
        # When user selects an item from the list -> fetch UoM
        self.hs_code_combo.currentIndexChanged.connect(self.on_hs_selected)
        # When user types -> filter list (does not fetch UoM)
        self.hs_code_combo.lineEdit().textEdited.connect(self.on_hs_search_edited)

    def load_fbr_dropdown_data(self):
        """Load dropdown data from FBR APIs"""
        self.show_loading_state(True, "Loading HS codes from FBR...")
        
        # Get authorization token from parent window or settings
        auth_token = self.get_auth_token()
        
        if not auth_token:
            self.show_loading_state(False, "❌ No authorization token configured")
            self._populate_fallback_hs_codes()
            return
        
        headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Load HS codes
        self.load_hs_codes_thread = FBRAPIThread(
            'hs_codes',
            'https://gw.fbr.gov.pk/pdi/v1/itemdesccode',
            headers
        )
        self.load_hs_codes_thread.data_received.connect(self.on_hs_codes_loaded)
        self.load_hs_codes_thread.error_occurred.connect(self.on_api_error)
        self.load_hs_codes_thread.start()

    def get_auth_token(self):
        """Get authorization token from parent window or settings"""
        # Try to get from parent window (main window)
        if hasattr(self.parent_window, 'auth_token_edit'):
            token = self.parent_window.auth_token_edit.text().strip()
            if token:
                return token
        
        # Try to get from database settings
        if self.db_manager:
            try:
                session = self.db_manager.get_session()
                from fbr_core.models import FBRSettings
                
                settings = session.query(FBRSettings).filter_by(company_id=self.company_id).first()
                if settings and settings.pral_authorization_token:
                    return settings.pral_authorization_token.strip()
            except Exception as e:
                print(f"Error getting auth token from database: {e}")
        
        # Fallback token (should be configured in production)
        return "e8882e63-ca03-3174-8e19-f9e609f2a418"

    def on_hs_selected(self, idx: int):
        """Combo selection changed -> get UoM for that HS."""
        if idx < 0 or idx >= self.hs_code_combo.count():
            self.uom_edit.clear()
            self.uom_edit.setPlaceholderText("Select an HS Code first")
            return
        payload = self.hs_code_combo.itemData(idx)
        code = (payload or {}).get("code")
        if not code:
            # fallback: parse from text
            text = self.hs_code_combo.itemText(idx)
            code = text.split(" - ")[0].strip() if " - " in text else text.strip()
        if code:
            self.on_uom_request_for(code)

    def on_uom_request_for(self, hs_code: str):
        """Starts the thread to fetch and set UoM; extracted for reuse."""
        self.uom_edit.clear()
        self.uom_edit.setPlaceholderText("Loading UoM...")
        self.uom_loading_label.setText("🔄 Loading UoM for selected HS code...")
        self.uom_loading_label.setVisible(True)

        auth_token = self.get_auth_token()
        if not auth_token:
            self.uom_loading_label.setText("❌ No authorization token for UoM API")
            return

        headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        params = {'hs_code': hs_code, 'annexure_id': 3}

        if hasattr(self, 'load_uom_thread') and self.load_uom_thread.isRunning():
            self.load_uom_thread.quit(); self.load_uom_thread.wait()

        self.load_uom_thread = FBRAPIThread('uom', 'https://gw.fbr.gov.pk/pdi/v2/HS_UOM', headers, params)
        self.load_uom_thread.data_received.connect(self.on_uom_loaded)
        self.load_uom_thread.error_occurred.connect(self.on_api_error)
        self.load_uom_thread.start()

    def on_hs_codes_loaded(self, endpoint_key, data):
        """Handle HS codes data loaded from API"""
        try:
            if endpoint_key == 'hs_codes' and data:
                # build and cache
                self._hs_all = []
                for item in data:
                    hs_code = (item.get('hS_CODE') or item.get('HS_CODE') or item.get('hs_code') or '').strip()
                    description = (item.get('description') or '').strip()
                    if not hs_code:
                        continue
                    self._hs_all.append({
                        "code": hs_code,
                        "desc": description,
                        "label": f"{hs_code} - {description}",
                    })

                self.hs_code_combo.setEnabled(True)
                self.hs_code_combo.lineEdit().clear()
                self._rebuild_hs_combo(self._hs_all, preserve_text=False)
                self.hs_code_combo.lineEdit().setPlaceholderText("Type HS code or keyword...")
                self.show_loading_state(False, "✅ HS codes loaded successfully")
                QTimer.singleShot(3000, lambda: self.show_loading_state(False, ""))

            else:
                self.show_loading_state(False, "⚠️ No HS codes received")
                self._populate_fallback_hs_codes()

        except Exception as e:
            self.show_loading_state(False, f"❌ Error processing HS codes: {e}")
            self._populate_fallback_hs_codes()


    def on_api_error(self, endpoint_key, error_message):
        """Handle API errors"""
        if endpoint_key == 'hs_codes':
            self.show_loading_state(False, f"❌ Failed to load HS codes: {error_message}")
            self._populate_fallback_hs_codes()
        elif endpoint_key == 'uom':
            self.uom_loading_label.setText(f"❌ Failed to load UoM: {error_message}")
            self.uom_loading_label.setVisible(True)
            # Hide error after 5 seconds
            QTimer.singleShot(5000, lambda: self.uom_loading_label.setVisible(False))

    def _populate_fallback_hs_codes(self):
        """Populate with fallback HS codes when API fails"""
        fallback_hs_codes = [
            "0101.2100 - Live horses",
            "1001.1100 - Durum wheat seed",
            "1001.1900 - Other durum wheat",
            "8471.3000 - Portable digital automatic data processing machines",
            "8542.3100 - Processors and controllers",
            "9999.0000 - General/Other"
        ]
        
        self._hs_all = []
        for s in fallback_hs_codes:
            code = s.split(" - ")[0].strip()
            desc = s.split(" - ", 1)[1].strip() if " - " in s else ""
            self._hs_all.append({"code": code, "desc": desc, "label": s})
        self.hs_code_combo.setEnabled(True)
        self._rebuild_hs_combo(self._hs_all, preserve_text=False)
        self.hs_code_combo.lineEdit().setPlaceholderText("Type HS code or keyword…")

    _hs_all: list = []

    def _rebuild_hs_combo(self, items: list, preserve_text: bool = True):
        """Rebuild the HS combo with the given items (each an object with 'label' and 'code')."""
        # preserve whatever the user has typed
        typed = self.hs_code_combo.lineEdit().text() if preserve_text else ""
        cursor_pos = self.hs_code_combo.lineEdit().cursorPosition() if preserve_text else 0

        # rebuild without firing signals
        self.hs_code_combo.blockSignals(True)
        self.hs_code_combo.clear()
        for obj in items:
            self.hs_code_combo.addItem(obj["label"], obj)
        self.hs_code_combo.blockSignals(False)

        if preserve_text:
            self.hs_code_combo.lineEdit().setText(typed)
            self.hs_code_combo.lineEdit().setCursorPosition(cursor_pos)

    def _filter_hs_items(self, query: str) -> list:
        """Digit query -> startswith(code); text query -> contains(label/desc)."""
        if not query:
            return self._hs_all

        q = query.strip()
        if q.isdigit():
            return [o for o in self._hs_all if o["code"].startswith(q)]
        ql = q.lower()
        return [o for o in self._hs_all
                if (ql in o["label"].lower()) or (ql in (o["desc"] or "").lower())]

    def on_hs_search_edited(self, text: str):
        """User typing in the HS box -> filter choices in-place."""
        filtered = self._filter_hs_items(text)
        self._rebuild_hs_combo(filtered, preserve_text=True)

    def on_uom_loaded(self, endpoint_key, data):
        """Handle UoM data loaded from API"""
        try:
            if endpoint_key == 'uom' and data:
                # Get the first UoM (should be the primary one for this HS code)
                if len(data) > 0:
                    uom_description = data[0].get('description', '')
                    self.uom_edit.setText(uom_description)
                    self.uom_edit.setPlaceholderText("Auto-populated from HS code")
                    self.uom_loading_label.setText("✅ UoM loaded successfully")
                    
                    # Hide success message after 2 seconds
                    QTimer.singleShot(2000, lambda: self.uom_loading_label.setVisible(False))
                else:
                    self.uom_loading_label.setText("⚠️ No UoM found for this HS code")
                    self.uom_edit.setPlaceholderText("No UoM available")
                    
                    # Hide warning after 3 seconds
                    QTimer.singleShot(3000, lambda: self.uom_loading_label.setVisible(False))
            else:
                self.uom_loading_label.setText("⚠️ No UoM data received")
                # Hide warning after 3 seconds
                QTimer.singleShot(3000, lambda: self.uom_loading_label.setVisible(False))
                
        except Exception as e:
            self.uom_loading_label.setText(f"❌ Error processing UoM: {e}")
            # Hide error after 5 seconds
            QTimer.singleShot(5000, lambda: self.uom_loading_label.setVisible(False))

    def show_loading_state(self, is_loading, message=""):
        """Show or hide loading state"""
        self.loading_label.setVisible(is_loading)
        self.loading_progress.setVisible(is_loading)
        
        if message:
            self.loading_label.setText(message)

    def load_items(self):
        """Load items for the current company"""
        try:
            session = self.db_manager.get_session()
            items = (
                session.query(Item)
                .filter_by(company_id=self.company_id)
                .order_by(Item.created_at.desc())
                .all()
            )
            
            self.items_table.setRowCount(len(items))
            self.items_table.setColumnCount(7)
            self.items_table.setHorizontalHeaderLabels([
                "ID", "Name", "HS Code", "UoM", "Category", "Rate", "Created"
            ])
            
            for row, item in enumerate(items):
                self.items_table.setItem(row, 0, QTableWidgetItem(str(item.id)))
                self.items_table.setItem(row, 1, QTableWidgetItem(item.name or ""))
                self.items_table.setItem(row, 2, QTableWidgetItem(item.hs_code or ""))
                self.items_table.setItem(row, 3, QTableWidgetItem(item.uom or ""))
                self.items_table.setItem(row, 4, QTableWidgetItem(item.category or ""))
                self.items_table.setItem(row, 5, QTableWidgetItem(
                    f"{item.standard_rate:.2f}" if item.standard_rate else "0.00"
                ))
                self.items_table.setItem(row, 6, QTableWidgetItem(
                    item.created_at.strftime("%Y-%m-%d %H:%M") if item.created_at else ""
                ))
            
            # Resize columns
            self.items_table.resizeColumnsToContents()
            header = self.items_table.horizontalHeader()
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name column
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load items: {str(e)}")

    def save_item(self):
        """Save item to database with validation"""
        # Validate form
        name = self.name_edit.text().strip()
        hs_code_text = self.hs_code_combo.currentText().strip()
        uom = self.uom_edit.text().strip()
        category = self.category_combo.currentText().strip()
        description = self.description_edit.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Item name is required!")
            self.name_edit.setFocus()
            return
            
        if not hs_code_text:
            QMessageBox.warning(self, "Validation Error", "HS Code is required!")
            self.hs_code_combo.setFocus()
            return
            
        if not uom:
            QMessageBox.warning(self, "Validation Error", "Unit of Measurement is required! Please select a valid HS code first.")
            self.hs_code_combo.setFocus()
            return
        
        # Extract HS code from formatted text
        hs_code = self.formatter.extract_hs_code_from_dropdown_text(hs_code_text)
        if not hs_code:
            QMessageBox.warning(self, "Validation Error", "Invalid HS Code format!")
            return
        
        # Validate numeric fields
        try:
            standard_rate = float(self.standard_rate_edit.text()) if self.standard_rate_edit.text().strip() else None
            tax_rate = float(self.tax_rate_edit.text()) if self.tax_rate_edit.text().strip() else 18.0
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Please enter valid numeric values for rates!")
            return
        
        try:
            session = self.db_manager.get_session()
            
            if self.editing_item_id:
                # Edit existing item
                item = session.query(Item).filter_by(id=self.editing_item_id).first()
                if not item:
                    QMessageBox.warning(self, "Error", "Item not found for editing!")
                    return
                    
                action = "updated"
            else:
                # Create new item
                item = Item(company_id=self.company_id)
                session.add(item)
                action = "created"
            
            # Update item fields
            item.name = name
            item.hs_code = hs_code
            item.uom = uom
            item.category = category
            item.description = description
            item.standard_rate = standard_rate
            item.tax_rate = tax_rate
            item.updated_at = datetime.now()
            
            if not self.editing_item_id:
                item.created_at = datetime.now()
            
            session.commit()
            
            QMessageBox.information(
                self, "Success", 
                f"Item '{name}' {action} successfully!"
            )
            
            self.clear_form()
            self.load_items()
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to save item: {str(e)}")

    def clear_form(self):
        """Clear the form fields"""
        self.name_edit.clear()
        self.hs_code_combo.setCurrentIndex(-1)
        self.hs_code_combo.clearEditText()
        self.uom_edit.clear()
        self.uom_edit.setPlaceholderText("Auto-populated from HS code")
        self.category_combo.setCurrentIndex(0)
        self.description_edit.clear()
        self.standard_rate_edit.clear()
        self.tax_rate_edit.clear()
        
        self.editing_item_id = None
        self.edit_mode_label.setText("")
        self.save_item_btn.setText("💾 Save Item")
        self.uom_loading_label.setVisible(False)

    def on_selection_changed(self):
        """Handle table selection changes"""
        has_selection = len(self.items_table.selectedItems()) > 0
        self.edit_selected_btn.setEnabled(has_selection)
        self.delete_selected_btn.setEnabled(has_selection)

    def edit_selected_item(self):
        """Edit the selected item"""
        current_row = self.items_table.currentRow()
        if current_row < 0:
            return
            
        try:
            item_id = int(self.items_table.item(current_row, 0).text())
            
            session = self.db_manager.get_session()
            item = session.query(Item).filter_by(id=item_id).first()
            
            if not item:
                QMessageBox.warning(self, "Error", "Item not found!")
                return
            
            # Populate form with item data
            self.name_edit.setText(item.name or "")
            
            # Set HS code - try to find matching formatted text
            hs_code_text = item.hs_code or ""
            combo_index = -1
            for i in range(self.hs_code_combo.count()):
                combo_text = self.hs_code_combo.itemText(i)
                if combo_text.startswith(hs_code_text + " - ") or combo_text == hs_code_text:
                    combo_index = i
                    break
            
            if combo_index >= 0:
                self.hs_code_combo.setCurrentIndex(combo_index)
            else:
                self.hs_code_combo.setCurrentText(hs_code_text)
            
            # Set other fields
            self.uom_edit.setText(item.uom or "")
            
            category_index = self.category_combo.findText(item.category or "General")
            if category_index >= 0:
                self.category_combo.setCurrentIndex(category_index)
            
            self.description_edit.setText(item.description or "")
            self.standard_rate_edit.setText(str(item.standard_rate) if item.standard_rate else "")
            self.tax_rate_edit.setText(str(item.tax_rate) if item.tax_rate else "")
            
            # Set edit mode
            self.editing_item_id = item_id
            self.edit_mode_label.setText(f"Editing: {item.name}")
            self.save_item_btn.setText("💾 Update Item")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load item for editing: {str(e)}")

    def delete_selected_item(self):
        """Delete the selected item"""
        current_row = self.items_table.currentRow()
        if current_row < 0:
            return
            
        try:
            item_id = int(self.items_table.item(current_row, 0).text())
            item_name = self.items_table.item(current_row, 1).text()
            
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Are you sure you want to delete the item '{item_name}'?\n\n"
                "This action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                session = self.db_manager.get_session()
                item = session.query(Item).filter_by(id=item_id).first()
                
                if item:
                    session.delete(item)
                    session.commit()
                    
                    QMessageBox.information(
                        self, "Success", 
                        f"Item '{item_name}' deleted successfully!"
                    )
                    
                    self.load_items()
                    
                    # Clear form if we were editing this item
                    if self.editing_item_id == item_id:
                        self.clear_form()
                else:
                    QMessageBox.warning(self, "Error", "Item not found!")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete item: {str(e)}")

    def closeEvent(self, event):
        """Clean up when dialog is closed"""
        # Stop any running threads
        if hasattr(self, 'load_hs_codes_thread') and self.load_hs_codes_thread.isRunning():
            self.load_hs_codes_thread.quit()
            self.load_hs_codes_thread.wait()
        
        if hasattr(self, 'load_uom_thread') and self.load_uom_thread.isRunning():
            self.load_uom_thread.quit()
            self.load_uom_thread.wait()
        
        event.accept()


class ItemSelectionDialog(QDialog):
    """Dialog for selecting items from company inventory"""
    
    item_selected = pyqtSignal(dict)  # Emits selected item data
    
    def __init__(self, db_manager, company_id, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.company_id = company_id
        
        self.setWindowTitle("Select Item")
        self.setModal(True)
        self.resize(800, 500)
        
        self.setStyleSheet(parent.styleSheet() if parent else "")
        
        self.setup_ui()
        self.load_items()

    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Search
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type to search items...")
        self.search_edit.textChanged.connect(self.filter_items)
        search_layout.addWidget(self.search_edit)
        
        layout.addLayout(search_layout)
        
        # Items table
        self.items_table = QTableWidget()
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.doubleClicked.connect(self.select_item)
        layout.addWidget(self.items_table)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_new_btn = QPushButton("➕ Add New Item")
        add_new_btn.clicked.connect(self.add_new_item)
        button_layout.addWidget(add_new_btn)
        
        button_layout.addStretch()
        
        select_btn = QPushButton("✅ Select")
        select_btn.setProperty("style", "success")
        select_btn.clicked.connect(self.select_item)
        button_layout.addWidget(select_btn)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)

    def load_items(self):
        """Load items for selection"""
        try:
            session = self.db_manager.get_session()
            self.items = (
                session.query(Item)
                .filter_by(company_id=self.company_id)
                .order_by(Item.name)
                .all()
            )
            
            self.populate_table(self.items)
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load items: {str(e)}")

    def populate_table(self, items):
        """Populate table with items"""
        self.items_table.setRowCount(len(items))
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels([
            "ID", "Name", "HS Code", "UoM", "Rate"
        ])
        
        for row, item in enumerate(items):
            self.items_table.setItem(row, 0, QTableWidgetItem(str(item.id)))
            self.items_table.setItem(row, 1, QTableWidgetItem(item.name or ""))
            self.items_table.setItem(row, 2, QTableWidgetItem(item.hs_code or ""))
            self.items_table.setItem(row, 3, QTableWidgetItem(item.uom or ""))
            self.items_table.setItem(row, 4, QTableWidgetItem(
                f"{item.standard_rate:.2f}" if item.standard_rate else "0.00"
            ))
        
        self.items_table.resizeColumnsToContents()

    def filter_items(self, text):
        """Filter items based on search text"""
        if not text:
            self.populate_table(self.items)
            return
            
        filtered_items = [
            item for item in self.items
            if text.lower() in (item.name or "").lower() or
               text.lower() in (item.hs_code or "").lower() or
               text.lower() in (item.category or "").lower()
        ]
        
        self.populate_table(filtered_items)

    def select_item(self):
        """Select the current item"""
        current_row = self.items_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Information", "Please select an item")
            return
            
        try:
            item_id = int(self.items_table.item(current_row, 0).text())
            item_name = self.items_table.item(current_row, 1).text()
            hs_code = self.items_table.item(current_row, 2).text()
            uom = self.items_table.item(current_row, 3).text()
            rate = self.items_table.item(current_row, 4).text()
            
            item_data = {
                'id': item_id,
                'name': item_name,
                'hs_code': hs_code,
                'uom': uom,
                'standard_rate': float(rate) if rate != "0.00" else 0.0
            }
            
            self.item_selected.emit(item_data)
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to select item: {str(e)}")

    def add_new_item(self):
        """Add a new item"""
        dialog = ItemManagementDialog(self.db_manager, self.company_id, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_items()  # Refresh the list


# Test the dialogs
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Mock database manager for testing
    class MockDBManager:
        def get_session(self):
            return None
    
    dialog = ItemManagementDialog(MockDBManager(), "TEST_COMPANY", None)
    result = dialog.exec()
    
    sys.exit(app.exec())