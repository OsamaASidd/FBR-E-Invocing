# setup_company_database.py
"""
Updated script to initialize your Neon PostgreSQL database with company-specific structure.
Run this to set up your database schema and create sample company data.
"""

import sys
from pathlib import Path
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fbr_core.models import Base, Company, Buyer, Item, FBRSettings, Invoices, SalesInvoiceItem

# Your Neon PostgreSQL connection
DATABASE_URL = "postgresql://neondb_owner:npg_H2hByXAgPz8n@ep-sparkling-shape-adwmth20-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def setup_database():
    """Initialize the database with tables and sample company data"""
    
    print("🚀 Setting up Company-Specific FBR E-Invoicing Database...")
    
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
        
        # Create sample companies
        print("🏢 Creating sample companies...")
        companies_created = create_sample_companies(session)
        
        print(f"✅ Created {companies_created} sample companies")
        
        # Commit all changes
        session.commit()
        session.close()
        
        print("✅ Database setup completed successfully!")
        print("\n📊 Database Summary:")
        show_database_summary(engine)
                
    except Exception as e:
        print(f"❌ Database setup failed: {str(e)}")
        raise


def create_sample_companies(session):
    """Create sample companies with complete data"""
    companies_data = [
        {
            'ntn_cnic': '1234567890123',
            'name': 'Tech Solutions (Pvt) Ltd',
            'address': 'Plot 123, Block A, Karachi Technology Park, Karachi',
            'province': 'Sindh',
            'city': 'Karachi',
            'phone': '+92-21-1234567',
            'email': 'info@techsolutions.com.pk',
            'contact_person': 'Ahmed Ali',
            'business_type': 'Information Technology',
            'registration_date': datetime(2020, 1, 15)
        },
        {
            'ntn_cnic': '2345678901234',
            'name': 'Global Trading Company',
            'address': '45 Mall Road, Gulberg III, Lahore',
            'province': 'Punjab',
            'city': 'Lahore', 
            'phone': '+92-42-9876543',
            'email': 'contact@globaltrading.pk',
            'contact_person': 'Sarah Khan',
            'business_type': 'Import/Export',
            'registration_date': datetime(2019, 6, 10)
        },
        {
            'ntn_cnic': '3456789012345',
            'name': 'Manufacturing Industries Ltd',
            'address': 'Industrial Area, Phase II, Islamabad',
            'province': 'Islamabad Capital Territory',
            'city': 'Islamabad',
            'phone': '+92-51-5555555',
            'email': 'admin@manufacturing.com.pk',
            'contact_person': 'Muhammad Hassan',
            'business_type': 'Manufacturing',
            'registration_date': datetime(2018, 3, 22)
        }
    ]
    
    companies_created = 0
    
    for company_data in companies_data:
        # Check if company already exists
        existing_company = session.query(Company).filter_by(
            ntn_cnic=company_data['ntn_cnic']
        ).first()
        
        if existing_company:
            print(f"   📌 Company {company_data['name']} already exists, skipping...")
            continue
        
        # Create company
        company = Company(**company_data)
        session.add(company)
        session.flush()  # Get the company ID
        
        print(f"   ✅ Created company: {company.name}")
        
        # Create FBR settings for company
        create_company_fbr_settings(session, company.ntn_cnic)
        
        # Create sample items for company
        create_sample_items(session, company.ntn_cnic, company.business_type)
        
        # Create sample buyers for company
        create_sample_buyers(session, company.ntn_cnic)
        
        # Create sample invoices for company (optional)
        create_sample_invoices(session, company.ntn_cnic)
        
        companies_created += 1
    
    return companies_created


def create_company_fbr_settings(session, company_id):
    """Create FBR settings for a company"""
    fbr_settings = FBRSettings(
        company_id=company_id,
        api_endpoint="https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata_sb",
        validation_endpoint="https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata_sb",
        pral_authorization_token="e8882e63-ca03-3174-8e19-f9e609f2a418",  # Sample token
        pral_login_id="",
        pral_login_password="",
        timeout_seconds=30,
        max_retries=3,
        default_mode="sandbox",
        sandbox_scenario_id="SN001",
        auto_validate_before_submit=True,
        auto_queue_on_failure=True
    )
    
    session.add(fbr_settings)
    print(f"   📋 Created FBR settings for company {company_id}")


