# fbr_core/models.py - Updated Company-Specific Version
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Float,
    Boolean,
    create_engine,
    ForeignKey,
    Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()


class Company(Base):
    """Company/Organization table - Primary entity"""
    __tablename__ = "companies"

    ntn_cnic = Column(String(100), primary_key=True)  # NTN/CNIC as primary key
    name = Column(String(255), nullable=False)
    address = Column(Text)
    phone = Column(String(50))
    email = Column(String(100))
    contact_person = Column(String(255))
    province = Column(String(100))
    city = Column(String(100))
    postal_code = Column(String(20))
    business_type = Column(String(100))
    registration_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    invoices = relationship("Invoices", back_populates="company")
    items = relationship("Item", back_populates="company")
    buyers = relationship("Buyer", back_populates="company")
    fbr_settings = relationship("FBRSettings", back_populates="company")
    fbr_queue = relationship("FBRQueue", back_populates="company")
    fbr_logs = relationship("FBRLogs", back_populates="company")


class Buyer(Base):
    """Buyer/Customer table - Company specific"""
    __tablename__ = "buyers"

    id = Column(Integer, primary_key=True)
    ntn_cnic = Column(String(100), nullable=False)  # Buyer's NTN/CNIC
    name = Column(String(255), nullable=False)
    address = Column(Text)
    phone = Column(String(50))
    email = Column(String(100))
    province = Column(String(100))
    city = Column(String(100))
    buyer_type = Column(String(50), default="Registered")  # Registered/Unregistered
    
    # Company relationship
    company_id = Column(String(100), ForeignKey('companies.ntn_cnic'), nullable=False)
    company = relationship("Company", back_populates="buyers")
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    invoices = relationship("Invoices", back_populates="buyer")

    # Indexes
    __table_args__ = (
        Index('ix_buyers_company_ntn', 'company_id', 'ntn_cnic'),
    )


class Item(Base):
    """Items/Products table - Company specific"""
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    hs_code = Column(String(50), nullable=False)
    uom = Column(String(50), nullable=False)  # Unit of Measurement
    category = Column(String(100))
    
    # Pricing information
    standard_rate = Column(Float)  # Default selling rate
    cost_price = Column(Float)
    tax_rate = Column(Float, default=18.0)  # Default tax rate
    
    # Company relationship
    company_id = Column(String(100), ForeignKey('companies.ntn_cnic'), nullable=False)
    company = relationship("Company", back_populates="items")
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    invoice_items = relationship("SalesInvoiceItem", back_populates="item")

    # Indexes
    __table_args__ = (
        Index('ix_items_company_hs', 'company_id', 'hs_code'),
        Index('ix_items_company_name', 'company_id', 'name'),
    )


class Invoices(Base):
    """Sales Invoices table - Company specific"""
    __tablename__ = "sales_invoices"

    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(100), nullable=False)
    
    # Company and buyer relationships
    company_id = Column(String(100), ForeignKey('companies.ntn_cnic'), nullable=False)
    buyer_id = Column(Integer, ForeignKey('buyers.id'), nullable=True)
    
    # Invoice details
    invoice_type = Column(String(50), default="Sale Invoice")
    posting_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime)
    
    # Buyer details (denormalized for FBR submission)
    buyer_ntn_cnic = Column(String(100))
    buyer_name = Column(String(255))
    buyer_address = Column(Text)
    buyer_province = Column(String(100))
    buyer_type = Column(String(50), default="Registered")
    
    # Transaction details
    transaction_type = Column(String(100))
    sale_origination_province = Column(String(100))
    destination_supply_province = Column(String(100))
    
    # Financial totals
    subtotal_amount = Column(Float, default=0.0)
    total_tax_amount = Column(Float, default=0.0)
    total_extra_tax = Column(Float, default=0.0)
    total_further_tax = Column(Float, default=0.0)
    total_discount = Column(Float, default=0.0)
    grand_total = Column(Float, default=0.0)

    # FBR specific fields
    fbr_invoice_number = Column(String(255))
    fbr_status = Column(String(50))  # Valid, Invalid, Error, Pending
    fbr_response = Column(Text)
    fbr_datetime = Column(DateTime)
    fbr_scenario_id = Column(String(50))  # For sandbox mode
    submit_to_fbr = Column(Boolean, default=True)
    
    # Status tracking
    status = Column(String(50), default="Draft")  # Draft, Validated, Submitted, Completed
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="invoices")
    buyer = relationship("Buyer", back_populates="invoices")
    items = relationship("SalesInvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('ix_invoices_company_date', 'company_id', 'posting_date'),
        Index('ix_invoices_fbr_status', 'company_id', 'fbr_status'),
        Index('ix_invoices_number', 'company_id', 'invoice_number'),
    )


