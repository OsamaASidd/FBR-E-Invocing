from setuptools import setup, find_packages

setup(
    name="fbr-invoicing-app",
    version="1.0.0",
    description="FBR E-Invoicing Desktop Application",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "PyQt6>=6.6.0",
        "SQLAlchemy>=2.0.0",
        "psycopg2-binary>=2.9.0",
        "requests>=2.31.0",
        "cryptography>=41.0.0",
        "python-dateutil>=2.8.0",
    ],
    entry_points={
        "console_scripts": [
            "fbr-invoicing=main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "resources": ["icons/*", "styles/*", "database/*"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Office/Business :: Financial :: Accounting",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