def create_sample_items(session, company_id, business_type):
    """Create sample items based on business type"""
    
    items_by_business_type = {
        'Information Technology': [
            {
                'name': 'Software Development Services',
                'description': 'Custom software development and programming services',
                'hs_code': '8542.3100',
                'uom': 'Hours',
                'category': 'Services',
                'standard_rate': 5000.0,
                'tax_rate': 16.0
            },
            {
                'name': 'IT Consultation',
                'description': 'Technology consulting and advisory services',
                'hs_code': '9999.0000',
                'uom': 'Hours',
                'category': 'Services',
                'standard_rate': 7500.0,
                'tax_rate': 16.0
            },
            {
                'name': 'Computer Hardware',
                'description': 'Desktop computers and accessories',
                'hs_code': '8471.3000',
                'uom': 'Numbers, pieces, units',
                'category': 'Products',
                'standard_rate': 125000.0,
                'tax_rate': 18.0
            }
        ],
        'Import/Export': [
            {
                'name': 'Import Services',
                'description': 'Import handling and clearance services',
                'hs_code': '9999.0000',
                'uom': 'Numbers, pieces, units',
                'category': 'Services',
                'standard_rate': 25000.0,
                'tax_rate': 16.0
            },
            {
                'name': 'Export Services',
                'description': 'Export documentation and shipping services',
                'hs_code': '9999.0000',
                'uom': 'Numbers, pieces, units',
                'category': 'Services',
                'standard_rate': 30000.0,
                'tax_rate': 16.0
            },
            {
                'name': 'Logistics Services',
                'description': 'Transportation and logistics management',
                'hs_code': '9999.0000',
                'uom': 'Numbers, pieces, units',
                'category': 'Services',
                'standard_rate': 15000.0,
                'tax_rate': 16.0
            }
        ],
        'Manufacturing': [
            {
                'name': 'Manufactured Goods',
                'description': 'Custom manufactured products',
                'hs_code': '8542.3100',
                'uom': 'Numbers, pieces, units',
                'category': 'Products',
                'standard_rate': 45000.0,
                'tax_rate': 17.0
            },
            {
                'name': 'Raw Materials',
                'description': 'Industrial raw materials and components',
                'hs_code': '1001.1900',
                'uom': 'Kg',
                'category': 'Materials',
                'standard_rate': 850.0,
                'tax_rate': 18.0
            },
            {
                'name': 'Manufacturing Services',
                'description': 'Contract manufacturing services',
                'hs_code': '9999.0000',
                'uom': 'Hours',
                'category': 'Services',
                'standard_rate': 3500.0,
                'tax_rate': 16.0
            }
        ]
    }
    
    # Get items for this business type, or use generic items
    items_data = items_by_business_type.get(business_type, items_by_business_type['Information Technology'])
    
    for item_data in items_data:
        item = Item(
            company_id=company_id,
            **item_data
        )
        session.add(item)
    
    print(f"   📦 Created {len(items_data)} sample items for {business_type}")


def create_sample_buyers(session, company_id):
    """Create sample buyers for a company"""
    
    buyers_data = [
        {
            'ntn_cnic': '1111111111111',
            'name': 'ABC Corporation',
            'address': 'Business District, Karachi',
            'province': 'Sindh',
            'city': 'Karachi',
            'phone': '+92-21-1111111',
            'email': 'finance@abccorp.com',
            'buyer_type': 'Registered'
        },
        {
            'ntn_cnic': '2222222222222',
            'name': 'XYZ Industries',
            'address': 'Industrial Zone, Lahore',
            'province': 'Punjab',
            'city': 'Lahore',
            'phone': '+92-42-2222222',
            'email': 'accounts@xyzind.com',
            'buyer_type': 'Registered'
        },
        {
            'ntn_cnic': '3333333333333',
            'name': 'Individual Customer',
            'address': 'Residential Area, Islamabad',
            'province': 'Islamabad Capital Territory',
            'city': 'Islamabad',
            'phone': '+92-51-3333333',
            'buyer_type': 'Unregistered'
        }
    ]
    
    for buyer_data in buyers_data:
        # Check if buyer already exists for this company
        existing_buyer = session.query(Buyer).filter_by(
            company_id=company_id,
            ntn_cnic=buyer_data['ntn_cnic']
        ).first()
        
        if not existing_buyer:
            buyer = Buyer(
                company_id=company_id,
                **buyer_data
            )
            session.add(buyer)
    
    print(f"   👥 Created sample buyers for company {company_id}")


