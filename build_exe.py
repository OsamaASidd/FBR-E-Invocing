import PyInstaller.__main__
import os
import sys

def build_executable():
    """Build Windows executable using PyInstaller"""
    
    # PyInstaller options
    options = [
        '--name=FBR_Invoicing',  # Executable name
        '--onefile',             # Single executable file
        '--windowed',            # Hide console window
        # '--icon=resources/icons/app_icon.ico',  # Application icon (commented out due to format issue)
        
        # Include additional files
        '--add-data=resources;resources',
        '--add-data=config;config',
        
        # Hidden imports (modules not automatically detected)
        '--hidden-import=PyQt6.sip',
        '--hidden-import=psycopg2',
        '--hidden-import=sqlalchemy.dialects.postgresql',
        '--hidden-import=sqlalchemy.pool',
        
        # Exclude unnecessary modules to reduce size
        '--exclude-module=matplotlib',
        '--exclude-module=numpy',
        '--exclude-module=pandas',
        '--exclude-module=scipy',
        
        # Main script
        'main.py'
    ]
    
    # Run PyInstaller
    PyInstaller.__main__.run(options)

if __name__ == "__main__":
    build_executable()