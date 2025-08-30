import configparser
import os
import sys
from typing import Any


class AppConfig:
    """Application configuration manager"""

    def __init__(self, config_file: str = None):
        self.config = configparser.ConfigParser()
        self.config_file = config_file or self._get_default_config_file()
        self.load_config()

    def _get_default_config_file(self) -> str:
        """Get default configuration file path"""
        if hasattr(sys, "_MEIPASS"):  # Running as PyInstaller bundle
            return os.path.join(sys._MEIPASS, "config", "app_config.ini")
        else:
            return os.path.join("config", "app_config.ini")

    def load_config(self):
        """Load configuration from file"""
        try:
            self.config.read(self.config_file)
        except Exception as e:
            print(f"Error loading config: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """Create default configuration"""
        self.config["DATABASE"] = {
            "url": (
                "postgresql://neondb_owner:npg_H2hByXAgPz8n@ep-sparkling-shape-"
                "adwmth20-pooler.c-2.us-east-1.aws.neon.tech/neondb?"
                "sslmode=require&channel_binding=require"
            ),
            "pool_size": "10",
            "max_overflow": "20",
            "pool_pre_ping": "true",
            "pool_recycle": "3600",
        }

        self.config["FBR_API"] = {
            "endpoint": "https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata_sb",
            "authorization_token": "e8882e63-ca03-3174-8e19-f9e609f2a418",
            "login_id": "",
            "login_password": "",
            "timeout": "30",
            "max_retries": "4",
        }

        self.config["APPLICATION"] = {
            "auto_refresh_interval": "30",
            "queue_process_limit": "50",
            "log_retention_days": "90",
            "backup_enabled": "true",
            "debug_mode": "false",
        }

        self.save_config()

    def save_config(self):
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, "w") as f:
                self.config.write(f)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, section: str, key: str, fallback: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(section, key, fallback=fallback)

    def set(self, section: str, key: str, value: str):
        """Set configuration value"""
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, key, value)

    def get_database_url(self) -> str:
        """Get database connection URL"""
        return self.get(
            "DATABASE",
            "url",
            (
                "postgresql://neondb_owner:npg_H2hByXAgPz8n@ep-sparkling-shape-"
                "adwmth20-pooler.c-2.us-east-1.aws.neon.tech/neondb?"
                "sslmode=require&channel_binding=require"
            ),
        )


def load_configuration(config_file: str = None) -> AppConfig:
    """Load application configuration"""
    return AppConfig(config_file)