def create_sample_invoices(session, company_id):
    """Create sample invoices for demonstration"""
    
    # Get company items and buyers
    items = session.query(Item).filter_by(company_id=company_id).limit(2).all()
    buyers = session.query(Buyer).filter_by(company_id=company_id).limit(2).all()
    
    if not items or not buyers:
        print(f"   ⚠️  Skipping sample invoices - no items or buyers available")
        return
    
    # Create 2 sample invoices
    for i in range(2):
        buyer = buyers[i % len(buyers)]
        
        # Generate invoice number
        invoice_number = f"INV-{company_id[-3:]}-{datetime.now().strftime('%Y%m')}-{(i+1):03d}"
        
        # Calculate dates
        posting_date = datetime.now() - timedelta(days=i*7)
        due_date = posting_date + timedelta(days=30)
        
        # Create invoice
        invoice = Invoices(
            company_id=company_id,
            buyer_id=buyer.id,
            invoice_number=invoice_number,
            invoice_type="Sale Invoice",
            posting_date=posting_date,
            due_date=due_date,
            
            # Buyer details
            buyer_ntn_cnic=buyer.ntn_cnic,
            buyer_name=buyer.name,
            buyer_address=buyer.address,
            buyer_province=buyer.province,
            buyer_type=buyer.buyer_type,
            
            # Transaction details
            transaction_type="Goods at standard rate (default)",
            sale_origination_province="Sindh",
            destination_supply_province=buyer.province,
            
            status="Draft",
            fbr_status=None
        )
        
        session.add(invoice)
        session.flush()  # Get invoice ID
        
        # Add invoice items
        total_amount = 0
        total_tax = 0
        
        for j, item in enumerate(items[:2]):  # Add up to 2 items per invoice
            quantity = 1.0 + j
            unit_price = item.standard_rate or 1000.0
            total_value = quantity * unit_price
            tax_amount = (total_value * item.tax_rate) / 100
            
            invoice_item = SalesInvoiceItem(
                invoice_id=invoice.id,
                item_id=item.id,
                item_name=item.name,
                item_description=item.description,
                hs_code=item.hs_code,
                uom=item.uom,
                quantity=quantity,
                unit_price=unit_price,
                total_value=total_value,
                tax_rate=item.tax_rate,
                tax_amount=tax_amount,
                sale_type="Goods at standard rate (default)"
            )
            
            session.add(invoice_item)
            total_amount += total_value
            total_tax += tax_amount
        
        # Update invoice totals
        invoice.subtotal_amount = total_amount
        invoice.total_tax_amount = total_tax
        invoice.grand_total = total_amount + total_tax
    
    print(f"   📄 Created sample invoices for company {company_id}")


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


def show_database_summary(engine):
    """Show database summary after setup"""
    try:
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Count records in each table
        tables_info = [
            ('Companies', Company),
            ('Items', Item),
            ('Buyers', Buyer),
            ('FBR Settings', FBRSettings),
            ('Invoices', Invoices),
            ('Invoice Items', SalesInvoiceItem)
        ]
        
        for table_name, model_class in tables_info:
            count = session.query(model_class).count()
            print(f"   📊 {table_name}: {count} records")
        
        session.close()
        
    except Exception as e:
        print(f"   ❌ Could not retrieve database summary: {str(e)}")


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


