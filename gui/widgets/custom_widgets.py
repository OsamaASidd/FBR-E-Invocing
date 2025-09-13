# gui/widgets/custom_widgets.py
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QLineEdit, QComboBox, QTextEdit, QFrame, QApplication,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QColor, QPalette, QPainter, QBrush, QPen


class StatusCard(QFrame):
    """Custom status card widget for dashboard"""
    
    clicked = pyqtSignal()
    
    def __init__(self, title, value, icon, color="#5aa2ff", clickable=True, parent=None):
        super().__init__(parent)
        self.title = title
        self.value = value
        self.icon = icon
        self.color = color
        self.clickable = clickable
        self.is_hovered = False
        
        self.setFixedHeight(120)
        self.setMinimumWidth(200)
        self.setCursor(Qt.CursorShape.PointingHandCursor if clickable else Qt.CursorShape.ArrowCursor)
        
        self.setStyleSheet(f"""
            StatusCard {{
                background-color: #1b2028;
                border-left: 4px solid {color};
                border-radius: 8px;
                margin: 5px;
            }}
            StatusCard:hover {{
                background-color: #243447;
            }}
        """)
        
        self.setup_ui()

    def setup_ui(self):
        """Setup the card UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # Header with icon and title
        header_layout = QHBoxLayout()
        
        # Icon
        icon_label = QLabel(self.icon)
        icon_label.setStyleSheet(f"color: {self.color}; font-size: 24px; font-weight: bold;")
        header_layout.addWidget(icon_label)
        
        header_layout.addStretch()
        
        # Title
        title_label = QLabel(self.title)
        title_label.setStyleSheet("color: #cccccc; font-size: 12px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        header_layout.addWidget(title_label)
        
        layout.addLayout(header_layout)
        
        # Value
        self.value_label = QLabel(str(self.value))
        self.value_label.setStyleSheet(f"""
            color: {self.color}; 
            font-size: 32px; 
            font-weight: bold;
            margin: 10px 0;
        """)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)
        
        layout.addStretch()

    def update_value(self, new_value):
        """Update the card value with animation"""
        self.value = new_value
        self.value_label.setText(str(new_value))
        
        # Simple flash animation
        self.animate_update()

    def animate_update(self):
        """Animate value update"""
        # Flash effect
        original_style = self.value_label.styleSheet()
        flash_style = original_style.replace(self.color, "#ffffff")
        
        self.value_label.setStyleSheet(flash_style)
        QTimer.singleShot(150, lambda: self.value_label.setStyleSheet(original_style))

    def mousePressEvent(self, event):
        """Handle mouse press"""
        if self.clickable and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class SearchableComboBox(QComboBox):
    """Combobox with search functionality"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        
        self.original_items = []
        self.completer_items = []
        
        self.lineEdit().textChanged.connect(self.filter_items)
        
    def add_items(self, items):
        """Add items to the combo box"""
        self.original_items = items.copy()
        self.completer_items = items.copy()
        self.clear()
        self.addItems(items)
    
    def filter_items(self, text):
        """Filter items based on text input"""
        if not text:
            # Show all items if no filter text
            self.clear()
            self.addItems(self.original_items)
            return
        
        # Filter items that contain the text (case insensitive)
        filtered_items = [
            item for item in self.original_items
            if text.lower() in item.lower()
        ]
        
        self.clear()
        self.addItems(filtered_items)
        
        # Show dropdown if there are filtered results
        if filtered_items:
            self.showPopup()

    def get_selected_value(self):
        """Get the currently selected/entered value"""
        return self.currentText().strip()


class LoadingOverlay(QFrame):
    """Loading overlay widget"""
    
    def __init__(self, parent=None, message="Loading..."):
        super().__init__(parent)
        self.message = message
        
        self.setStyleSheet("""
            LoadingOverlay {
                background-color: rgba(15, 17, 21, 200);
                border-radius: 8px;
            }
        """)
        
        self.setup_ui()
        self.hide()

    def setup_ui(self):
        """Setup the overlay UI"""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #5aa2ff;
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
        layout.addWidget(self.progress_bar)
        
        # Message
        self.message_label = QLabel(self.message)
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.setStyleSheet("""
            color: #eaeef6;
            font-size: 14px;
            font-weight: bold;
            margin: 10px;
        """)
        layout.addWidget(self.message_label)

    def show_loading(self, message=None):
        """Show the loading overlay"""
        if message:
            self.message_label.setText(message)
        
        # Resize to parent if parent exists
        if self.parent():
            self.resize(self.parent().size())
        
        self.show()
        self.raise_()

    def hide_loading(self):
        """Hide the loading overlay"""
        self.hide()

    def update_message(self, message):
        """Update the loading message"""
        self.message_label.setText(message)


