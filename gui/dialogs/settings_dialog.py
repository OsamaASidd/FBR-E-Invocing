# gui/dialogs/settings_dialog.py
import sys
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox, QCheckBox, QPushButton,
    QGroupBox, QTabWidget, QWidget, QTextEdit, QMessageBox,
    QFileDialog, QProgressBar, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt6.QtGui import QFont

from fbr_core.models import FBRSettings


class TestConnectionThread(QThread):
    """Background thread for testing FBR API connection"""
    
    connection_tested = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, endpoint, token):
        super().__init__()
        self.endpoint = endpoint
        self.token = token
    
    def run(self):
        """Test the connection in background"""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {self.token}',
                'Content-Type': 'application/json'
            }
            
            # Test with a simple provinces endpoint
            test_url = "https://gw.fbr.gov.pk/pdi/v1/provinces"
            
            response = requests.get(test_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    self.connection_tested.emit(True, f"✅ Connection successful! Found {len(data)} provinces.")
                else:
                    self.connection_tested.emit(False, "⚠️ Connection successful but no data received")
            elif response.status_code == 401:
                self.connection_tested.emit(False, "❌ Authentication failed. Please check your authorization token.")
            else:
                self.connection_tested.emit(False, f"❌ HTTP {response.status_code}: {response.text[:100]}...")
                
        except requests.exceptions.Timeout:
            self.connection_tested.emit(False, "❌ Connection timed out. Please check your internet connection.")
        except requests.exceptions.ConnectionError:
            self.connection_tested.emit(False, "❌ Cannot connect to FBR API. Please check your internet connection.")
        except Exception as e:
            self.connection_tested.emit(False, f"❌ Connection test failed: {str(e)}")


class FBRSettingsDialog(QDialog):
    """Dialog for managing FBR settings for a specific company"""
    
    settings_saved = pyqtSignal()  # Signal when settings are saved
    
    def __init__(self, db_manager, company_data, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.company_data = company_data
        self.company_id = company_data['ntn_cnic']
        
        self.setWindowTitle(f"FBR Settings - {company_data['name']}")
        self.setModal(True)
        self.resize(800, 700)
        
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
            QLineEdit, QComboBox, QSpinBox, QTextEdit {
                background: #0f141c;
                color: #eaeef6;
                border: 1px solid #334561;
                border-radius: 6px;
                padding: 8px 12px;
                min-height: 28px;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {
                border: 1px solid #5aa2ff;
                box-shadow: 0 0 0 2px rgba(90,162,255,0.18);
            }
            QLineEdit[echoMode="2"] {
                font-family: monospace;
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
        self.load_settings()

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
        company_label = QLabel(f"FBR Settings for: {self.company_data['name']}")
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
        
        # Create tab widget
        tab_widget = QTabWidget()
        
        # API Settings tab
        api_tab = self.create_api_settings_tab()
        tab_widget.addTab(api_tab, "🌐 API Configuration")
        
        # Validation Settings tab
        validation_tab = self.create_validation_settings_tab()
        tab_widget.addTab(validation_tab, "✅ Validation")
        
        # Queue Settings tab
        queue_tab = self.create_queue_settings_tab()
        tab_widget.addTab(queue_tab, "⚡ Queue Management")
        
        # Advanced Settings tab
        advanced_tab = self.create_advanced_settings_tab()
        tab_widget.addTab(advanced_tab, "⚙️ Advanced")
        
        layout.addWidget(tab_widget)
        
        # Connection test section
        test_frame = QFrame()
        test_frame.setStyleSheet("""
            QFrame {
                background-color: #1b2028;
                border: 1px solid #2c3b52;
                border-radius: 8px;
                padding: 10px;
                margin: 5px;
            }
        """)
        
        test_layout = QHBoxLayout(test_frame)
        
        self.test_connection_btn = QPushButton("🔍 Test Connection")
        self.test_connection_btn.setProperty("style", "warning")
        self.test_connection_btn.clicked.connect(self.test_connection)
        test_layout.addWidget(self.test_connection_btn)
        
        self.test_progress = QProgressBar()
        self.test_progress.setRange(0, 0)  # Indeterminate
        self.test_progress.setVisible(False)
        self.test_progress.setMaximumHeight(6)
        test_layout.addWidget(self.test_progress)
        
        test_layout.addStretch()
        
        self.connection_status_label = QLabel("")
        test_layout.addWidget(self.connection_status_label)
        
        layout.addWidget(test_frame)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        
        # Reset to defaults
        reset_btn = QPushButton("🔄 Reset to Defaults")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
        # Export settings
        export_btn = QPushButton("📤 Export Settings")
        export_btn.clicked.connect(self.export_settings)
        button_layout.addWidget(export_btn)
        
        # Import settings
        import_btn = QPushButton("📥 Import Settings")
        import_btn.clicked.connect(self.import_settings)
        button_layout.addWidget(import_btn)
        
        button_layout.addStretch()
        
        # Cancel button
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # Save button
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setProperty("style", "success")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)

    def create_api_settings_tab(self):
        """Create API settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # API Endpoints group
        endpoints_group = QGroupBox("API Endpoints")
        endpoints_layout = QFormLayout(endpoints_group)
        
        self.api_endpoint_edit = QLineEdit()
        self.api_endpoint_edit.setPlaceholderText("https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata_sb")
        endpoints_layout.addRow("Submission API:", self.api_endpoint_edit)
        
        self.validation_endpoint_edit = QLineEdit()
        self.validation_endpoint_edit.setPlaceholderText("https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata_sb")
        endpoints_layout.addRow("Validation API:", self.validation_endpoint_edit)
        
        layout.addWidget(endpoints_group)
        
        # Authentication group
        auth_group = QGroupBox("Authentication")
        auth_layout = QFormLayout(auth_group)
        
        self.auth_token_edit = QLineEdit()
        self.auth_token_edit.setPlaceholderText("Enter your PRAL authorization token")
        self.auth_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        auth_layout.addRow("Authorization Token*:", self.auth_token_edit)
        
        # Show/hide token button
        token_layout = QHBoxLayout()
        token_layout.addWidget(self.auth_token_edit)
        
        self.show_token_btn = QPushButton("👁️")
        self.show_token_btn.setMaximumWidth(40)
        self.show_token_btn.clicked.connect(self.toggle_token_visibility)
        self.show_token_btn.setToolTip("Show/Hide Token")
        token_layout.addWidget(self.show_token_btn)
        
        auth_layout.addRow("Authorization Token*:", token_layout)
        
        self.login_id_edit = QLineEdit()
        self.login_id_edit.setPlaceholderText("Enter your PRAL login ID")
        auth_layout.addRow("Login ID:", self.login_id_edit)
        
        self.login_password_edit = QLineEdit()
        self.login_password_edit.setPlaceholderText("Enter your PRAL password")
        self.login_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        auth_layout.addRow("Login Password:", self.login_password_edit)
        
        layout.addWidget(auth_group)
        
        # Timeout settings
        timeout_group = QGroupBox("Connection Settings")
        timeout_layout = QFormLayout(timeout_group)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setSuffix(" seconds")
        self.timeout_spin.setValue(30)
        timeout_layout.addRow("Request Timeout:", self.timeout_spin)
        
        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(1, 10)
        self.max_retries_spin.setValue(3)
        timeout_layout.addRow("Max Retries:", self.max_retries_spin)
        
        layout.addWidget(timeout_group)
        
        layout.addStretch()
        
        return widget

    def create_validation_settings_tab(self):
        """Create validation settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Validation behavior group
        behavior_group = QGroupBox("Validation Behavior")
        behavior_layout = QVBoxLayout(behavior_group)
        
        self.auto_validate_check = QCheckBox("Auto-validate invoices before submission")
        self.auto_validate_check.setToolTip("Automatically validate invoices with FBR before submitting")
        behavior_layout.addWidget(self.auto_validate_check)
        
        self.strict_validation_check = QCheckBox("Enable strict validation mode")
        self.strict_validation_check.setToolTip("Apply additional validation rules beyond FBR requirements")
        behavior_layout.addWidget(self.strict_validation_check)
        
        self.validate_hs_codes_check = QCheckBox("Validate HS codes against FBR database")
        self.validate_hs_codes_check.setToolTip("Check if HS codes are valid according to FBR")
        behavior_layout.addWidget(self.validate_hs_codes_check)
        
        layout.addWidget(behavior_group)
        
        # Error handling group
        error_group = QGroupBox("Error Handling")
        error_layout = QVBoxLayout(error_group)
        
        self.auto_queue_check = QCheckBox("Auto-queue failed submissions for retry")
        self.auto_queue_check.setToolTip("Automatically add failed submissions to retry queue")
        error_layout.addWidget(self.auto_queue_check)
        
        self.notify_errors_check = QCheckBox("Show error notifications")
        self.notify_errors_check.setToolTip("Display popup notifications for validation errors")
        error_layout.addWidget(self.notify_errors_check)
        
        self.save_error_logs_check = QCheckBox("Save detailed error logs")
        self.save_error_logs_check.setToolTip("Keep detailed logs of all validation errors")
        error_layout.addWidget(self.save_error_logs_check)
        
        layout.addWidget(error_group)
        
        # Default values group
        defaults_group = QGroupBox("Default Values")
        defaults_layout = QFormLayout(defaults_group)
        
        self.default_mode_combo = QComboBox()
        self.default_mode_combo.addItems(["sandbox", "production"])
        defaults_layout.addRow("Default Mode:", self.default_mode_combo)
        
        self.sandbox_scenario_edit = QLineEdit()
        self.sandbox_scenario_edit.setPlaceholderText("SN001")
        defaults_layout.addRow("Sandbox Scenario ID:", self.sandbox_scenario_edit)
        
        layout.addWidget(defaults_group)
        
        layout.addStretch()
        
        return widget

    def create_queue_settings_tab(self):
        """Create queue settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Queue behavior group
        queue_group = QGroupBox("Queue Management")
        queue_layout = QFormLayout(queue_group)
        
        self.queue_batch_size_spin = QSpinBox()
        self.queue_batch_size_spin.setRange(1, 100)
        self.queue_batch_size_spin.setValue(10)
        queue_layout.addRow("Batch Size:", self.queue_batch_size_spin)
        
        self.queue_interval_spin = QSpinBox()
        self.queue_interval_spin.setRange(5, 300)
        self.queue_interval_spin.setSuffix(" seconds")
        self.queue_interval_spin.setValue(30)
        queue_layout.addRow("Processing Interval:", self.queue_interval_spin)
        
        self.max_queue_retries_spin = QSpinBox()
        self.max_queue_retries_spin.setRange(1, 20)
        self.max_queue_retries_spin.setValue(5)
        queue_layout.addRow("Max Queue Retries:", self.max_queue_retries_spin)
        
        layout.addWidget(queue_group)
        
        # Priority settings
        priority_group = QGroupBox("Priority Settings")
        priority_layout = QFormLayout(priority_group)
        
        self.high_priority_combo = QComboBox()
        self.high_priority_combo.addItems(["Urgent invoices", "Large amounts", "VIP customers"])
        priority_layout.addRow("High Priority:", self.high_priority_combo)
        
        self.retry_delay_spin = QSpinBox()
        self.retry_delay_spin.setRange(1, 60)
        self.retry_delay_spin.setSuffix(" minutes")
        self.retry_delay_spin.setValue(5)
        priority_layout.addRow("Retry Delay:", self.retry_delay_spin)
        
        layout.addWidget(priority_group)
        
        # Cleanup settings
        cleanup_group = QGroupBox("Queue Cleanup")
        cleanup_layout = QFormLayout(cleanup_group)
        
        self.auto_cleanup_check = QCheckBox("Auto-cleanup completed items")
        cleanup_layout.addRow("", self.auto_cleanup_check)
        
        self.cleanup_days_spin = QSpinBox()
        self.cleanup_days_spin.setRange(1, 365)
        self.cleanup_days_spin.setSuffix(" days")
        self.cleanup_days_spin.setValue(30)
        cleanup_layout.addRow("Keep completed items for:", self.cleanup_days_spin)
        
        layout.addWidget(cleanup_group)
        
        layout.addStretch()
        
        return widget

    def create_advanced_settings_tab(self):
        """Create advanced settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Performance group
        performance_group = QGroupBox("Performance")
        performance_layout = QFormLayout(performance_group)
        
        self.bulk_submission_check = QCheckBox("Enable bulk submission")
        performance_layout.addRow("", self.bulk_submission_check)
        
        self.cache_api_data_check = QCheckBox("Cache API data")
        performance_layout.addRow("", self.cache_api_data_check)
        
        self.parallel_processing_check = QCheckBox("Enable parallel processing")
        performance_layout.addRow("", self.parallel_processing_check)
        
        layout.addWidget(performance_group)
        
        # Logging group
        logging_group = QGroupBox("Logging & Auditing")
        logging_layout = QFormLayout(logging_group)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level_combo.setCurrentText("INFO")
        logging_layout.addRow("Log Level:", self.log_level_combo)
        
        self.log_retention_spin = QSpinBox()
        self.log_retention_spin.setRange(30, 365)
        self.log_retention_spin.setSuffix(" days")
        self.log_retention_spin.setValue(90)
        logging_layout.addRow("Log Retention:", self.log_retention_spin)
        
        self.detailed_api_logs_check = QCheckBox("Detailed API logs")
        logging_layout.addRow("", self.detailed_api_logs_check)
        
        layout.addWidget(logging_group)
        
        # Security group
        security_group = QGroupBox("Security")
        security_layout = QVBoxLayout(security_group)
        
        self.encrypt_data_check = QCheckBox("Encrypt sensitive data in database")
        security_layout.addWidget(self.encrypt_data_check)
        
        self.secure_connection_check = QCheckBox("Force secure connections (HTTPS)")
        security_layout.addWidget(self.secure_connection_check)
        
        self.audit_trail_check = QCheckBox("Enable audit trail")
        security_layout.addWidget(self.audit_trail_check)
        
        layout.addWidget(security_group)
        
        # Custom settings
        custom_group = QGroupBox("Custom Configuration")
        custom_layout = QVBoxLayout(custom_group)
        
        custom_label = QLabel("Custom JSON Configuration (Advanced users only):")
        custom_layout.addWidget(custom_label)
        
        self.custom_config_edit = QTextEdit()
        self.custom_config_edit.setMaximumHeight(150)
        self.custom_config_edit.setPlaceholderText('{"custom_setting": "value"}')
        custom_layout.addWidget(self.custom_config_edit)
        
        layout.addWidget(custom_group)
        
        layout.addStretch()
        
        return widget

    def toggle_token_visibility(self):
        """Toggle authorization token visibility"""
        if self.auth_token_edit.echoMode() == QLineEdit.EchoMode.Password:
            self.auth_token_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_token_btn.setText("🙈")
        else:
            self.auth_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_token_btn.setText("👁️")

    def test_connection(self):
        """Test FBR API connection"""
        endpoint = self.api_endpoint_edit.text().strip()
        token = self.auth_token_edit.text().strip()
        
        if not endpoint or not token:
            QMessageBox.warning(
                self, "Validation Error",
                "Please enter both API endpoint and authorization token before testing connection."
            )
            return
        
        # Show progress
        self.test_connection_btn.setEnabled(False)
        self.test_progress.setVisible(True)
        self.connection_status_label.setText("Testing connection...")
        self.connection_status_label.setStyleSheet("color: #ffc107;")
        
        # Start test thread
        self.test_thread = TestConnectionThread(endpoint, token)
        self.test_thread.connection_tested.connect(self.on_connection_tested)
        self.test_thread.start()

    def on_connection_tested(self, success, message):
        """Handle connection test results"""
        self.test_connection_btn.setEnabled(True)
        self.test_progress.setVisible(False)
        
        self.connection_status_label.setText(message)
        
        if success:
            self.connection_status_label.setStyleSheet("color: #28a745; font-weight: bold;")
        else:
            self.connection_status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        
        # Auto-clear status after 10 seconds
        QTimer.singleShot(10000, lambda: self.connection_status_label.setText(""))

    def load_settings(self):
        """Load settings from database"""
        try:
            session = self.db_manager.get_session()
            settings = session.query(FBRSettings).filter_by(company_id=self.company_id).first()
            
            if settings:
                # API Settings
                self.api_endpoint_edit.setText(settings.api_endpoint or "")
                self.validation_endpoint_edit.setText(settings.validation_endpoint or "")
                self.auth_token_edit.setText(settings.pral_authorization_token or "")
                self.login_id_edit.setText(settings.pral_login_id or "")
                self.login_password_edit.setText(settings.pral_login_password or "")
                self.timeout_spin.setValue(settings.timeout_seconds or 30)
                self.max_retries_spin.setValue(settings.max_retries or 3)
                
                # Validation Settings
                self.auto_validate_check.setChecked(settings.auto_validate_before_submit or False)
                self.auto_queue_check.setChecked(settings.auto_queue_on_failure or False)
                self.default_mode_combo.setCurrentText(settings.default_mode or "sandbox")
                self.sandbox_scenario_edit.setText(settings.sandbox_scenario_id or "SN001")
                
                # Advanced Settings
                self.bulk_submission_check.setChecked(settings.bulk_submission_enabled or False)
                
            else:
                # Load default values
                self.reset_to_defaults()
                
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load settings: {str(e)}")

    def save_settings(self):
        """Save settings to database"""
        try:
            # Validate required fields
            if not self.auth_token_edit.text().strip():
                QMessageBox.warning(
                    self, "Validation Error",
                    "Authorization Token is required. Please enter your PRAL token."
                )
                return
            
            session = self.db_manager.get_session()
            
            # Get existing settings or create new
            settings = session.query(FBRSettings).filter_by(company_id=self.company_id).first()
            if not settings:
                settings = FBRSettings(company_id=self.company_id)
                session.add(settings)
            
            # Update API settings
            settings.api_endpoint = self.api_endpoint_edit.text().strip()
            settings.validation_endpoint = self.validation_endpoint_edit.text().strip()
            settings.pral_authorization_token = self.auth_token_edit.text().strip()
            settings.pral_login_id = self.login_id_edit.text().strip()
            settings.pral_login_password = self.login_password_edit.text().strip()
            settings.timeout_seconds = self.timeout_spin.value()
            settings.max_retries = self.max_retries_spin.value()
            
            # Update validation settings
            settings.auto_validate_before_submit = self.auto_validate_check.isChecked()
            settings.auto_queue_on_failure = self.auto_queue_check.isChecked()
            settings.default_mode = self.default_mode_combo.currentText()
            settings.sandbox_scenario_id = self.sandbox_scenario_edit.text().strip()
            
            # Update advanced settings
            settings.bulk_submission_enabled = self.bulk_submission_check.isChecked()
            settings.updated_at = datetime.now()
            
            session.commit()
            
            QMessageBox.information(
                self, "Success",
                f"Settings saved successfully for {self.company_data['name']}!"
            )
            
            self.settings_saved.emit()
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save settings: {str(e)}")

    def reset_to_defaults(self):
        """Reset all settings to default values"""
        reply = QMessageBox.question(
            self, "Confirm Reset",
            "Are you sure you want to reset all settings to defaults?\n\nThis will overwrite your current configuration.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Default API settings
            self.api_endpoint_edit.setText("https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata_sb")
            self.validation_endpoint_edit.setText("https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata_sb")
            self.auth_token_edit.clear()
            self.login_id_edit.clear()
            self.login_password_edit.clear()
            self.timeout_spin.setValue(30)
            self.max_retries_spin.setValue(3)
            
            # Default validation settings
            self.auto_validate_check.setChecked(True)
            self.auto_queue_check.setChecked(True)
            self.strict_validation_check.setChecked(False)
            self.validate_hs_codes_check.setChecked(True)
            self.notify_errors_check.setChecked(True)
            self.save_error_logs_check.setChecked(True)
            self.default_mode_combo.setCurrentText("sandbox")
            self.sandbox_scenario_edit.setText("SN001")
            
            # Default queue settings
            self.queue_batch_size_spin.setValue(10)
            self.queue_interval_spin.setValue(30)
            self.max_queue_retries_spin.setValue(5)
            self.retry_delay_spin.setValue(5)
            self.auto_cleanup_check.setChecked(True)
            self.cleanup_days_spin.setValue(30)
            
            # Default advanced settings
            self.bulk_submission_check.setChecked(False)
            self.cache_api_data_check.setChecked(True)
            self.parallel_processing_check.setChecked(False)
            self.log_level_combo.setCurrentText("INFO")
            self.log_retention_spin.setValue(90)
            self.detailed_api_logs_check.setChecked(False)
            self.encrypt_data_check.setChecked(True)
            self.secure_connection_check.setChecked(True)
            self.audit_trail_check.setChecked(True)
            self.custom_config_edit.clear()

    def export_settings(self):
        """Export settings to JSON file"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Settings",
                f"fbr_settings_{self.company_id}_{datetime.now().strftime('%Y%m%d')}.json",
                "JSON files (*.json);;All files (*.*)"
            )
            
            if filename:
                settings_data = {
                    "company_id": self.company_id,
                    "company_name": self.company_data['name'],
                    "export_date": datetime.now().isoformat(),
                    "api_endpoint": self.api_endpoint_edit.text(),
                    "validation_endpoint": self.validation_endpoint_edit.text(),
                    "login_id": self.login_id_edit.text(),
                    "timeout_seconds": self.timeout_spin.value(),
                    "max_retries": self.max_retries_spin.value(),
                    "auto_validate_before_submit": self.auto_validate_check.isChecked(),
                    "auto_queue_on_failure": self.auto_queue_check.isChecked(),
                    "default_mode": self.default_mode_combo.currentText(),
                    "sandbox_scenario_id": self.sandbox_scenario_edit.text(),
                    "bulk_submission_enabled": self.bulk_submission_check.isChecked()
                    # Note: We don't export sensitive data like tokens and passwords
                }
                
                import json
                with open(filename, 'w') as f:
                    json.dump(settings_data, f, indent=2)
                
                QMessageBox.information(
                    self, "Export Successful",
                    f"Settings exported successfully to:\n{filename}\n\n"
                    "Note: Sensitive data (tokens, passwords) are not included in the export for security."
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export settings: {str(e)}")

    def import_settings(self):
        """Import settings from JSON file"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Import Settings",
                "",
                "JSON files (*.json);;All files (*.*)"
            )
            
            if filename:
                import json
                with open(filename, 'r') as f:
                    settings_data = json.load(f)
                
                # Validate the file
                if "company_id" not in settings_data:
                    QMessageBox.warning(self, "Invalid File", "This doesn't appear to be a valid FBR settings file.")
                    return
                
                reply = QMessageBox.question(
                    self, "Confirm Import",
                    f"Import settings from:\n{filename}\n\n"
                    f"Exported for: {settings_data.get('company_name', 'Unknown')}\n"
                    f"Export date: {settings_data.get('export_date', 'Unknown')}\n\n"
                    "This will overwrite your current settings (except sensitive data).",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    # Import non-sensitive settings
                    self.api_endpoint_edit.setText(settings_data.get("api_endpoint", ""))
                    self.validation_endpoint_edit.setText(settings_data.get("validation_endpoint", ""))
                    self.login_id_edit.setText(settings_data.get("login_id", ""))
                    self.timeout_spin.setValue(settings_data.get("timeout_seconds", 30))
                    self.max_retries_spin.setValue(settings_data.get("max_retries", 3))
                    self.auto_validate_check.setChecked(settings_data.get("auto_validate_before_submit", True))
                    self.auto_queue_check.setChecked(settings_data.get("auto_queue_on_failure", True))
                    self.default_mode_combo.setCurrentText(settings_data.get("default_mode", "sandbox"))
                    self.sandbox_scenario_edit.setText(settings_data.get("sandbox_scenario_id", "SN001"))
                    self.bulk_submission_check.setChecked(settings_data.get("bulk_submission_enabled", False))
                    
                    QMessageBox.information(
                        self, "Import Successful",
                        "Settings imported successfully!\n\n"
                        "Note: You'll need to re-enter sensitive data (tokens, passwords)."
                    )
                
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import settings: {str(e)}")


# Test the dialog
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Mock data for testing
    class MockDBManager:
        def get_session(self):
            return None
    
    company_data = {
        'ntn_cnic': '1234567890123',
        'name': 'Test Company Ltd'
    }
    
    dialog = FBRSettingsDialog(MockDBManager(), company_data)
    result = dialog.exec()
    
    sys.exit(app.exec())