class SalesInvoiceItem(Base):
    """Sales Invoice Items table"""
    __tablename__ = "sales_invoice_items"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey('sales_invoices.id'), nullable=False)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=True)  # Can be null for custom items
    
    # Item details (denormalized for FBR submission)
    item_name = Column(String(255), nullable=False)
    item_description = Column(Text)
    hs_code = Column(String(50), nullable=False)
    uom = Column(String(50), nullable=False)
    
    # Quantity and pricing
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_value = Column(Float, nullable=False)
    
    # Tax details
    tax_rate = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    extra_tax = Column(Float, default=0.0)
    further_tax = Column(Float, default=0.0)
    sales_tax_withheld_at_source = Column(Float, default=0.0)
    
    # Additional fields for FBR
    fixed_notified_value = Column(Float, default=0.0)
    sro_schedule_no = Column(String(100))
    fed_payable = Column(Float, default=0.0)
    discount = Column(Float, default=0.0)
    sale_type = Column(String(200), default="Goods at standard rate (default)")
    sro_item_serial_no = Column(String(100))
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoice = relationship("Invoices", back_populates="items")
    item = relationship("Item", back_populates="invoice_items")

    # Indexes
    __table_args__ = (
        Index('ix_invoice_items_invoice', 'invoice_id'),
        Index('ix_invoice_items_item', 'item_id'),
    )


class FBRQueue(Base):
    """FBR Submission Queue - Company specific"""
    __tablename__ = "fbr_queue"

    id = Column(Integer, primary_key=True)
    
    # Company relationship
    company_id = Column(String(100), ForeignKey('companies.ntn_cnic'), nullable=False)
    
    # Document details
    document_type = Column(String(50), nullable=False)  # Sales Invoice, POS Invoice
    document_id = Column(Integer, nullable=False)
    
    # Queue management
    status = Column(String(50), default="Pending")  # Pending, Processing, Completed, Failed
    priority = Column(Integer, default=5)  # 1-10, lower number = higher priority
    
    # Retry management
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=5)
    
    # Error handling
    error_message = Column(Text)
    fbr_response = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_retry_at = Column(DateTime)
    completed_at = Column(DateTime)
    next_retry_at = Column(DateTime)  # For scheduled retries

    # Relationships
    company = relationship("Company", back_populates="fbr_queue")

    # Indexes
    __table_args__ = (
        Index('ix_fbr_queue_company_status', 'company_id', 'status'),
        Index('ix_fbr_queue_priority', 'status', 'priority', 'created_at'),
        Index('ix_fbr_queue_retry', 'next_retry_at'),
    )


class FBRLogs(Base):
    """FBR Submission Logs - Company specific"""
    __tablename__ = "fbr_logs"

    id = Column(Integer, primary_key=True)
    
    # Company relationship
    company_id = Column(String(100), ForeignKey('companies.ntn_cnic'), nullable=False)
    
    # Document details
    document_type = Column(String(50), nullable=False)
    document_id = Column(Integer, nullable=False)
    
    # FBR details
    fbr_invoice_number = Column(String(255))
    fbr_scenario_id = Column(String(50))  # For sandbox mode
    
    # Submission details
    status = Column(String(50), nullable=False)  # Success, Invalid, Error, Timeout
    submitted_at = Column(DateTime, default=datetime.utcnow)
    processing_time = Column(Float)  # Processing time in milliseconds
    
    # API details
    api_endpoint = Column(String(500))
    request_payload = Column(Text)
    response_data = Column(Text)
    response_status_code = Column(String(10))
    response_headers = Column(Text)
    
    # Error details
    validation_errors = Column(Text)
    error_code = Column(String(50))
    error_description = Column(Text)
    
    # Additional metadata
    mode = Column(String(20), default="sandbox")  # sandbox, production
    api_version = Column(String(20))
    user_agent = Column(String(200))
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="fbr_logs")

    # Indexes
    __table_args__ = (
        Index('ix_fbr_logs_company_date', 'company_id', 'submitted_at'),
        Index('ix_fbr_logs_status', 'company_id', 'status'),
        Index('ix_fbr_logs_document', 'company_id', 'document_type', 'document_id'),
    )


