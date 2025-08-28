#!/usr/bin/env python3
import sys
import os
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fbr_invoicing.log'),
        logging.StreamHandler()
    ]
)

def main():
    """Main application entry point"""
    try:
        from PyQt6.QtWidgets import QApplication
        from gui.main_window import MainWindow
        from fbr_core.config import load_configuration
        
        # Load configuration
        config = load_configuration()
        
        # Create QApplication
        app = QApplication(sys.argv)
        app.setApplicationName("FBR E-Invoicing System")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("Your Company")
        
        # Set application style
        try:
            with open('resources/styles/application.qss', 'r') as f:
                app.setStyleSheet(f.read())
        except FileNotFoundError:
            logging.warning("Application stylesheet not found")
        
        # Create and show main window
        window = MainWindow(config)
        window.show()
        
        # Run the application
        sys.exit(app.exec())
        
    except Exception as e:
        logging.error(f"Application startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()