class CollapsibleSection(QWidget):
    """Collapsible section widget"""
    
    def __init__(self, title="Section", parent=None):
        super().__init__(parent)
        self.title = title
        self.is_expanded = True
        
        self.setup_ui()

    def setup_ui(self):
        """Setup the collapsible section UI"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Header
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet("""
            QFrame {
                background-color: #2c3b52;
                border-radius: 6px;
                padding: 5px;
            }
            QFrame:hover {
                background-color: #334561;
            }
        """)
        
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(10, 5, 10, 5)
        
        # Toggle button
        self.toggle_button = QPushButton("▼")
        self.toggle_button.setFixedSize(20, 20)
        self.toggle_button.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                color: #eaeef6;
                font-weight: bold;
            }
        """)
        self.toggle_button.clicked.connect(self.toggle_section)
        header_layout.addWidget(self.toggle_button)
        
        # Title
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            color: #eaeef6;
            font-weight: bold;
            font-size: 14px;
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.main_layout.addWidget(self.header_frame)
        
        # Content area
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("""
            QFrame {
                background-color: #1b2028;
                border-radius: 6px;
                margin-top: 2px;
            }
        """)
        
        self.content_layout = QVBoxLayout(self.content_frame)
        self.main_layout.addWidget(self.content_frame)

    def add_content_widget(self, widget):
        """Add a widget to the content area"""
        self.content_layout.addWidget(widget)

    def add_content_layout(self, layout):
        """Add a layout to the content area"""
        self.content_layout.addLayout(layout)

    def toggle_section(self):
        """Toggle the section expanded/collapsed state"""
        self.is_expanded = not self.is_expanded
        
        if self.is_expanded:
            self.toggle_button.setText("▼")
            self.content_frame.show()
        else:
            self.toggle_button.setText("▶")
            self.content_frame.hide()


class NotificationBanner(QFrame):
    """Notification banner widget"""
    
    def __init__(self, message, notification_type="info", auto_hide=True, parent=None):
        super().__init__(parent)
        self.message = message
        self.notification_type = notification_type
        self.auto_hide = auto_hide
        
        self.setup_ui()
        
        if auto_hide:
            QTimer.singleShot(5000, self.hide_notification)

    def setup_ui(self):
        """Setup the notification UI"""
        self.setFixedHeight(50)
        
        # Color scheme based on type
        colors = {
            "info": {"bg": "#17a2b8", "text": "#ffffff"},
            "success": {"bg": "#28a745", "text": "#ffffff"}, 
            "warning": {"bg": "#ffc107", "text": "#000000"},
            "error": {"bg": "#dc3545", "text": "#ffffff"}
        }
        
        color_scheme = colors.get(self.notification_type, colors["info"])
        
        self.setStyleSheet(f"""
            NotificationBanner {{
                background-color: {color_scheme["bg"]};
                border-radius: 6px;
                margin: 5px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        
        # Icon based on type
        icons = {
            "info": "ℹ️",
            "success": "✅", 
            "warning": "⚠️",
            "error": "❌"
        }
        
        icon_label = QLabel(icons.get(self.notification_type, "ℹ️"))
        icon_label.setStyleSheet(f"color: {color_scheme['text']}; font-size: 16px;")
        layout.addWidget(icon_label)
        
        # Message
        message_label = QLabel(self.message)
        message_label.setStyleSheet(f"""
            color: {color_scheme["text"]};
            font-weight: bold;
            font-size: 14px;
        """)
        layout.addWidget(message_label)
        
        layout.addStretch()
        
        # Close button
        if not self.auto_hide:
            close_button = QPushButton("✕")
            close_button.setFixedSize(25, 25)
            close_button.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    border: none;
                    color: {color_scheme["text"]};
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 50);
                    border-radius: 12px;
                }}
            """)
            close_button.clicked.connect(self.hide_notification)
            layout.addWidget(close_button)

    def hide_notification(self):
        """Hide the notification with animation"""
        self.hide()

    @staticmethod
    def show_info(parent, message, auto_hide=True):
        """Show info notification"""
        return NotificationBanner(message, "info", auto_hide, parent)
    
    @staticmethod
    def show_success(parent, message, auto_hide=True):
        """Show success notification"""
        return NotificationBanner(message, "success", auto_hide, parent)
    
    @staticmethod
    def show_warning(parent, message, auto_hide=True):
        """Show warning notification"""
        return NotificationBanner(message, "warning", auto_hide, parent)
    
    @staticmethod
    def show_error(parent, message, auto_hide=True):
        """Show error notification"""
        return NotificationBanner(message, "error", auto_hide, parent)