class FBRSettings(Base):
    """FBR API Settings - Company specific"""
    __tablename__ = "fbr_settings"

    id = Column(Integer, primary_key=True)
    
    # Company relationship
    company_id = Column(String(100), ForeignKey('companies.ntn_cnic'), nullable=False)
    
    # API Configuration
    api_endpoint = Column(String(500))
    validation_endpoint = Column(String(500))
    pral_authorization_token = Column(String(500))
    pral_login_id = Column(String(200))
    pral_login_password = Column(String(200))
    
    # API Settings
    timeout_seconds = Column(Integer, default=30)
    max_retries = Column(Integer, default=3)
    retry_delay_seconds = Column(Integer, default=5)
    
    # Mode Configuration
    default_mode = Column(String(20), default="sandbox")  # sandbox, production
    sandbox_scenario_id = Column(String(50), default="SN001")
    
    # Validation Settings
    auto_validate_before_submit = Column(Boolean, default=True)
    auto_queue_on_failure = Column(Boolean, default=True)
    
    # Notification Settings
    email_notifications = Column(Boolean, default=False)
    notification_email = Column(String(200))
    
    # Advanced Settings
    bulk_submission_enabled = Column(Boolean, default=True)
    max_bulk_size = Column(Integer, default=50)
    parallel_processing = Column(Boolean, default=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="fbr_settings")

    # Indexes
    __table_args__ = (
        Index('ix_fbr_settings_company', 'company_id'),
    )