def create_specific_company():
    """Interactive function to create a specific company"""
    print("🏢 Create New Company")
    print("=" * 50)
    
    try:
        # Get company details from user
        ntn_cnic = input("Enter NTN/CNIC (13 digits): ").strip()
        if len(ntn_cnic) != 13 or not ntn_cnic.isdigit():
            print("❌ Invalid NTN/CNIC format")
            return
        
        name = input("Enter Company Name: ").strip()
        if not name:
            print("❌ Company name is required")
            return
        
        address = input("Enter Address: ").strip()
        province = input("Enter Province: ").strip()
        city = input("Enter City: ").strip()
        phone = input("Enter Phone (optional): ").strip()
        email = input("Enter Email (optional): ").strip()
        contact_person = input("Enter Contact Person: ").strip()
        business_type = input("Enter Business Type: ").strip()
        
        # Create database connection
        engine = create_engine(DATABASE_URL)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Check if company already exists
        existing = session.query(Company).filter_by(ntn_cnic=ntn_cnic).first()
        if existing:
            print(f"❌ Company with NTN/CNIC {ntn_cnic} already exists")
            return
        
        # Create company
        company = Company(
            ntn_cnic=ntn_cnic,
            name=name,
            address=address or None,
            province=province or None,
            city=city or None,
            phone=phone or None,
            email=email or None,
            contact_person=contact_person or None,
            business_type=business_type or None,
            registration_date=datetime.now()
        )
        
        session.add(company)
        session.commit()
        
        print(f"✅ Company '{name}' created successfully!")
        
        # Ask if user wants to add FBR settings
        add_settings = input("Add FBR settings for this company? (y/N): ").strip().lower()
        if add_settings == 'y':
            create_company_fbr_settings(session, ntn_cnic)
            session.commit()
            print("✅ FBR settings added")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error creating company: {str(e)}")


def show_help():
    """Show help information"""
    help_text = """
FBR E-Invoicing Database Setup Tool
==================================

Commands:
  python setup_company_database.py                 - Full setup with sample data
  python setup_company_database.py test           - Test database connection
  python setup_company_database.py reset          - Reset database (WARNING: deletes all data)
  python setup_company_database.py create         - Create a new company interactively
  python setup_company_database.py summary        - Show database summary
  python setup_company_database.py help           - Show this help

Features:
  ✅ Company-specific data structure
  ✅ Sample companies with complete data
  ✅ FBR settings configuration
  ✅ Sample items, buyers, and invoices
  ✅ Proper database relationships and indexes
  
After setup, you can start the application with:
  python main.py
    """
    print(help_text)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "test":
            test_connection()
        elif command == "reset":
            reset_database()
        elif command == "setup":
            setup_database()
        elif command == "create":
            create_specific_company()
        elif command == "summary":
            if test_connection():
                engine = create_engine(DATABASE_URL)
                show_database_summary(engine)
        elif command == "help":
            show_help()
        else:
            print(f"Unknown command: {command}")
            print("Use 'help' to see available commands")
    else:
        # Default action
        print("FBR Invoicing - Company-Specific Database Setup")
        print("=" * 60)
        
        if test_connection():
            setup_database()
            print("\n🎉 Your database is ready to use!")
            print("\nNext steps:")
            print("1. Run: python main.py")
            print("2. Select a company to work with")
            print("3. Configure FBR API settings in the Settings tab")
            print("4. Start creating invoices!")
            
            print("\n💡 Tips:")
            print("- Each company has its own data and settings")
            print("- Use sandbox mode for testing")
            print("- Check the logs tab for submission details")
            
        else:
            print("\n❌ Database connection failed.")
            print("Please check your connection string and try again.")

# Additional utility functions for maintenance

def backup_company_data(company_id, backup_file=None):
    """Backup data for a specific company"""
    if not backup_file:
        backup_file = f"company_backup_{company_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    # Implementation would use pg_dump with specific table filters
    print(f"Backing up company {company_id} to {backup_file}")
    # This would require implementing custom backup logic


def migrate_data():
    """Migrate data from old structure to company-specific structure"""
    print("Data migration functionality - implement as needed")
    # This would handle migrating from older database structures


def optimize_database():
    """Optimize database performance"""
    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            # Run VACUUM and ANALYZE
            conn.execute(text("VACUUM ANALYZE;"))
            print("✅ Database optimization completed")
            
    except Exception as e:
        print(f"❌ Database optimization failed: {str(e)}")