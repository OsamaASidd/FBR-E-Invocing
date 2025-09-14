# gui/main_window.py - Updated Company-Specific Version
import sys
import json
import pandas as pd
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QTableWidget, QTableWidgetItem, QTabWidget, QLabel,
    QLineEdit, QComboBox, QGroupBox, QFormLayout, QMessageBox,
    QProgressBar, QDialog, QDialogButtonBox, QDateEdit, QFileDialog,
    QCheckBox, QFrame, QGridLayout, QHeaderView, QTextEdit, QSpinBox,
    QSplitter, QScrollArea
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QDate, Qt
from PyQt6.QtGui import QFont, QPixmap, QPalette, QColor

# Import dialogs
from gui.dialogs.company_selection_dialog import CompanySelectionDialog
from gui.dialogs.invoice_dialog import FBRInvoiceDialog
from gui.dialogs.item_dialog import ItemManagementDialog
from gui.dialogs.buyer_dialog import BuyerManagementDialog
from gui.dialogs.settings_dialog import FBRSettingsDialog
from gui.dialogs.about_dialog import AboutDialog

# Import core services
from fbr_core.models import DatabaseManager, Invoices, FBRQueue, FBRLogs, Item, Company, Buyer, FBRSettings
from fbr_core.fbr_service import FBRSubmissionService, FBRQueueManager


class FBRProcessingThread(QThread):
    """Background thread for FBR queue processing"""
    
    processing_finished = pyqtSignal(dict)  # results
    progress_updated = pyqtSignal(int, str)  # progress, status
    
    def __init__(self, db_manager, company_id, mode="sandbox", limit=50):
        super().__init__()
        self.db_manager = db_manager
        self.company_id = company_id
        self.mode = mode
        self.limit = limit
    
    def run(self):
        """Process FBR queue in background"""
        try:
            queue_manager = FBRQueueManager(self.db_manager, self.company_id)
            
            self.progress_updated.emit(0, "Starting queue processing...")
            
            result = queue_manager.process_queue(self.limit, self.mode)
            
            self.progress_updated.emit(100, "Queue processing completed")
            self.processing_finished.emit(result)
            
        except Exception as e:
            error_result = {
                "processed_count": 0,
                "failed_count": 0,
                "error": str(e)
            }
            self.processing_finished.emit(error_result)


