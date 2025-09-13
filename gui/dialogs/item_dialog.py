# gui/dialogs/item_dialog.py
import sys
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QTextEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QGroupBox, QMessageBox, QDialogButtonBox,
    QHeaderView, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from fbr_core.models import Item


class ItemManagementDialog(QDialog):
    """Dialog for managing company-specific items"""
    
    def __init__(self, db_manager, company_id, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.company_id = company_id
        
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
        self.load_items()

    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Item Management")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #5aa2ff; margin: 10px 0;")
        layout.addWidget(title_label)
        
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
        """Create item entry form"""
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
        self.hs_code_combo.addItems([
            "0101.2100 - Live horses",
            "1001.1100 - Durum wheat seed",
            "1001.1900 - Other durum wheat",
            "8471.3000 - Portable digital automatic data processing machines",
            "8542.3100 - Processors and controllers",
            "9999.0000 - General/Other"
        ])
        form_layout.addWidget(self.hs_code_combo, 0, 3)
        
        # Row 2: UoM and Description
        form_layout.addWidget(QLabel("Unit of Measurement*:"), 1, 0)
        self.uom_combo = QComboBox()
        self.uom_combo.addItems([
            "Numbers, pieces, units",
            "Kg",
            "Meter",
            "Liter",
            "Square meter",
            "Cubic meter",
            "Hours",
            "Days"
        ])
        form_layout.addWidget(self.uom_combo, 1, 1)
        
        # Row 3: Description
        form_layout.addWidget(QLabel("Description:"), 2, 0)
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setPlaceholderText("Optional item description")
        form_layout.addWidget(self.description_edit, 2, 1, 1, 3)
        
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
        
        form_layout.addLayout(button_layout, 3, 0, 1, 4)
        
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
                    item.created_at.strftime("%Y-%m-%d %H:%M") if item.created_at else ""
                ))
            
            # Resize columns
            self.items_table.resizeColumnsToContents()
            header = self.items_table.horizontalHeader()
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name column
            
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Failed to load items: {str(e)}")

    def save_item(self):
        """Save item to database"""
        # Validate form
        name = self.name_edit.text().strip()
        hs_code = self.hs_code_combo.currentText().strip()
        uom = self.uom_combo.currentText().strip()
        description = self.description_edit.toPlainText().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Item name is required!")
            self.name_edit.setFocus()
            return
            
        if not hs_code:
            QMessageBox.warning(self, "Validation Error", "HS Code is required!")
            self.hs_code_combo.setFocus()
            return
            
        if not uom:
            QMessageBox.warning(self, "Validation Error", "Unit of Measurement is required!")
            self.uom_combo.setFocus()
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
            
            # Extract HS code (remove description part if present)
            if ' - ' in hs_code:
                hs_code = hs_code.split(' - ')[0].strip()
            
            # Update item fields
            item.name = name
            item.hs_code = hs_code
            item.uom = uom
            item.created_at = datetime.now() if not self.editing_item_id else item.created_at
            
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
        self.hs_code_combo.setCurrentIndex(0)
        self.uom_combo.setCurrentIndex(0)
        self.description_edit.clear()
        
        self.editing_item_id = None
        self.edit_mode_label.setText("")
        self.save_item_btn.setText("💾 Save Item")

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
            
            # Set HS code
            hs_code_text = item.hs_code or ""
            index = self.hs_code_combo.findText(hs_code_text, Qt.MatchFlag.MatchStartsWith)
            if index >= 0:
                self.hs_code_combo.setCurrentIndex(index)
            else:
                self.hs_code_combo.setCurrentText(hs_code_text)
            
            # Set UoM
            uom_index = self.uom_combo.findText(item.uom or "")
            if uom_index >= 0:
                self.uom_combo.setCurrentIndex(uom_index)
            
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
        self.items_table.setColumnCount(4)
        self.items_table.setHorizontalHeaderLabels([
            "ID", "Name", "HS Code", "UoM"
        ])
        
        for row, item in enumerate(items):
            self.items_table.setItem(row, 0, QTableWidgetItem(str(item.id)))
            self.items_table.setItem(row, 1, QTableWidgetItem(item.name or ""))
            self.items_table.setItem(row, 2, QTableWidgetItem(item.hs_code or ""))
            self.items_table.setItem(row, 3, QTableWidgetItem(item.uom or ""))
        
        self.items_table.resizeColumnsToContents()

    def filter_items(self, text):
        """Filter items based on search text"""
        if not text:
            self.populate_table(self.items)
            return
            
        filtered_items = [
            item for item in self.items
            if text.lower() in (item.name or "").lower() or
               text.lower() in (item.hs_code or "").lower()
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
            
            item_data = {
                'id': item_id,
                'name': item_name,
                'hs_code': hs_code,
                'uom': uom
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