class DataTableWidget(QTableWidget):
    """Enhanced table widget with additional functionality"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Apply styling
        self.setStyleSheet("""
            QTableWidget {
                background-color: #1b2028;
                alternate-background-color: #243447;
                gridline-color: #2c3b52;
                color: #eaeef6;
                border: 1px solid #2c3b52;
                border-radius: 6px;
            }
            QHeaderView::section {
                background-color: #2c3b52;
                color: #ffffff;
                border: 1px solid #334561;
                padding: 8px;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2c3b52;
            }
            QTableWidget::item:selected {
                background-color: #5aa2ff;
                color: #0f1115;
            }
        """)
        
        # Set properties
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        
        # Auto-resize columns
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

    def setup_columns(self, headers):
        """Setup table columns"""
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)

    def add_data_row(self, data):
        """Add a data row to the table"""
        row = self.rowCount()
        self.insertRow(row)
        
        for col, value in enumerate(data):
            if col < self.columnCount():
                item = QTableWidgetItem(str(value) if value is not None else "")
                self.setItem(row, col, item)

    def clear_data(self):
        """Clear all data while keeping headers"""
        self.setRowCount(0)

    def export_to_csv(self, filename):
        """Export table data to CSV"""
        import csv
        
        with open(filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            # Write headers
            headers = []
            for col in range(self.columnCount()):
                headers.append(self.horizontalHeaderItem(col).text())
            writer.writerow(headers)
            
            # Write data
            for row in range(self.rowCount()):
                row_data = []
                for col in range(self.columnCount()):
                    item = self.item(row, col)
                    row_data.append(item.text() if item else "")
                writer.writerow(row_data)

    def get_selected_row_data(self):
        """Get data from the selected row"""
        current_row = self.currentRow()
        if current_row >= 0:
            row_data = []
            for col in range(self.columnCount()):
                item = self.item(current_row, col)
                row_data.append(item.text() if item else "")
            return row_data
        return None


class FormFieldWidget(QWidget):
    """Custom form field widget with label and input"""
    
    def __init__(self, label_text, widget_type="line_edit", required=False, parent=None):
        super().__init__(parent)
        self.label_text = label_text
        self.widget_type = widget_type
        self.required = required
        
        self.setup_ui()

    def setup_ui(self):
        """Setup the form field UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 5)
        layout.setSpacing(5)
        
        # Label
        label_text = self.label_text
        if self.required:
            label_text += " *"
            
        self.label = QLabel(label_text)
        self.label.setStyleSheet("""
            color: #eaeef6;
            font-weight: bold;
            font-size: 13px;
        """ + ("color: #ffc107;" if self.required else ""))
        layout.addWidget(self.label)
        
        # Input widget
        if self.widget_type == "line_edit":
            self.input_widget = QLineEdit()
        elif self.widget_type == "combo_box":
            self.input_widget = QComboBox()
        elif self.widget_type == "text_edit":
            self.input_widget = QTextEdit()
            self.input_widget.setMaximumHeight(80)
        elif self.widget_type == "searchable_combo":
            self.input_widget = SearchableComboBox()
        else:
            self.input_widget = QLineEdit()
        
        # Apply styling
        self.input_widget.setStyleSheet("""
            QLineEdit, QComboBox, QTextEdit {
                background: #0f141c;
                color: #eaeef6;
                border: 1px solid #334561;
                border-radius: 6px;
                padding: 8px 12px;
                min-height: 28px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 1px solid #5aa2ff;
                box-shadow: 0 0 0 2px rgba(90,162,255,0.18);
            }
        """)
        
        layout.addWidget(self.input_widget)

    def set_placeholder(self, text):
        """Set placeholder text"""
        if hasattr(self.input_widget, 'setPlaceholderText'):
            self.input_widget.setPlaceholderText(text)

    def get_value(self):
        """Get the input value"""
        if isinstance(self.input_widget, QLineEdit):
            return self.input_widget.text().strip()
        elif isinstance(self.input_widget, QComboBox):
            return self.input_widget.currentText().strip()
        elif isinstance(self.input_widget, QTextEdit):
            return self.input_widget.toPlainText().strip()
        elif isinstance(self.input_widget, SearchableComboBox):
            return self.input_widget.get_selected_value()
        return ""

    def set_value(self, value):
        """Set the input value"""
        if isinstance(self.input_widget, QLineEdit):
            self.input_widget.setText(str(value))
        elif isinstance(self.input_widget, QComboBox):
            index = self.input_widget.findText(str(value))
            if index >= 0:
                self.input_widget.setCurrentIndex(index)
        elif isinstance(self.input_widget, QTextEdit):
            self.input_widget.setText(str(value))
        elif isinstance(self.input_widget, SearchableComboBox):
            self.input_widget.setCurrentText(str(value))

    def is_valid(self):
        """Check if the field is valid"""
        if self.required:
            value = self.get_value()
            return bool(value)
        return True

    def show_error(self, message=""):
        """Show error state"""
        self.input_widget.setStyleSheet("""
            QLineEdit, QComboBox, QTextEdit {
                background: #0f141c;
                color: #eaeef6;
                border: 2px solid #dc3545;
                border-radius: 6px;
                padding: 8px 12px;
                min-height: 28px;
            }
        """)
        
        if message:
            self.label.setText(f"{self.label_text}{'*' if self.required else ''} - {message}")
            self.label.setStyleSheet(self.label.styleSheet() + "color: #dc3545;")

    def clear_error(self):
        """Clear error state"""
        self.input_widget.setStyleSheet("""
            QLineEdit, QComboBox, QTextEdit {
                background: #0f141c;
                color: #eaeef6;
                border: 1px solid #334561;
                border-radius: 6px;
                padding: 8px 12px;
                min-height: 28px;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 1px solid #5aa2ff;
                box-shadow: 0 0 0 2px rgba(90,162,255,0.18);
            }
        """)
        
        label_text = self.label_text
        if self.required:
            label_text += " *"
        self.label.setText(label_text)
        self.label.setStyleSheet("""
            color: #eaeef6;
            font-weight: bold;
            font-size: 13px;
        """ + ("color: #ffc107;" if self.required else ""))