class MainWindow(QMainWindow):
    """Company-specific main window for FBR E-Invoicing System"""

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.db_manager = None
        self.current_company = None
        self.is_sandbox_mode = True  # Default to sandbox
        self.processing_thread = None
        
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
        self.setWindowTitle(f"FBR E-Invoicing System - {self.current_company['name']}")
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
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #1b2028;
                color: #eaeef6;
                border: 1px solid #2c3b52;
                padding: 12px 20px;
                margin-right: 2px;
                border-radius: 8px 8px 0 0;
                font-weight: 600;
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
            QPushButton:disabled {
                background-color: #333;
                color: #666;
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
                border-radius: 6px;
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
            QComboBox, QLineEdit, QDateEdit, QSpinBox, QTextEdit {
                background: #0f141c;
                color: #eaeef6;
                border: 1px solid #334561;
                border-radius: 6px;
                padding: 6px 10px;
                min-height: 28px;
            }
            QComboBox:focus, QLineEdit:focus, QDateEdit:focus, QSpinBox:focus, QTextEdit:focus {
                border: 1px solid #5aa2ff;
                box-shadow: 0 0 0 2px rgba(90,162,255,0.18);
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

        # Setup menu bar
        self.setup_menu_bar()

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

        # Buyers Management tab
        self.buyers_tab = self.create_buyers_tab()
        tab_widget.addTab(self.buyers_tab, "👥 Buyers")

        # Queue tab
        self.queue_tab = self.create_queue_tab()
        tab_widget.addTab(self.queue_tab, "⚡ FBR Queue")

        # Logs tab
        self.logs_tab = self.create_logs_tab()
        tab_widget.addTab(self.logs_tab, "📋 FBR Logs")

        # Status bar
        self.statusBar().showMessage(f"Connected as: {self.current_company['name']} | Mode: {'Sandbox' if self.is_sandbox_mode else 'Production'}")
        self.statusBar().setStyleSheet("background-color: #2c3b52; color: #eaeef6; padding: 5px;")

    def setup_menu_bar(self):
        """Setup the menu bar"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #2c3b52;
                color: #eaeef6;
                border-bottom: 1px solid #334561;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 8px 12px;
            }
            QMenuBar::item:selected {
                background-color: #5aa2ff;
                color: #0f1115;
            }
            QMenu {
                background-color: #1b2028;
                color: #eaeef6;
                border: 1px solid #2c3b52;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background-color: #5aa2ff;
                color: #0f1115;
            }
        """)
        
        # File menu
        file_menu = menubar.addMenu('&File')
        
        new_invoice_action = file_menu.addAction('📄 &New Invoice')
        new_invoice_action.setShortcut('Ctrl+N')
        new_invoice_action.triggered.connect(self.new_invoice)
        
        file_menu.addSeparator()
        
        export_action = file_menu.addAction('📊 &Export Data')
        export_action.triggered.connect(self.export_data)
        
        import_action = file_menu.addAction('📥 &Import Data')
        import_action.triggered.connect(self.import_data)
        
        file_menu.addSeparator()
        
        switch_company_action = file_menu.addAction('🔄 &Switch Company')
        switch_company_action.triggered.connect(self.switch_company)
        
        exit_action = file_menu.addAction('🚪 E&xit')
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        
        # Tools menu
        tools_menu = menubar.addMenu('&Tools')
        
        settings_action = tools_menu.addAction('⚙️ &Settings')
        settings_action.triggered.connect(self.open_settings)
        
        tools_menu.addSeparator()
        
        process_queue_action = tools_menu.addAction('⚡ &Process FBR Queue')
        process_queue_action.setShortcut('Ctrl+P')
        process_queue_action.triggered.connect(self.process_fbr_queue)
        
        validate_all_action = tools_menu.addAction('✅ &Validate All Invoices')
        validate_all_action.triggered.connect(self.validate_all_invoices)
        
        # Help menu
        help_menu = menubar.addMenu('&Help')
        
        about_action = help_menu.addAction('ℹ️ &About')
        about_action.triggered.connect(self.show_about_dialog)
        
        help_action = help_menu.addAction('❓ &User Guide')
        help_action.triggered.connect(self.show_user_guide)

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
        
        company_details = f"NTN: {self.current_company['ntn_cnic']}"
        if self.current_company.get('business_type'):
            company_details += f" | {self.current_company['business_type']}"
        if self.current_company.get('city'):
            company_details += f" | {self.current_company['city']}"
            
        company_details_label = QLabel(company_details)
        company_details_label.setStyleSheet("color: #cccccc; margin: 2px 5px;")
        
        company_info_layout.addWidget(company_name_label)
        company_info_layout.addWidget(company_details_label)
        
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
        
        # Quick actions
        quick_actions_layout = QVBoxLayout()
        
        new_invoice_btn = QPushButton("📄 New Invoice")
        new_invoice_btn.setProperty("style", "success")
        new_invoice_btn.clicked.connect(self.new_invoice)
        new_invoice_btn.setMaximumHeight(35)
        
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.clicked.connect(self.open_settings)
        settings_btn.setMaximumHeight(35)
        
        quick_actions_layout.addWidget(new_invoice_btn)
        quick_actions_layout.addWidget(settings_btn)
        
        header_layout.addLayout(quick_actions_layout)
        
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
            ("Failed", "0", "#dc3545", "❌"),
            ("Total Items", "0", "#17a2b8", "📦"),
            ("Active Buyers", "0", "#6f42c1", "👥"),
            ("Queue Items", "0", "#fd7e14", "⚡"),
            ("Today's Revenue", "PKR 0", "#20c997", "💰")
        ]
        
        self.stat_labels = {}
        for i, (title, value, color, icon) in enumerate(stats):
            row = i // 4
            col = i % 4
            card = self.create_stat_card(title, value, color, icon)
            stats_layout.addWidget(card, row, col)
            self.stat_labels[title] = card.findChild(QLabel, "value_label")
        
        layout.addLayout(stats_layout)
        
        # Split layout for charts and recent activity
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Recent activity
        recent_group = QGroupBox("Recent Invoice Activity")
        recent_layout = QVBoxLayout(recent_group)
        
        self.recent_table = QTableWidget()
        self.recent_table.setMaximumHeight(250)
        recent_layout.addWidget(self.recent_table)
        
        refresh_recent_btn = QPushButton("🔄 Refresh")
        refresh_recent_btn.clicked.connect(self.refresh_recent_activity)
        recent_layout.addWidget(refresh_recent_btn)
        
        splitter.addWidget(recent_group)
        
        # Quick stats and actions
        quick_group = QGroupBox("Quick Actions & System Status")
        quick_layout = QVBoxLayout(quick_group)
        
        # System status
        system_status_group = QGroupBox("System Status")
        system_status_layout = QFormLayout(system_status_group)
        
        self.db_status_label = QLabel("✅ Connected")
        self.db_status_label.setStyleSheet("color: #28a745; font-weight: bold;")
        system_status_layout.addRow("Database:", self.db_status_label)
        
        self.fbr_status_label = QLabel("❓ Not Tested")
        self.fbr_status_label.setStyleSheet("color: #ffc107; font-weight: bold;")
        system_status_layout.addRow("FBR API:", self.fbr_status_label)
        
        test_connection_btn = QPushButton("🔍 Test FBR Connection")
        test_connection_btn.clicked.connect(self.test_fbr_connection)
        system_status_layout.addRow("", test_connection_btn)
        
        quick_layout.addWidget(system_status_group)
        
        # Quick actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QGridLayout(actions_group)
        
        actions = [
            ("📄 New Invoice", self.new_invoice, "success"),
            ("📦 Add/Edit Items", self.manage_items, None),
            ("👥 Manage Buyers", self.manage_buyers, None),
            ("⚡ Process Queue", self.process_fbr_queue, "warning"),
            ("📊 Export Data", self.export_data, None),
            ("⚙️ Settings", self.open_settings, None)
        ]
        
        for i, (text, handler, style) in enumerate(actions):
            row = i // 2
            col = i % 2
            btn = QPushButton(text)
            if style:
                btn.setProperty("style", style)
            btn.clicked.connect(handler)
            actions_layout.addWidget(btn, row, col)
        
        quick_layout.addWidget(actions_group)
        quick_layout.addStretch()
        
        splitter.addWidget(quick_group)
        layout.addWidget(splitter)
        
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
        value_label.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")
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

        # Filter controls
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("Status:"))
        self.invoice_status_filter = QComboBox()
        self.invoice_status_filter.addItems(["All", "Draft", "Validated", "Submitted", "Completed", "Failed"])
        self.invoice_status_filter.currentTextChanged.connect(self.refresh_invoices_table)
        filter_layout.addWidget(self.invoice_status_filter)
        
        filter_layout.addWidget(QLabel("FBR Status:"))
        self.fbr_status_filter = QComboBox()
        self.fbr_status_filter.addItems(["All", "Pending", "Valid", "Invalid", "Error"])
        self.fbr_status_filter.currentTextChanged.connect(self.refresh_invoices_table)
        filter_layout.addWidget(self.fbr_status_filter)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_invoices_table)
        filter_layout.addWidget(refresh_btn)
        
        toolbar_layout.addLayout(filter_layout)

        layout.addLayout(toolbar_layout)

        # Invoices table
        self.invoices_table = QTableWidget()
        self.invoices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.invoices_table.setAlternatingRowColors(True)
        self.invoices_table.doubleClicked.connect(self.edit_invoice)
        layout.addWidget(self.invoices_table)

        return widget

    def create_items_tab(self):
        """Create items management tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        manage_items_btn = QPushButton("📦 Add/Edit Items")
        manage_items_btn.setProperty("style", "success")
        manage_items_btn.clicked.connect(self.manage_items)
        toolbar_layout.addWidget(manage_items_btn)
        
        toolbar_layout.addStretch()
        
        # Search
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.items_search_edit = QLineEdit()
        self.items_search_edit.setPlaceholderText("Search items...")
        self.items_search_edit.textChanged.connect(self.filter_items)
        search_layout.addWidget(self.items_search_edit)
        
        refresh_items_btn = QPushButton("🔄 Refresh")
        refresh_items_btn.clicked.connect(self.refresh_items_table)
        search_layout.addWidget(refresh_items_btn)
        
        toolbar_layout.addLayout(search_layout)
        layout.addLayout(toolbar_layout)
        
        # Items table
        self.items_table = QTableWidget()
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.items_table.setAlternatingRowColors(True)
        layout.addWidget(self.items_table)
        
        return widget

    def create_buyers_tab(self):
        """Create buyers management tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        manage_buyers_btn = QPushButton("👥 Manage Buyers")
        manage_buyers_btn.setProperty("style", "success")
        manage_buyers_btn.clicked.connect(self.manage_buyers)
        toolbar_layout.addWidget(manage_buyers_btn)
        
        toolbar_layout.addStretch()
        
        # Search and filters
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.buyers_search_edit = QLineEdit()
        self.buyers_search_edit.setPlaceholderText("Search buyers...")
        self.buyers_search_edit.textChanged.connect(self.filter_buyers)
        search_layout.addWidget(self.buyers_search_edit)
        
        search_layout.addWidget(QLabel("Type:"))
        self.buyer_type_filter = QComboBox()
        self.buyer_type_filter.addItems(["All", "Registered", "Unregistered"])
        self.buyer_type_filter.currentTextChanged.connect(self.filter_buyers)
        search_layout.addWidget(self.buyer_type_filter)
        
        refresh_buyers_btn = QPushButton("🔄 Refresh")
        refresh_buyers_btn.clicked.connect(self.refresh_buyers_table)
        search_layout.addWidget(refresh_buyers_btn)
        
        toolbar_layout.addLayout(search_layout)
        layout.addLayout(toolbar_layout)
        
        # Buyers table
        self.buyers_table = QTableWidget()
        self.buyers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.buyers_table.setAlternatingRowColors(True)
        layout.addWidget(self.buyers_table)
        
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
        self.queue_progress.setMaximumHeight(25)
        controls_layout.addWidget(self.queue_progress)
        
        # Progress label
        self.queue_progress_label = QLabel("")
        self.queue_progress_label.setVisible(False)
        controls_layout.addWidget(self.queue_progress_label)

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

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Status Filter:"))
        self.logs_filter_combo = QComboBox()
        self.logs_filter_combo.addItems(["All", "Success", "Invalid", "Error", "Timeout"])
        self.logs_filter_combo.currentTextChanged.connect(self.refresh_logs_table)
        filter_layout.addWidget(self.logs_filter_combo)
        
        filter_layout.addWidget(QLabel("Date Range:"))
        self.logs_date_from = QDateEdit()
        self.logs_date_from.setDate(QDate.currentDate().addDays(-7))
        self.logs_date_from.dateChanged.connect(self.refresh_logs_table)
        filter_layout.addWidget(self.logs_date_from)
        
        filter_layout.addWidget(QLabel("to"))
        self.logs_date_to = QDateEdit()
        self.logs_date_to.setDate(QDate.currentDate())
        self.logs_date_to.dateChanged.connect(self.refresh_logs_table)
        filter_layout.addWidget(self.logs_date_to)

        controls_layout.addLayout(filter_layout)
        controls_layout.addStretch()

        export_logs_btn = QPushButton("📊 Export Logs")
        export_logs_btn.clicked.connect(self.export_logs)
        controls_layout.addWidget(export_logs_btn)
        
        refresh_logs_btn = QPushButton("🔄 Refresh")
        refresh_logs_btn.clicked.connect(self.refresh_logs_table)
        controls_layout.addWidget(refresh_logs_btn)

        layout.addLayout(controls_layout)

        # Logs table
        self.logs_table = QTableWidget()
        self.logs_table.setAlternatingRowColors(True)
        layout.addWidget(self.logs_table)

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
            self.refresh_buyers_table()
            self.refresh_queue_table()
            self.refresh_logs_table()
            self.refresh_recent_activity()
            
            # Test database connection
            self.test_database_connection()
            
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
            failed = session.query(Invoices).filter(
                Invoices.company_id == company_id,
                Invoices.fbr_status.in_(['Invalid', 'Error'])
            ).count()
            
            # Count items and buyers
            total_items = session.query(Item).filter_by(company_id=company_id).count()
            active_buyers = session.query(Buyer).filter_by(
                company_id=company_id, 
                is_active=True
            ).count()
            
            # Count queue items
            queue_items = session.query(FBRQueue).filter_by(
                company_id=company_id,
                status='Pending'
            ).count()
            
            # Calculate today's revenue
            today = datetime.now().date()
            today_revenue = session.query(Invoices).filter(
                Invoices.company_id == company_id,
                Invoices.posting_date >= today,
                Invoices.posting_date < today + timedelta(days=1)
            ).with_entities(Invoices.grand_total).all()
            
            total_revenue = sum([r[0] for r in today_revenue if r[0]]) or 0
            
            # Update stat cards
            self.stat_labels["Total Invoices"].setText(str(total_invoices))
            self.stat_labels["Pending FBR"].setText(str(pending_fbr))
            self.stat_labels["Successful"].setText(str(successful))
            self.stat_labels["Failed"].setText(str(failed))
            self.stat_labels["Total Items"].setText(str(total_items))
            self.stat_labels["Active Buyers"].setText(str(active_buyers))
            self.stat_labels["Queue Items"].setText(str(queue_items))
            self.stat_labels["Today's Revenue"].setText(f"PKR {total_revenue:,.0f}")
            
        except Exception as e:
            print(f"Error updating dashboard stats: {e}")

    def test_database_connection(self):
        """Test database connection status"""
        try:
            session = self.db_manager.get_session()
            # Simple query to test connection
            session.query(Company).filter_by(ntn_cnic=self.current_company['ntn_cnic']).first()
            self.db_status_label.setText("✅ Connected")
            self.db_status_label.setStyleSheet("color: #28a745; font-weight: bold;")
        except Exception as e:
            self.db_status_label.setText("❌ Disconnected")
            self.db_status_label.setStyleSheet("color: #dc3545; font-weight: bold;")

    def test_fbr_connection(self):
        """Test FBR API connection"""
        try:
            session = self.db_manager.get_session()
            settings = session.query(FBRSettings).filter_by(
                company_id=self.current_company['ntn_cnic']
            ).first()
            
            if not settings or not settings.pral_authorization_token:
                self.fbr_status_label.setText("❌ No Token")
                self.fbr_status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
                QMessageBox.warning(
                    self, "FBR Settings Missing",
                    "Please configure FBR settings first in the Settings tab."
                )
                return
            
            self.fbr_status_label.setText("🔍 Testing...")
            self.fbr_status_label.setStyleSheet("color: #ffc107; font-weight: bold;")
            
            # Test with a simple API call
            import requests
            headers = {
                'Authorization': f'Bearer {settings.pral_authorization_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                "https://gw.fbr.gov.pk/pdi/v1/provinces",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.fbr_status_label.setText("✅ Connected")
                self.fbr_status_label.setStyleSheet("color: #28a745; font-weight: bold;")
                QMessageBox.information(
                    self, "FBR Connection Test",
                    "✅ FBR API connection successful!"
                )
            else:
                self.fbr_status_label.setText("❌ Failed")
                self.fbr_status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
                QMessageBox.warning(
                    self, "FBR Connection Test",
                    f"❌ FBR API connection failed: HTTP {response.status_code}"
                )
                
        except requests.exceptions.Timeout:
            self.fbr_status_label.setText("❌ Timeout")
            self.fbr_status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
            QMessageBox.warning(
                self, "FBR Connection Test",
                "❌ Connection timed out. Please check your internet connection."
            )
        except Exception as e:
            self.fbr_status_label.setText("❌ Error")
            self.fbr_status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
            QMessageBox.critical(
                self, "FBR Connection Test",
                f"❌ Connection test failed: {str(e)}"
            )

    def toggle_mode(self, checked):
        """Toggle between Sandbox and Production mode"""
        self.is_sandbox_mode = checked
        mode_text = "Sandbox" if checked else "Production"
        self.statusBar().showMessage(
            f"Connected as: {self.current_company['name']} | Mode: {mode_text}"
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
            'sellerAddress': self.current_company['address'],
            'sellerProvince': self.current_company.get('province', 'Sindh')
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
            
            try:
                session = self.db_manager.get_session()
                invoice = session.query(Invoices).filter_by(id=invoice_id).first()
                
                if invoice:
                    # Create invoice dialog in edit mode
                    mode = "sandbox" if self.is_sandbox_mode else "production"
                    
                    # Build invoice data for editing
                    invoice_data = {
                        'id': invoice.id,
                        'invoice_number': invoice.invoice_number,
                        'invoiceType': invoice.invoice_type,
                        'invoiceDate': invoice.posting_date.strftime('%Y-%m-%d'),
                        'buyerNTNCNIC': invoice.buyer_ntn_cnic,
                        'buyerBusinessName': invoice.buyer_name,
                        'buyerAddress': invoice.buyer_address,
                        'buyerProvince': invoice.buyer_province,
                        'buyerRegistrationType': invoice.buyer_type
                    }
                    
                    seller_data = {
                        'sellerNTNCNIC': self.current_company['ntn_cnic'],
                        'sellerBusinessName': self.current_company['name'],
                        'sellerAddress': self.current_company['address'],
                        'sellerProvince': self.current_company.get('province', 'Sindh')
                    }
                    
                    dialog = FBRInvoiceDialog(
                        self,
                        invoice_data=invoice_data,
                        mode=mode,
                        company_data=self.current_company,
                        seller_data=seller_data
                    )
                    dialog.invoice_saved.connect(self.on_invoice_saved)
                    
                    if dialog.exec() == QDialog.DialogCode.Accepted:
                        self.refresh_invoices_table()
                        self.update_dashboard_stats()
                else:
                    QMessageBox.warning(self, "Error", "Invoice not found!")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load invoice for editing: {str(e)}")
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
            service = FBRSubmissionService(self.db_manager, self.current_company['ntn_cnic'])
            mode = "sandbox" if self.is_sandbox_mode else "production"
            
            result = service.validate_invoice_with_fbr(invoice_id, mode)
            
            if result["success"]:
                validation_response = result["response"].get("validationResponse", {})
                status = validation_response.get("status", "Unknown")
                
                if status.lower() == "valid":
                    QMessageBox.information(
                        self, "Validation Result", 
                        "✅ Invoice validation successful!\n\nThe invoice is valid and ready for submission to FBR."
                    )
                else:
                    error_msg = validation_response.get("error", "No error details provided")
                    QMessageBox.warning(
                        self, "Validation Result", 
                        f"❌ Invoice validation failed!\n\nStatus: {status}\nError: {error_msg}"
                    )
            else:
                QMessageBox.warning(
                    self, "Validation Error", 
                    f"Validation request failed: {result.get('error', 'Unknown error')}"
                )
                
            self.refresh_invoices_table()
            self.update_dashboard_stats()
                
        except Exception as e:
            QMessageBox.critical(self, "Validation Error", f"Failed to validate invoice: {str(e)}")

    def validate_all_invoices(self):
        """Validate all pending invoices"""
        try:
            session = self.db_manager.get_session()
            pending_invoices = session.query(Invoices).filter_by(
                company_id=self.current_company['ntn_cnic'],
                fbr_status=None
            ).all()
            
            if not pending_invoices:
                QMessageBox.information(self, "No Pending Invoices", "No invoices pending validation.")
                return
            
            reply = QMessageBox.question(
                self, "Validate All Invoices",
                f"Validate {len(pending_invoices)} pending invoice(s)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                service = FBRSubmissionService(self.db_manager, self.current_company['ntn_cnic'])
                mode = "sandbox" if self.is_sandbox_mode else "production"
                
                success_count = 0
                failed_count = 0
                
                for invoice in pending_invoices:
                    try:
                        result = service.validate_invoice_with_fbr(invoice.id, mode)
                        if result["success"]:
                            success_count += 1
                        else:
                            failed_count += 1
                    except:
                        failed_count += 1
                
                QMessageBox.information(
                    self, "Validation Complete",
                    f"Validation completed!\n\nSuccess: {success_count}\nFailed: {failed_count}"
                )
                
                self.refresh_invoices_table()
                self.update_dashboard_stats()
                
        except Exception as e:
            QMessageBox.critical(self, "Validation Error", f"Failed to validate invoices: {str(e)}")

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
        try:
            service = FBRSubmissionService(self.db_manager, self.current_company['ntn_cnic'])
            mode = "sandbox" if self.is_sandbox_mode else "production"
            
            success_count = 0
            failed_count = 0
            errors = []
            
            for invoice_id in invoice_ids:
                try:
                    result = service.submit_invoice(invoice_id, mode)
                    if result["success"]:
                        success_count += 1
                    else:
                        failed_count += 1
                        errors.append(f"Invoice {invoice_id}: {result.get('error', 'Unknown error')}")
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Invoice {invoice_id}: {str(e)}")
            
            # Show results
            message = f"Submission completed!\n\nSuccess: {success_count}\nFailed: {failed_count}"
            if errors:
                message += f"\n\nErrors:\n" + "\n".join(errors[:5])  # Show first 5 errors
                if len(errors) > 5:
                    message += f"\n... and {len(errors) - 5} more errors"
            
            if failed_count > 0:
                QMessageBox.warning(self, "Submission Results", message)
            else:
                QMessageBox.information(self, "Submission Results", message)
            
            self.refresh_invoices_table()
            self.refresh_queue_table()
            self.update_dashboard_stats()
            
        except Exception as e:
            QMessageBox.critical(self, "Submission Error", f"Failed to submit invoices: {str(e)}")

    def manage_items(self):
        """Open item management dialog"""
        dialog = ItemManagementDialog(self.db_manager, self.current_company['ntn_cnic'], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_items_table()
            self.update_dashboard_stats()

    def manage_buyers(self):
        """Open buyer management dialog"""
        dialog = BuyerManagementDialog(self.db_manager, self.current_company, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_buyers_table()
            self.update_dashboard_stats()

    def open_settings(self):
        """Open FBR settings dialog"""
        dialog = FBRSettingsDialog(self.db_manager, self.current_company, self)
        dialog.settings_saved.connect(self.on_settings_saved)
        dialog.exec()

    def on_settings_saved(self):
        """Handle when settings are saved"""
        self.statusBar().showMessage("Settings saved successfully", 3000)
        # Test FBR connection after settings update
        QTimer.singleShot(1000, self.test_fbr_connection)

    def show_about_dialog(self):
        """Show about dialog"""
        dialog = AboutDialog(self)
        dialog.exec()

    def show_user_guide(self):
        """Show user guide"""
        QMessageBox.information(
            self, "User Guide",
            "User Guide:\n\n"
            "1. Select or create a company\n"
            "2. Configure FBR settings in the Settings tab\n"
            "3. Add items and buyers\n"
            "4. Create invoices\n"
            "5. Validate and submit to FBR\n\n"
            "For detailed documentation, please contact your system administrator."
        )

    def refresh_invoices_table(self):
        """Refresh invoices table with company-specific data"""
        if not self.db_manager or not self.current_company:
            return

        try:
            session = self.db_manager.get_session()
            company_id = self.current_company['ntn_cnic']
            
            # Build query with filters
            query = session.query(Invoices).filter_by(company_id=company_id)
            
            # Apply status filter
            status_filter = self.invoice_status_filter.currentText()
            if status_filter != "All":
                query = query.filter_by(status=status_filter)
            
            # Apply FBR status filter
            fbr_status_filter = self.fbr_status_filter.currentText()
            if fbr_status_filter == "Pending":
                query = query.filter(Invoices.fbr_status.is_(None))
            elif fbr_status_filter != "All":
                query = query.filter_by(fbr_status=fbr_status_filter)
            
            invoices = query.order_by(Invoices.created_at.desc()).limit(200).all()

            self.invoices_table.setRowCount(len(invoices))
            self.invoices_table.setColumnCount(9)
            self.invoices_table.setHorizontalHeaderLabels([
                "ID", "Invoice No", "Buyer Name", "Date", "Amount", 
                "Status", "FBR Status", "FBR Invoice No", "Created"
            ])

            for row, invoice in enumerate(invoices):
                self.invoices_table.setItem(row, 0, QTableWidgetItem(str(invoice.id)))
                self.invoices_table.setItem(row, 1, QTableWidgetItem(invoice.invoice_number or ""))
                self.invoices_table.setItem(row, 2, QTableWidgetItem(invoice.buyer_name or ""))
                self.invoices_table.setItem(row, 3, QTableWidgetItem(
                    invoice.posting_date.strftime("%Y-%m-%d") if invoice.posting_date else ""
                ))
                self.invoices_table.setItem(row, 4, QTableWidgetItem(
                    f"PKR {invoice.grand_total:,.2f}" if invoice.grand_total else "PKR 0.00"
                ))
                
                # Color code status
                status_item = QTableWidgetItem(invoice.status or "Draft")
                if invoice.status == "Completed":
                    status_item.setBackground(QColor("#28a745"))
                elif invoice.status == "Failed":
                    status_item.setBackground(QColor("#dc3545"))
                elif invoice.status == "Submitted":
                    status_item.setBackground(QColor("#17a2b8"))
                else:
                    status_item.setBackground(QColor("#ffc107"))
                self.invoices_table.setItem(row, 5, status_item)
                
                # Color code FBR status
                fbr_status_item = QTableWidgetItem(invoice.fbr_status or "Pending")
                if invoice.fbr_status == "Valid":
                    fbr_status_item.setBackground(QColor("#28a745"))
                elif invoice.fbr_status in ["Invalid", "Error"]:
                    fbr_status_item.setBackground(QColor("#dc3545"))
                else:
                    fbr_status_item.setBackground(QColor("#ffc107"))
                self.invoices_table.setItem(row, 6, fbr_status_item)
                
                self.invoices_table.setItem(row, 7, QTableWidgetItem(invoice.fbr_invoice_number or ""))
                self.invoices_table.setItem(row, 8, QTableWidgetItem(
                    invoice.created_at.strftime("%Y-%m-%d %H:%M") if invoice.created_at else ""
                ))

            self.invoices_table.resizeColumnsToContents()
            header = self.invoices_table.horizontalHeader()
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Buyer name
            
        except Exception as e:
            print(f"Error refreshing invoices table: {e}")

    def refresh_items_table(self):
        """Refresh items table with company-specific data"""
        if not self.db_manager or not self.current_company:
            return

        try:
            session = self.db_manager.get_session()
            company_id = self.current_company['ntn_cnic']
            
            # Build query with search filter
            query = session.query(Item).filter_by(company_id=company_id)
            
            search_text = self.items_search_edit.text().lower() if hasattr(self, 'items_search_edit') else ""
            if search_text:
                query = query.filter(
                    Item.name.ilike(f'%{search_text}%') |
                    Item.hs_code.ilike(f'%{search_text}%') |
                    Item.description.ilike(f'%{search_text}%')
                )
            
            items = query.order_by(Item.created_at.desc()).all()

            self.items_table.setRowCount(len(items))
            self.items_table.setColumnCount(7)
            self.items_table.setHorizontalHeaderLabels([
                "ID", "Name", "HS Code", "UoM", "Category", "Standard Rate", "Status"
            ])

            for row, item in enumerate(items):
                self.items_table.setItem(row, 0, QTableWidgetItem(str(item.id)))
                self.items_table.setItem(row, 1, QTableWidgetItem(item.name or ""))
                self.items_table.setItem(row, 2, QTableWidgetItem(item.hs_code or ""))
                self.items_table.setItem(row, 3, QTableWidgetItem(item.uom or ""))
                self.items_table.setItem(row, 4, QTableWidgetItem(item.category or ""))
                self.items_table.setItem(row, 5, QTableWidgetItem(
                    f"PKR {item.standard_rate:,.2f}" if item.standard_rate else "PKR 0.00"
                ))
                
                status_item = QTableWidgetItem("Active" if item.is_active else "Inactive")
                if item.is_active:
                    status_item.setBackground(QColor("#28a745"))
                else:
                    status_item.setBackground(QColor("#dc3545"))
                self.items_table.setItem(row, 6, status_item)

            self.items_table.resizeColumnsToContents()
            header = self.items_table.horizontalHeader()
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name
            
        except Exception as e:
            print(f"Error refreshing items table: {e}")

    def filter_items(self):
        """Filter items table based on search"""
        self.refresh_items_table()

    def refresh_buyers_table(self):
        """Refresh buyers table with company-specific data"""
        if not self.db_manager or not self.current_company:
            return

        try:
            session = self.db_manager.get_session()
            company_id = self.current_company['ntn_cnic']
            
            # Build query with filters
            query = session.query(Buyer).filter_by(company_id=company_id)
            
            # Apply search filter
            search_text = self.buyers_search_edit.text().lower() if hasattr(self, 'buyers_search_edit') else ""
            if search_text:
                query = query.filter(
                    Buyer.name.ilike(f'%{search_text}%') |
                    Buyer.ntn_cnic.ilike(f'%{search_text}%') |
                    Buyer.province.ilike(f'%{search_text}%')
                )
            
            # Apply type filter
            type_filter = self.buyer_type_filter.currentText() if hasattr(self, 'buyer_type_filter') else "All"
            if type_filter != "All":
                query = query.filter_by(buyer_type=type_filter)
            
            buyers = query.order_by(Buyer.name.asc()).all()

            self.buyers_table.setRowCount(len(buyers))
            self.buyers_table.setColumnCount(7)
            self.buyers_table.setHorizontalHeaderLabels([
                "ID", "Name", "NTN/CNIC", "Type", "Province", "Phone", "Status"
            ])

            for row, buyer in enumerate(buyers):
                self.buyers_table.setItem(row, 0, QTableWidgetItem(str(buyer.id)))
                self.buyers_table.setItem(row, 1, QTableWidgetItem(buyer.name or ""))
                self.buyers_table.setItem(row, 2, QTableWidgetItem(buyer.ntn_cnic or ""))
                self.buyers_table.setItem(row, 3, QTableWidgetItem(buyer.buyer_type or ""))
                self.buyers_table.setItem(row, 4, QTableWidgetItem(buyer.province or ""))
                self.buyers_table.setItem(row, 5, QTableWidgetItem(buyer.phone or ""))
                
                status_item = QTableWidgetItem("Active" if buyer.is_active else "Inactive")
                if buyer.is_active:
                    status_item.setBackground(QColor("#28a745"))
                else:
                    status_item.setBackground(QColor("#dc3545"))
                self.buyers_table.setItem(row, 6, status_item)

            self.buyers_table.resizeColumnsToContents()
            header = self.buyers_table.horizontalHeader()
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Name
            
        except Exception as e:
            print(f"Error refreshing buyers table: {e}")

    def filter_buyers(self):
        """Filter buyers table based on search and type"""
        self.refresh_buyers_table()

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
                .order_by(FBRQueue.priority.desc(), FBRQueue.created_at.asc())
                .limit(200)
                .all()
            )

            self.queue_table.setRowCount(len(queue_items))
            self.queue_table.setColumnCount(8)
            self.queue_table.setHorizontalHeaderLabels([
                "ID", "Document", "Status", "Priority", "Retries", "Error", "Created", "Last Retry"
            ])

            for row, item in enumerate(queue_items):
                self.queue_table.setItem(row, 0, QTableWidgetItem(str(item.id)))
                self.queue_table.setItem(row, 1, QTableWidgetItem(
                    f"{item.document_type} #{item.document_id}"
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
                    (item.error_message or "")[:50] + "..." if item.error_message and len(item.error_message) > 50 else (item.error_message or "")
                ))
                self.queue_table.setItem(row, 6, QTableWidgetItem(
                    item.created_at.strftime("%Y-%m-%d %H:%M") if item.created_at else ""
                ))
                self.queue_table.setItem(row, 7, QTableWidgetItem(
                    item.last_retry_at.strftime("%Y-%m-%d %H:%M") if item.last_retry_at else ""
                ))

            self.queue_table.resizeColumnsToContents()
            header = self.queue_table.horizontalHeader()
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Error column
            
        except Exception as e:
            print(f"Error refreshing queue table: {e}")

    def refresh_logs_table(self):
        """Refresh logs table with company-specific data"""
        if not self.db_manager or not self.current_company:
            return

        try:
            session = self.db_manager.get_session()
            company_id = self.current_company['ntn_cnic']
            
            # Build query with filters
            query = session.query(FBRLogs).filter_by(company_id=company_id)
            
            # Apply status filter
            status_filter = self.logs_filter_combo.currentText() if hasattr(self, 'logs_filter_combo') else "All"
            if status_filter != "All":
                query = query.filter_by(status=status_filter)
            
            # Apply date range filter
            if hasattr(self, 'logs_date_from') and hasattr(self, 'logs_date_to'):
                from_date = self.logs_date_from.date().toPython()
                to_date = self.logs_date_to.date().toPython()
                query = query.filter(
                    FBRLogs.submitted_at >= from_date,
                    FBRLogs.submitted_at <= to_date + timedelta(days=1)
                )
            
            logs = query.order_by(FBRLogs.submitted_at.desc()).limit(200).all()

            self.logs_table.setRowCount(len(logs))
            self.logs_table.setColumnCount(8)
            self.logs_table.setHorizontalHeaderLabels([
                "ID", "Document", "FBR Invoice No", "Status", "Processing Time", 
                "Submitted", "Mode", "Error"
            ])

            for row, log in enumerate(logs):
                self.logs_table.setItem(row, 0, QTableWidgetItem(str(log.id)))
                self.logs_table.setItem(row, 1, QTableWidgetItem(
                    f"{log.document_type} #{log.document_id}"
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
                    f"{log.processing_time:.0f}ms" if log.processing_time else ""
                ))
                self.logs_table.setItem(row, 5, QTableWidgetItem(
                    log.submitted_at.strftime("%Y-%m-%d %H:%M") if log.submitted_at else ""
                ))
                self.logs_table.setItem(row, 6, QTableWidgetItem(log.mode or "sandbox"))
                self.logs_table.setItem(row, 7, QTableWidgetItem(
                    (log.validation_errors or "")[:50] + "..." if log.validation_errors and len(log.validation_errors) > 50 else (log.validation_errors or "")
                ))

            self.logs_table.resizeColumnsToContents()
            header = self.logs_table.horizontalHeader()
            header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)  # Error column
            
        except Exception as e:
            print(f"Error refreshing logs table: {e}")

    def refresh_recent_activity(self):
        """Refresh recent activity table"""
        if not self.db_manager or not self.current_company:
            return

        try:
            session = self.db_manager.get_session()
            company_id = self.current_company['ntn_cnic']
            
            # Get recent invoices
            recent_invoices = (
                session.query(Invoices)
                .filter_by(company_id=company_id)
                .order_by(Invoices.updated_at.desc())
                .limit(10)
                .all()
            )

            self.recent_table.setRowCount(len(recent_invoices))
            self.recent_table.setColumnCount(5)
            self.recent_table.setHorizontalHeaderLabels([
                "Invoice No", "Buyer", "Amount", "Status", "Updated"
            ])

            for row, invoice in enumerate(recent_invoices):
                self.recent_table.setItem(row, 0, QTableWidgetItem(invoice.invoice_number or ""))
                self.recent_table.setItem(row, 1, QTableWidgetItem(invoice.buyer_name or ""))
                self.recent_table.setItem(row, 2, QTableWidgetItem(
                    f"PKR {invoice.grand_total:,.0f}" if invoice.grand_total else "PKR 0"
                ))
                
                # Color code status
                status_text = f"{invoice.status or 'Draft'}"
                if invoice.fbr_status:
                    status_text += f" ({invoice.fbr_status})"
                    
                status_item = QTableWidgetItem(status_text)
                if invoice.fbr_status == "Valid":
                    status_item.setBackground(QColor("#28a745"))
                elif invoice.fbr_status in ["Invalid", "Error"]:
                    status_item.setBackground(QColor("#dc3545"))
                else:
                    status_item.setBackground(QColor("#ffc107"))
                self.recent_table.setItem(row, 3, status_item)
                
                self.recent_table.setItem(row, 4, QTableWidgetItem(
                    invoice.updated_at.strftime("%m-%d %H:%M") if invoice.updated_at else ""
                ))

            self.recent_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"Error refreshing recent activity: {e}")

    def process_fbr_queue(self):
        """Process FBR queue for current company"""
        if not self.db_manager or not self.current_company:
            return

        try:
            # Check if there are pending items
            session = self.db_manager.get_session()
            pending_count = session.query(FBRQueue).filter_by(
                company_id=self.current_company['ntn_cnic'],
                status='Pending'
            ).count()
            
            if pending_count == 0:
                QMessageBox.information(self, "Queue Processing", "No pending items in queue.")
                return
            
            reply = QMessageBox.question(
                self, "Process FBR Queue",
                f"Process {pending_count} pending queue item(s)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Show progress
                self.queue_progress.setVisible(True)
                self.queue_progress_label.setVisible(True)
                self.queue_progress.setRange(0, 0)  # Indeterminate
                
                # Start processing thread
                mode = "sandbox" if self.is_sandbox_mode else "production"
                self.processing_thread = FBRProcessingThread(
                    self.db_manager, 
                    self.current_company['ntn_cnic'], 
                    mode, 
                    50
                )
                self.processing_thread.progress_updated.connect(self.on_queue_progress_updated)
                self.processing_thread.processing_finished.connect(self.on_queue_processing_finished)
                self.processing_thread.start()
                
        except Exception as e:
            QMessageBox.critical(self, "Queue Error", f"Failed to process queue: {str(e)}")

    def on_queue_progress_updated(self, progress, status):
        """Handle queue processing progress update"""
        self.queue_progress_label.setText(status)
        if progress > 0:
            self.queue_progress.setRange(0, 100)
            self.queue_progress.setValue(progress)

    def on_queue_processing_finished(self, result):
        """Handle queue processing completion"""
        # Hide progress
        self.queue_progress.setVisible(False)
        self.queue_progress_label.setVisible(False)
        
        # Show results
        message = (
            f"Queue processing completed!\n\n"
            f"Processed: {result.get('processed_count', 0)} items\n"
            f"Failed: {result.get('failed_count', 0)} items"
        )
        
        if "error" in result:
            message += f"\n\nError: {result['error']}"
            QMessageBox.warning(self, "Queue Processing", message)
        else:
            QMessageBox.information(self, "Queue Processing", message)
        
        # Refresh tables
        self.refresh_queue_table()
        self.refresh_logs_table()
        self.refresh_invoices_table()
        self.update_dashboard_stats()

    def retry_failed_items(self):
        """Retry failed queue items"""
        try:
            queue_manager = FBRQueueManager(self.db_manager, self.current_company['ntn_cnic'])
            result = queue_manager.retry_failed_items()
            
            if result["success"]:
                QMessageBox.information(
                    self, "Retry Queue Items",
                    f"Retried {result['retry_count']} failed items."
                )
            else:
                QMessageBox.warning(
                    self, "Retry Queue Items",
                    f"Failed to retry items: {result.get('error', 'Unknown error')}"
                )
            
            self.refresh_queue_table()
            
        except Exception as e:
            QMessageBox.critical(self, "Retry Error", f"Failed to retry queue items: {str(e)}")

    def clear_completed_queue_items(self):
        """Clear completed queue items"""
        try:
            reply = QMessageBox.question(
                self, "Clear Completed Items",
                "Clear all completed queue items older than 7 days?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                queue_manager = FBRQueueManager(self.db_manager, self.current_company['ntn_cnic'])
                result = queue_manager.clear_completed_items(7)
                
                if result["success"]:
                    QMessageBox.information(
                        self, "Clear Completed Items",
                        f"Cleared {result['deleted_count']} completed items."
                    )
                else:
                    QMessageBox.warning(
                        self, "Clear Completed Items",
                        f"Failed to clear items: {result.get('error', 'Unknown error')}"
                    )
                
                self.refresh_queue_table()
                
        except Exception as e:
            QMessageBox.critical(self, "Clear Error", f"Failed to clear queue items: {str(e)}")

    def export_logs(self):
        """Export logs to CSV"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Logs",
                f"fbr_logs_{self.current_company['ntn_cnic']}_{datetime.now().strftime('%Y%m%d')}.csv",
                "CSV files (*.csv);;All files (*.*)"
            )
            
            if filename:
                session = self.db_manager.get_session()
                logs = session.query(FBRLogs).filter_by(
                    company_id=self.current_company['ntn_cnic']
                ).all()
                
                # Create DataFrame
                import pandas as pd
                data = []
                for log in logs:
                    data.append({
                        'ID': log.id,
                        'Document Type': log.document_type,
                        'Document ID': log.document_id,
                        'FBR Invoice Number': log.fbr_invoice_number or '',
                        'Status': log.status,
                        'Processing Time (ms)': log.processing_time or 0,
                        'Submitted At': log.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if log.submitted_at else '',
                        'Mode': log.mode or 'sandbox',
                        'API Endpoint': log.api_endpoint or '',
                        'Validation Errors': log.validation_errors or ''
                    })
                
                df = pd.DataFrame(data)
                df.to_csv(filename, index=False)
                
                QMessageBox.information(
                    self, "Export Successful",
                    f"Exported {len(logs)} log entries to:\n{filename}"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export logs: {str(e)}")

    def export_data(self):
        """Export company data"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Company Data",
                f"company_data_{self.current_company['ntn_cnic']}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                "Excel files (*.xlsx);;CSV files (*.csv);;All files (*.*)"
            )
            
            if filename:
                session = self.db_manager.get_session()
                company_id = self.current_company['ntn_cnic']
                
                # Get data
                invoices = session.query(Invoices).filter_by(company_id=company_id).all()
                items = session.query(Item).filter_by(company_id=company_id).all()
                buyers = session.query(Buyer).filter_by(company_id=company_id).all()
                
                import pandas as pd
                
                # Create DataFrames
                invoice_data = []
                for inv in invoices:
                    invoice_data.append({
                        'Invoice Number': inv.invoice_number,
                        'Buyer Name': inv.buyer_name,
                        'Date': inv.posting_date.strftime('%Y-%m-%d') if inv.posting_date else '',
                        'Amount': inv.grand_total or 0,
                        'Status': inv.status,
                        'FBR Status': inv.fbr_status or 'Pending',
                        'FBR Invoice Number': inv.fbr_invoice_number or ''
                    })
                
                item_data = []
                for item in items:
                    item_data.append({
                        'Name': item.name,
                        'HS Code': item.hs_code,
                        'UoM': item.uom,
                        'Category': item.category or '',
                        'Standard Rate': item.standard_rate or 0,
                        'Status': 'Active' if item.is_active else 'Inactive'
                    })
                
                buyer_data = []
                for buyer in buyers:
                    buyer_data.append({
                        'Name': buyer.name,
                        'NTN/CNIC': buyer.ntn_cnic,
                        'Type': buyer.buyer_type,
                        'Province': buyer.province or '',
                        'Phone': buyer.phone or '',
                        'Status': 'Active' if buyer.is_active else 'Inactive'
                    })
                
                # Export based on file type
                if filename.endswith('.xlsx'):
                    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                        pd.DataFrame(invoice_data).to_excel(writer, sheet_name='Invoices', index=False)
                        pd.DataFrame(item_data).to_excel(writer, sheet_name='Items', index=False)
                        pd.DataFrame(buyer_data).to_excel(writer, sheet_name='Buyers', index=False)
                else:
                    # Export as CSV (invoices only)
                    pd.DataFrame(invoice_data).to_csv(filename, index=False)
                
                QMessageBox.information(
                    self, "Export Successful",
                    f"Exported company data to:\n{filename}"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export data: {str(e)}")

    def import_data(self):
        """Import company data"""
        QMessageBox.information(
            self, "Import Data",
            "Import functionality will be implemented in a future version.\n\n"
            "For now, you can use the management dialogs to add items and buyers manually."
        )

    def on_invoice_saved(self, invoice_data):
        """Handle when an invoice is saved"""
        try:
            self.refresh_invoices_table()
            self.update_dashboard_stats()
            self.refresh_recent_activity()
            
            self.statusBar().showMessage(
                f"Invoice {invoice_data.get('invoice_number', 'saved')} saved successfully", 
                5000
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to process saved invoice: {str(e)}")

    def closeEvent(self, event):
        """Handle application close event"""
        # Stop any running threads
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.quit()
            self.processing_thread.wait()
        
        # Close database connection
        if self.db_manager:
            self.db_manager.close()
        
        event.accept()


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