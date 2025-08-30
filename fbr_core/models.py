# fbr_core/models.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Text,
    Float,
    Boolean,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()


class Buyer(Base):
    __tablename__ = "buyers"

    ntn_cnic = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Customer(Base):
    __tablename__ = "customers"

    ntn_cnic = Column(String(100), primary_key=True)  
    name = Column(String(255), nullable=False)
    address = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    code = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    hs_code = Column(String(50))
    uom = Column(String(50))
    rate = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class Invoices(Base):
    __tablename__ = "sales_invoices"

    id = Column(Integer, primary_key=True)
    invoice_number = Column(String(100), unique=True, nullable=False)
    customer_id = Column(Integer)
    company_id = Column(Integer)
    posting_date = Column(DateTime)
    due_date = Column(DateTime)
    total_amount = Column(Float)
    tax_amount = Column(Float)
    grand_total = Column(Float)

    # FBR specific fields
    fbr_invoice_number = Column(String(255))
    fbr_status = Column(String(50))  # Valid, Invalid, Error
    fbr_response = Column(Text)
    fbr_datetime = Column(DateTime)
    submit_to_fbr = Column(Boolean, default=True)
    province = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SalesInvoiceItem(Base):
    __tablename__ = "sales_invoice_items"

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer)
    item_id = Column(Integer)
    quantity = Column(Float)
    rate = Column(Float)
    amount = Column(Float)
    tax_rate = Column(Float)
    tax_amount = Column(Float)
    hs_code = Column(String(50))
    description = Column(Text)


class FBRQueue(Base):
    __tablename__ = "fbr_queue"

    id = Column(Integer, primary_key=True)
    document_type = Column(String(50))  # Sales Invoice, POS Invoice
    document_id = Column(Integer)
    status = Column(String(50))  # Pending, Processing, Completed, Failed
    priority = Column(Integer, default=5)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=5)
    error_message = Column(Text)
    fbr_response = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_retry_at = Column(DateTime)
    completed_at = Column(DateTime)
    # validation_errors = Column(Text)
    # processing_time = Column(Float)


class FBRLogs(Base):
    __tablename__ = "fbr_logs"

    id = Column(Integer, primary_key=True)
    document_type = Column(String(50))
    document_id = Column(Integer)
    fbr_invoice_number = Column(String(255))
    status = Column(String(50))  # Success, Invalid, Error, Timeout
    submitted_at = Column(DateTime, default=datetime.utcnow)
    processing_time = Column(Float)
    request_payload = Column(Text)
    response_data = Column(Text)
    response_status_code = Column(String(10))
    validation_errors = Column(Text)


class FBRSettings(Base):
    __tablename__ = "fbr_settings"

    id = Column(Integer, primary_key=True)
    api_endpoint = Column(String(500))
    pral_authorization_token = Column(String(500))
    pral_login_id = Column(String(100))
    pral_login_password = Column(String(100))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Database connection
class DatabaseManager:
    def __init__(self, connection_string):
        # PostgreSQL connection with SSL settings for Neon
        self.engine = create_engine(
            connection_string,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=3600,  # Recycle connections after 1 hour
            echo=False,  # Set to True for SQL debugging
        )
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def get_session(self):
        return self.session

    def close(self):
        self.session.close()


# Example usage
def get_database_manager():
    # Neon PostgreSQL connection
    connection_string = (
        "postgresql://neondb_owner:npg_H2hByXAgPz8n@ep-sparkling-shape-"
        "adwmth20-pooler.c-2.us-east-1.aws.neon.tech/neondb?"
        "sslmode=require&channel_binding=require"
    )
    return DatabaseManager(connection_string)