# Test the custom widgets
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Test window
    window = QWidget()
    window.setStyleSheet("QWidget { background-color: #0f1115; }")
    window.resize(800, 600)
    
    layout = QVBoxLayout(window)
    
    # Test status cards
    cards_layout = QHBoxLayout()
    
    card1 = StatusCard("Total Sales", "PKR 150,000", "💰", "#28a745")
    card1.clicked.connect(lambda: print("Sales card clicked"))
    cards_layout.addWidget(card1)
    
    card2 = StatusCard("Pending Items", "5", "⏳", "#ffc107")
    cards_layout.addWidget(card2)
    
    card3 = StatusCard("Successful", "15", "✅", "#17a2b8")
    cards_layout.addWidget(card3)
    
    layout.addLayout(cards_layout)
    
    # Test collapsible section
    section = CollapsibleSection("Form Fields")
    
    # Test form fields
    name_field = FormFieldWidget("Company Name", "line_edit", required=True)
    name_field.set_placeholder("Enter company name")
    section.add_content_widget(name_field)
    
    type_field = FormFieldWidget("Business Type", "combo_box")
    type_field.input_widget.addItems(["Services", "Manufacturing", "Trading"])
    section.add_content_widget(type_field)
    
    desc_field = FormFieldWidget("Description", "text_edit")
    desc_field.set_placeholder("Enter description...")
    section.add_content_widget(desc_field)
    
    layout.addWidget(section)
    
    # Test notification
    notification = NotificationBanner.show_success(window, "This is a test success message!")
    layout.addWidget(notification)
    
    # Test table
    table = DataTableWidget()
    table.setup_columns(["ID", "Name", "Type", "Status"])
    table.add_data_row([1, "Test Item", "Product", "Active"])
    table.add_data_row([2, "Another Item", "Service", "Inactive"])
    layout.addWidget(table)
    
    window.show()
    sys.exit(app.exec())