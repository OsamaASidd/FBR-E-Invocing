# fbr_core/fbr_api_service.py
import requests
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FBRAPIService(QObject):
    """Service class for FBR API interactions"""
    
    # Signals for async operations
    data_loaded = pyqtSignal(str, list)  # endpoint_key, data
    error_occurred = pyqtSignal(str, str)  # endpoint_key, error_message
    
    def __init__(self, db_manager=None):
        super().__init__()
        self.db_manager = db_manager
        self.base_url = "https://gw.fbr.gov.pk"
        self.session = requests.Session()
        self._setup_session()
        
    def _setup_session(self):
        """Setup session with default headers and authorization"""
        try:
            if self.db_manager:
                session_db = self.db_manager.get_session()
                from fbr_core.models import FBRSettings
                
                settings = session_db.query(FBRSettings).first()
                if settings and settings.pral_authorization_token:
                    self.session.headers.update({
                        'Authorization': f'Bearer {settings.pral_authorization_token}',
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    })
                    logger.info("FBR API authorization token loaded from settings")
                else:
                    logger.warning("No FBR authorization token found in settings")
            
        except Exception as e:
            logger.error(f"Error setting up FBR API session: {e}")
    
    def _make_request(self, endpoint: str, params: dict = None) -> Optional[List[Dict]]:
        """Make API request to FBR endpoint"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            logger.info(f"Making request to: {url}")
            if params:
                logger.info(f"With parameters: {params}")
                
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Received {len(data)} items from {endpoint}")
            return data
            
        except requests.exceptions.Timeout:
            error_msg = f"Request timeout for {endpoint}"
            logger.error(error_msg)
            return None
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error {response.status_code} for {endpoint}: {e}"
            logger.error(error_msg)
            return None
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error for {endpoint}: {e}"
            logger.error(error_msg)
            return None
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON decode error for {endpoint}: {e}"
            logger.error(error_msg)
            return None
    
    def get_provinces(self) -> Optional[List[Dict]]:
        """Fetch provinces from FBR API"""
        return self._make_request("/pdi/v1/provinces")
    
    def get_document_types(self) -> Optional[List[Dict]]:
        """Fetch document types from FBR API"""
        return self._make_request("/pdi/v1/doctypecode")
    
    def get_hs_codes(self) -> Optional[List[Dict]]:
        """Fetch HS codes from FBR API"""
        return self._make_request("/pdi/v1/itemdesccode")
    
    def get_sro_item_codes(self) -> Optional[List[Dict]]:
        """Fetch SRO item codes from FBR API"""
        return self._make_request("/pdi/v1/sroitemcode")
    
    def get_transaction_types(self) -> Optional[List[Dict]]:
        """Fetch transaction types (sale types) from FBR API"""
        return self._make_request("/pdi/v1/transtypecode")
    
    def get_uom_types(self) -> Optional[List[Dict]]:
        """Fetch UOM types from FBR API"""
        return self._make_request("/pdi/v1/uom")
    
    def get_sro_schedule(self, rate_id: int, date: str) -> Optional[List[Dict]]:
        """Fetch SRO schedule from FBR API
        
        Args:
            rate_id: Rate ID from form
            date: Date in DD-MMM-YYYY format (e.g., '04-Feb-2024')
        """
        params = {
            'rate_id': rate_id,
            'date': date
        }
        return self._make_request("/pdi/v1/SroSchedule", params)
    
    def get_sale_type_to_rate(self, date: str, trans_type_id: int, origination_supplier: int) -> Optional[List[Dict]]:
        """Fetch sale type to rate from FBR API
        
        Args:
            date: Date in DD-MMM-YYYY format
            trans_type_id: Transaction type ID
            origination_supplier: Province ID
        """
        params = {
            'date': date,
            'transTypeId': trans_type_id,
            'originationSupplier': origination_supplier
        }
        return self._make_request("/pdi/v2/SaleTypeToRate", params)
    
    def get_hs_uom(self, hs_code: str, annexure_id: int = 3) -> Optional[List[Dict]]:
        """Fetch UOM filtered by HS code from FBR API
        
        Args:
            hs_code: HS code (e.g., '5904.9000')
            annexure_id: Sales annexure ID (default: 3)
        """
        params = {
            'hs_code': hs_code,
            'annexure_id': annexure_id
        }
        return self._make_request("/pdi/v2/HS_UOM", params)
    
    def get_sro_items(self, date: str, sro_id: int) -> Optional[List[Dict]]:
        """Fetch SRO items from FBR API
        
        Args:
            date: Date in YYYY-MM-DD format
            sro_id: SRO ID
        """
        params = {
            'date': date,
            'sro_id': sro_id
        }
        return self._make_request("/pdi/v2/SROItem", params)


class FBRAPIThread(QThread):
    """Background thread for FBR API calls"""
    
    data_received = pyqtSignal(str, list)  # endpoint_key, data
    error_occurred = pyqtSignal(str, str)  # endpoint_key, error_message
    
    def __init__(self, api_service: FBRAPIService, endpoint_key: str, method_name: str, **kwargs):
        super().__init__()
        self.api_service = api_service
        self.endpoint_key = endpoint_key
        self.method_name = method_name
        self.kwargs = kwargs
    
    def run(self):
        """Execute the API call in background thread"""
        try:
            method = getattr(self.api_service, self.method_name)
            data = method(**self.kwargs)
            
            if data is not None:
                self.data_received.emit(self.endpoint_key, data)
            else:
                self.error_occurred.emit(self.endpoint_key, f"Failed to fetch {self.endpoint_key}")
                
        except Exception as e:
            self.error_occurred.emit(self.endpoint_key, str(e))


class DropdownDataFormatter:
    """Helper class to format API data for dropdowns"""
    
    @staticmethod
    def format_provinces(data: List[Dict]) -> List[str]:
        """Format provinces for dropdown"""
        return [item['stateProvinceDesc'] for item in data]
    
    @staticmethod
    def format_document_types(data: List[Dict]) -> List[str]:
        """Format document types for dropdown: 'description - ID'"""
        return [f"{item['docDescription']} - {item['docTypeId']}" for item in data]
    
    @staticmethod
    def format_hs_codes(data: List[Dict]) -> List[str]:
        """Format HS codes for dropdown: 'code - description'"""
        return [f"{item['hS_CODE']} - {item['description']}" for item in data]
    
    @staticmethod
    def format_sro_item_codes(data: List[Dict]) -> List[str]:
        """Format SRO item codes for dropdown: 'description'"""
        return [item['srO_ITEM_DESC'] for item in data]
    
    @staticmethod
    def format_transaction_types(data: List[Dict]) -> List[str]:
        """Format transaction types for dropdown: 'description - ID'"""
        return [f"{item['transactioN_DESC']} - {item['transactioN_TYPE_ID']}" for item in data]
    
    @staticmethod
    def format_uom_types(data: List[Dict]) -> List[str]:
        """Format UOM types for dropdown: 'description - ID'"""
        return [f"{item['description']} - {item['uoM_ID']}" for item in data]
    
    @staticmethod
    def format_sro_schedule(data: List[Dict]) -> List[str]:
        """Format SRO schedule for dropdown: 'description - ID'"""
        return [f"{item['srO_DESC']} - {item['srO_ID']}" for item in data]
    
    @staticmethod
    def format_sale_type_rates(data: List[Dict]) -> List[str]:
        """Format sale type rates for dropdown: 'ID - description - value'"""
        return [f"{item['ratE_ID']} - {item['ratE_DESC']} - {item['ratE_VALUE']}%" for item in data]
    
    @staticmethod
    def extract_id_from_dropdown_text(text: str, position: int = -1) -> str:
        """Extract ID from formatted dropdown text
        
        Args:
            text: Formatted dropdown text
            position: Position of ID in split (-1 for last, 0 for first, etc.)
        """
        try:
            parts = text.split(' - ')
            return parts[position].strip()
        except (IndexError, AttributeError):
            return ""
    
    @staticmethod
    def extract_hs_code_from_dropdown_text(text: str) -> str:
        """Extract HS code from formatted dropdown text"""
        try:
            return text.split(' - ')[0].strip()
        except (IndexError, AttributeError):
            return ""


# Usage example and utility functions
class FBRDropdownManager:
    """Manager class for handling FBR dropdown data"""
    
    def __init__(self, db_manager):
        self.api_service = FBRAPIService(db_manager)
        self.formatter = DropdownDataFormatter()
        self.cached_data = {}
        self.loading_threads = {}
    
    def load_dropdown_data(self, dropdown_key: str, callback=None, **params):
        """Load dropdown data asynchronously
        
        Args:
            dropdown_key: Key identifying the dropdown type
            callback: Function to call when data is loaded
            **params: Additional parameters for API call
        """
        
        api_methods = {
            'provinces': 'get_provinces',
            'document_types': 'get_document_types', 
            'hs_codes': 'get_hs_codes',
            'sro_item_codes': 'get_sro_item_codes',
            'transaction_types': 'get_transaction_types',
            'uom_types': 'get_uom_types',
            'sro_schedule': 'get_sro_schedule',
            'sale_type_rates': 'get_sale_type_to_rate',
            'hs_uom': 'get_hs_uom',
            'sro_items': 'get_sro_items'
        }
        
        if dropdown_key not in api_methods:
            logger.error(f"Unknown dropdown key: {dropdown_key}")
            return
        
        # Create and start background thread
        thread = FBRAPIThread(
            self.api_service, 
            dropdown_key, 
            api_methods[dropdown_key], 
            **params
        )
        
        if callback:
            thread.data_received.connect(lambda key, data: callback(key, data))
            thread.error_occurred.connect(lambda key, error: logger.error(f"Error loading {key}: {error}"))
        
        self.loading_threads[dropdown_key] = thread
        thread.start()
    
    def format_data_for_dropdown(self, dropdown_key: str, data: List[Dict]) -> List[str]:
        """Format API data for dropdown display"""
        formatters = {
            'provinces': self.formatter.format_provinces,
            'document_types': self.formatter.format_document_types,
            'hs_codes': self.formatter.format_hs_codes,
            'sro_item_codes': self.formatter.format_sro_item_codes,
            'transaction_types': self.formatter.format_transaction_types,
            'uom_types': self.formatter.format_uom_types,
            'sro_schedule': self.formatter.format_sro_schedule,
            'sale_type_rates': self.formatter.format_sale_type_rates,
            'hs_uom': self.formatter.format_uom_types,  # Same format as uom_types
            'sro_items': self.formatter.format_sro_item_codes  # Same format as sro_item_codes
        }
        
        formatter = formatters.get(dropdown_key)
        if formatter:
            return formatter(data)
        else:
            logger.warning(f"No formatter found for {dropdown_key}")
            return []
    
    def cleanup_threads(self):
        """Clean up background threads"""
        for thread in self.loading_threads.values():
            if thread.isRunning():
                thread.quit()
                thread.wait()
        self.loading_threads.clear()


# Date formatting utilities for FBR APIs
class FBRDateUtils:
    """Utility class for FBR date formatting"""
    
    @staticmethod
    def format_date_for_fbr(date_obj) -> str:
        """Format date for FBR API (DD-MMM-YYYY format)
        
        Args:
            date_obj: datetime object or QDate
            
        Returns:
            Formatted date string like '04-Feb-2024'
        """
        try:
            if hasattr(date_obj, 'toPython'):  # QDate
                date_obj = date_obj.toPython()
            
            return date_obj.strftime('%d-%b-%Y')
            
        except Exception as e:
            logger.error(f"Error formatting date: {e}")
            return datetime.now().strftime('%d-%b-%Y')
    
    @staticmethod
    def format_date_iso(date_obj) -> str:
        """Format date in ISO format (YYYY-MM-DD)
        
        Args:
            date_obj: datetime object or QDate
            
        Returns:
            Formatted date string like '2024-02-04'
        """
        try:
            if hasattr(date_obj, 'toPython'):  # QDate
                date_obj = date_obj.toPython()
            
            return date_obj.strftime('%Y-%m-%d')
            
        except Exception as e:
            logger.error(f"Error formatting date: {e}")
            return datetime.now().strftime('%Y-%m-%d')