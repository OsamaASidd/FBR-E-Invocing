# 1. Install Python 3.8+ and MySQL
# 2. Clone/extract the project
# 3. Create virtual environment:
python -m venv venv
venv\Scripts\activate

# 4. Install dependencies:
pip install -r requirements.txt

# 5. Setup MySQL database:
mysql -u root -p
CREATE DATABASE fbr_invoicing;
# Import init_data.sql

# 6. Update database configuration in config/app_config.ini

# 7. Test the application:
python main.py

# 8. Build executable:
python build_exe.py

# The executable will be created in dist/ folder