class SystemSettings(Base):
    """System-wide settings"""
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    description = Column(Text)
    category = Column(String(50), default="general")
    data_type = Column(String(20), default="string")  # string, integer, boolean, json
    is_encrypted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """Audit log for tracking changes"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    company_id = Column(String(100), ForeignKey('companies.ntn_cnic'), nullable=True)
    
    # Action details
    action = Column(String(50), nullable=False)  # CREATE, UPDATE, DELETE, SUBMIT
    table_name = Column(String(100), nullable=False)
    record_id = Column(String(100), nullable=False)
    
    # Change details
    old_values = Column(Text)  # JSON
    new_values = Column(Text)  # JSON
    
    # User context (if applicable)
    user_id = Column(String(100))
    user_name = Column(String(255))
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    
    created_at = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('ix_audit_company_date', 'company_id', 'created_at'),
        Index('ix_audit_table_record', 'table_name', 'record_id'),
    )


# Database connection and management
class DatabaseManager:
    """Enhanced Database Manager with company support"""
    
    def __init__(self, connection_string):
        # PostgreSQL connection with SSL settings for Neon
        self.engine = create_engine(
            connection_string,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_size=10,       # Connection pool size
            max_overflow=20,    # Additional connections beyond pool_size
            echo=False,  # Set to True for SQL debugging
        )
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def get_session(self):
        """Get database session"""
        return self.session

    def close(self):
        """Close database connection"""
        self.session.close()
        
    def create_company(self, ntn_cnic, name, **kwargs):
        """Create a new company with default settings"""
        try:
            session = self.get_session()
            
            # Check if company exists
            existing = session.query(Company).filter_by(ntn_cnic=ntn_cnic).first()
            if existing:
                raise ValueError(f"Company with NTN/CNIC {ntn_cnic} already exists")
            
            # Create company
            company = Company(
                ntn_cnic=ntn_cnic,
                name=name,
                **kwargs
            )
            session.add(company)
            
            # Create default FBR settings
            fbr_settings = FBRSettings(
                company_id=ntn_cnic,
                api_endpoint="https://gw.fbr.gov.pk/di_data/v1/di/postinvoicedata_sb",
                validation_endpoint="https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata_sb"
            )
            session.add(fbr_settings)
            
            session.commit()
            return company
            
        except Exception as e:
            session.rollback()
            raise e

    def get_company_stats(self, company_id):
        """Get statistics for a specific company"""
        try:
            session = self.get_session()
            
            stats = {
                'total_invoices': session.query(Invoices).filter_by(company_id=company_id).count(),
                'pending_fbr': session.query(Invoices).filter_by(
                    company_id=company_id, 
                    fbr_status=None
                ).count(),
                'successful_fbr': session.query(Invoices).filter_by(
                    company_id=company_id, 
                    fbr_status='Valid'
                ).count(),
                'failed_fbr': session.query(Invoices).filter_by(
                    company_id=company_id, 
                    fbr_status='Invalid'
                ).count(),
                'total_items': session.query(Item).filter_by(company_id=company_id).count(),
                'total_buyers': session.query(Buyer).filter_by(company_id=company_id).count(),
                'queue_pending': session.query(FBRQueue).filter_by(
                    company_id=company_id, 
                    status='Pending'
                ).count(),
            }
            
            return stats
            
        except Exception as e:
            print(f"Error getting company stats: {e}")
            return {}

    def cleanup_old_logs(self, company_id, days_to_keep=90):
        """Clean up old FBR logs for a company"""
        try:
            session = self.get_session()
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            deleted = session.query(FBRLogs).filter(
                FBRLogs.company_id == company_id,
                FBRLogs.created_at < cutoff_date
            ).delete()
            
            session.commit()
            return deleted
            
        except Exception as e:
            session.rollback()
            print(f"Error cleaning up logs: {e}")
            return 0

    def backup_company_data(self, company_id, backup_path):
        """Backup company data to file"""
        # Implementation would depend on specific backup requirements
        pass


# Example usage and utility functions
def get_database_manager():
    """Get database manager instance"""
    # Neon PostgreSQL connection
    connection_string = (
        "postgresql://neondb_owner:npg_H2hByXAgPz8n@ep-sparkling-shape-"
        "adwmth20-pooler.c-2.us-east-1.aws.neon.tech/neondb?"
        "sslmode=require&channel_binding=require"
    )
    return DatabaseManager(connection_string)


def create_sample_company(db_manager, ntn_cnic="1234567890123"):
    """Create a sample company for testing"""
    try:
        company = db_manager.create_company(
            ntn_cnic=ntn_cnic,
            name="Sample Company Ltd",
            address="Sample Address, Karachi",
            province="Sindh",
            city="Karachi",
            business_type="Services",
            contact_person="John Doe",
            email="info@samplecompany.com",
            phone="+92-21-1234567"
        )
        
        # Create sample items
        session = db_manager.get_session()
        
        sample_items = [
            Item(
                company_id=ntn_cnic,
                name="Professional Services",
                description="Consulting and professional services",
                hs_code="9999.0000",
                uom="Hours",
                standard_rate=5000.0,
                tax_rate=18.0
            ),
            Item(
                company_id=ntn_cnic,
                name="Software License",
                description="Annual software license",
                hs_code="8542.3100",
                uom="Numbers, pieces, units",
                standard_rate=50000.0,
                tax_rate=17.0
            ),
            Item(
                company_id=ntn_cnic,
                name="Hardware Equipment",
                description="Computer hardware and equipment",
                hs_code="8471.3000",
                uom="Numbers, pieces, units",
                standard_rate=75000.0,
                tax_rate=18.0
            )
        ]
        
        for item in sample_items:
            session.add(item)
        
        # Create sample buyer
        sample_buyer = Buyer(
            company_id=ntn_cnic,
            ntn_cnic="9876543210987",
            name="Sample Customer Ltd",
            address="Customer Address, Lahore",
            province="Punjab",
            city="Lahore",
            buyer_type="Registered"
        )
        session.add(sample_buyer)
        
        session.commit()
        return company
        
    except Exception as e:
        print(f"Error creating sample company: {e}")
        return None


if __name__ == "__main__":
    # Test the models
    db_manager = get_database_manager()
    
    # Create sample company
    try:
        company = create_sample_company(db_manager)
        if company:
            print(f"✅ Sample company created: {company.name}")
            
            # Get stats
            stats = db_manager.get_company_stats(company.ntn_cnic)
            print(f"📊 Company stats: {stats}")
            
        else:
            print("❌ Failed to create sample company")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        db_manager.close()