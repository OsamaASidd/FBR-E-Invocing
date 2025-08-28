# setup_neon_database.py
"""
Script to initialize your Neon PostgreSQL database with the required tables and data.
Run this once to set up your database schema and initial data.
"""

import sqlalchemy as sa
from sqlalchemy import create_engine, text
from fbr_core.models import Base, Company, Customer, Item
from fbr_core.models import SalesInvoice, FBRQueue, FBRLogs, FBRSettings
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Your Neon PostgreSQL connection
DATABASE_URL = "postgresql://neondb_owner:npg_H2hByXAgPz8n@ep-sparkling-shape-adwmth20-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def setup_database():
    """Initialize the database with tables and sample data"""
    
    print("🚀 Setting up Neon PostgreSQL database...")
    
    try:
        # Create engine with PostgreSQL-specific settings
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,   # Recycle connections after 1 hour
            echo=True            # Show SQL queries (set to False in production)
        )
        
        print("✅ Connected to Neon PostgreSQL database")
        
        # Create all tables
        print("📋 Creating database tables...")
        Base.metadata.create_all(engine)
        print("✅ All tables created successfully")
        
        # Create session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Add provinces
        print("🌍 Adding provinces...")
        provinces_data = [
            "Punjab", "Sindh", "Khyber Pakhtunkhwa", "Balochistan",
            "Gilgit-Baltistan", "Azad Kashmir", "Islamabad Capital Territory"
        ]
        
        # Insert provinces using raw SQL to handle conflicts
        for province in provinces_data:
            result = session.execute(
                text("SELECT COUNT(*) FROM provinces WHERE name = :name"),
                {"name": province}
            )
            if result.scalar() == 0:
                session.execute(
                    text("INSERT INTO provinces (name) VALUES (:name)"),
                    {"name": province}
                )
        
        # Add sample HS codes
        print("📦 Adding HS Codes...")
        hs_codes = [
            "1001", "1002", "1003", "1004", "1005",  # Agricultural products
            "8471", "8542",  # Electronics
            "9999"  # General/Other
        ]
        
        for hs_code in hs_codes:
            result = session.execute(
                text("SELECT COUNT(*) FROM hs_codes WHERE code_number = :code"),
                {"code": hs_code}
            )
            if result.scalar() == 0:
                session.execute(
                    text("INSERT INTO hs_codes (code_number) VALUES (:code)"),
                    {"code": hs_code}
                )
        
        # Add default company
        print("🏢 Adding default company...")
        default_company = Company(
            name="Your Company Name",
            tax_id="1234567890123",  # Update with your actual NTN
            province="Punjab",  # Update with your province
            address="Your Company Address",  # Update with actual address
            created_at=datetime.utcnow()
        )
        
        # Check if company already exists
        existing_company = session.query(Company).filter_by(name="Your Company Name").first()
        if not existing_company:
            session.add(default_company)
        
        # Add sample customer
        print("👤 Adding sample customer...")
        sample_customer = Customer(
            name="Sample Customer",
            tax_id="9876543210987",
            province="Sindh",
            address="Customer Address, Karachi",
            created_at=datetime.utcnow()
        )
        
        existing_customer = session.query(Customer).filter_by(name="Sample Customer").first()
        if not existing_customer:
            session.add(sample_customer)
        
        # Add sample items
        print("📋 Adding sample items...")
        sample_items = [
            {"code": "ITEM001", "name": "Sample Product 1", "hs_code": "9999", "uom": "Nos", "rate": 100.00},
            {"code": "ITEM002", "name": "Sample Product 2", "hs_code": "9999", "uom": "Kg", "rate": 50.00},
            {"code": "SERV001", "name": "Sample Service", "hs_code": "9999", "uom": "Hrs", "rate": 1000.00}
        ]
        
        for item_data in sample_items:
            existing_item = session.query(Item).filter_by(code=item_data["code"]).first()
            if not existing_item:
                item = Item(
                    code=item_data["code"],
                    name=item_data["name"],
                    hs_code=item_data["hs_code"],
                    uom=item_data["uom"],
                    rate=item_data["rate"],
                    created_at=datetime.utcnow()
                )
                session.add(item)
        
        # Add FBR settings
        print("⚙️  Adding FBR settings...")
        fbr_settings = FBRSettings(
            api_endpoint="https://api.fbr.gov.pk/einvoicing",  # Update with actual endpoint
            pral_authorization_token="",  # Add your token
            pral_login_id="",  # Add your login ID
            pral_login_password="",  # Add your password
            updated_at=datetime.utcnow()
        )
        
        existing_settings = session.query(FBRSettings).first()
        if not existing_settings:
            session.add(fbr_settings)
        
        # Commit all changes
        session.commit()
        print("✅ Database setup completed successfully!")
        
        # Display summary
        print("\n📊 Database Summary:")
        print(f"   • Companies: {session.query(Company).count()}")
        print(f"   • Customers: {session.query(Customer).count()}")
        print(f"   • Items: {session.query(Item).count()}")
        print(f"   • Invoices: {session.query(SalesInvoice).count()}")
        print(f"   • Queue Items: {session.query(FBRQueue).count()}")
        print(f"   • Logs: {session.query(FBRLogs).count()}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        raise

def test_connection():
    """Test database connection"""
    print("🔍 Testing database connection...")
    
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected successfully!")
            print(f"   PostgreSQL Version: {version}")
            
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

def reset_database():
    """Reset database (drops all tables) - Use with caution!"""
    print("⚠️  WARNING: This will delete all data!")
    confirm = input("Type 'YES' to confirm database reset: ")
    
    if confirm == "YES":
        try:
            engine = create_engine(DATABASE_URL)
            Base.metadata.drop_all(engine)
            print("✅ Database reset completed")
            
        except Exception as e:
            print(f"❌ Database reset failed: {str(e)}")
    else:
        print("Database reset cancelled")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            test_connection()
        elif command == "reset":
            reset_database()
        elif command == "setup":
            setup_database()
        else:
            print("Usage: python setup_neon_database.py [test|setup|reset]")
    else:
        # Default action
        print("FBR Invoicing - Neon Database Setup")
        print("===================================")
        
        if test_connection():
            setup_database()
            print("\n🎉 Your database is ready to use!")
            print("\nNext steps:")
            print("1. Update company information in the app settings")
            print("2. Add your FBR API credentials")
            print("3. Start creating invoices!")
        else:
            print("\n❌ Please check your database connection and try again.")

# Additional utility functions

def backup_database_to_file(filename=None):
    """Create a backup of the database"""
    if not filename:
        filename = f"fbr_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    import subprocess
    import os
    
    # Parse connection URL for pg_dump
    env = os.environ.copy()
    env['PGPASSWORD'] = 'npg_H2hByXAgPz8n'
    
    try:
        subprocess.run([
            'pg_dump',
            '-h', 'ep-sparkling-shape-adwmth20-pooler.c-2.us-east-1.aws.neon.tech',
            '-U', 'neondb_owner',
            '-d', 'neondb',
            '-f', filename,
            '--no-password'
        ], env=env, check=True)
        
        print(f"✅ Backup created: {filename}")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Backup failed: {str(e)}")
    except FileNotFoundError:
        print("❌ pg_dump not found. Please install PostgreSQL client tools.")

def get_database_info():
    """Get information about the database"""
    try:
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Get table information
        inspector = sa.inspect(engine)
        tables = inspector.get_table_names()
        
        print("📊 Database Information:")
        print(f"   • Database: neondb")
        print(f"   • Tables: {len(tables)}")
        
        for table in tables:
            try:
                count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"   • {table}: {count} records")
            except:
                print(f"   • {table}: Unable to count records")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Could not retrieve database info: {str(e)}")

# Command line interface
if __name__ == "__main__":
    # You can run specific commands like:
    # python setup_neon_database.py test
    # python setup_neon_database.py setup
    # python setup_neon_database.py reset
    pass