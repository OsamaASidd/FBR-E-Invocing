# fbr_core/fbr_service.py
import json
import requests
from datetime import datetime
from typing import Dict, List
from .models import DatabaseManager, SalesInvoice, FBRQueue, FBRLogs, FBRSettings


class FBRPayloadBuilder:
    """Builds FBR payload from invoice data"""

    def build_sales_invoice_payload(self, invoice_data: Dict) -> Dict:
        """Build FBR payload for Sales Invoice"""

        # Extract party information
        seller_tax_id = invoice_data.get("customer_tax_id", "")
        seller_name = invoice_data.get("customer_name", "")
        seller_province = invoice_data.get("tax_category", "")
        seller_address = invoice_data.get("customer_address", "")

        buyer_tax_id = invoice_data.get("company_tax_id", "")
        buyer_name = invoice_data.get("company_name", "")
        buyer_province = invoice_data.get("province", "")
        buyer_address = invoice_data.get("company_address", "")

        # Determine invoice type
        invoice_type = (
            "Debit Note" if invoice_data.get("is_debit_note", False) else "Sale Invoice"
        )
        buyer_registration_type = "Registered" if buyer_tax_id else "Unregistered"

        # Build main payload
        payload = {
            "invoiceType": invoice_type,
            "invoiceDate": invoice_data["posting_date"].strftime("%Y-%m-%d"),
            "sellerNTNCNIC": seller_tax_id,
            "sellerBusinessName": seller_name,
            "sellerProvince": seller_province,
            "sellerAddress": seller_address,
            "buyerNTNCNIC": buyer_tax_id,
            "buyerBusinessName": buyer_name,
            "buyerProvince": buyer_province,
            "buyerAddress": buyer_address,
            "buyerRegistrationType": buyer_registration_type,
            "invoiceRefNo": "",
            "items": [],
        }

        # Build items
        for item in invoice_data.get("items", []):
            tax_rate = item.get("tax_rate", 0.0)
            value_excl_st = item.get("rate", 0.0)
            sales_tax_applicable = round((tax_rate * value_excl_st) / 100.0, 2)

            item_entry = {
                "hsCode": item.get("hs_code", ""),
                "productDescription": item.get(
                    "description", item.get("item_name", "")
                ),
                "rate": f"{tax_rate}%",
                "uoM": item.get("uom", ""),
                "quantity": item.get("quantity", 0.0),
                "totalValues": 0.00,
                "valueSalesExcludingST": value_excl_st,
                "fixedNotifiedValueOrRetailPrice": 0.00,
                "salesTaxApplicable": sales_tax_applicable,
                "salesTaxWithheldAtSource": 0.00,
                "extraTax": 0.00,
                "furtherTax": 0.00,
                "sroScheduleNo": "",
                "fedPayable": 0.00,
                "discount": abs(item.get("discount_amount", 0.0)),
                "saleType": "Goods at standard rate (default)",
                "sroItemSerialNo": "",
            }
            payload["items"].append(item_entry)

        return payload


class FBRValidator:
    """Validates invoices for FBR compliance"""

    def validate_invoice(self, invoice_data: Dict) -> Dict:
        """Validate invoice for FBR submission"""
        errors = []
        warnings = []

        # Check required fields
        if not invoice_data.get("province"):
            errors.append("Buyer Province is required for FBR submission")

        if not invoice_data.get("tax_category"):
            errors.append(
                "Tax Category (Seller Province) is required for FBR submission"
            )

        # Validate posting date
        posting_date = invoice_data.get("posting_date")
        if posting_date:
            today = datetime.now().date()
            if posting_date.date() != today:
                warnings.append(
                    f"FBR requires posting date to be current date ({today})"
                )

        # Validate customer tax information
        if not invoice_data.get("customer_tax_id"):
            warnings.append("Customer Tax ID missing - may affect FBR submission")

        # Validate company tax information
        if not invoice_data.get("company_tax_id"):
            errors.append("Company Tax ID is required for FBR submission")

        # Validate items
        items_errors = self._validate_items(invoice_data.get("items", []))
        errors.extend(items_errors)

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _validate_items(self, items: List[Dict]) -> List[str]:
        """Validate invoice items"""
        errors = []

        if not items:
            errors.append("At least one item is required for FBR submission")
            return errors

        missing_hs_codes = []
        missing_tax_rates = []

        for idx, item in enumerate(items, 1):
            if not item.get("hs_code"):
                missing_hs_codes.append(
                    f"Row {idx}: {item.get('item_name', 'Unknown')}"
                )

            if not item.get("tax_rate"):
                missing_tax_rates.append(
                    f"Row {idx}: {item.get('item_name', 'Unknown')}"
                )

        if missing_hs_codes:
            errors.append(
                f"Following items are missing HS Codes: {', '.join(missing_hs_codes)}"
            )

        if missing_tax_rates:
            errors.append(
                f"Following items are missing Tax Rates: {', '.join(missing_tax_rates)}"
            )

        return errors


class FBRSubmissionService:
    """Handles FBR API submissions"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.session = db_manager.get_session()

    def submit_invoice(
        self, invoice_id: int, document_type: str = "Sales Invoice"
    ) -> Dict:
        """Submit invoice to FBR"""
        try:
            # Get invoice data
            invoice_data = self._get_invoice_data(invoice_id, document_type)

            # Validate invoice
            validator = FBRValidator()
            validation_result = validator.validate_invoice(invoice_data)

            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": "Validation failed",
                    "errors": validation_result["errors"],
                }

            # Build payload
            payload_builder = FBRPayloadBuilder()
            payload = payload_builder.build_sales_invoice_payload(invoice_data)

            # Submit to FBR API
            response = self._submit_to_fbr_api(payload, invoice_id, document_type)

            # Update invoice with response
            self._update_invoice_with_response(invoice_id, document_type, response)

            # Log submission
            self._log_submission(invoice_id, document_type, payload, response)

            return {"success": True, "response": response}

        except Exception as e:
            error_msg = str(e)
            self._log_submission(
                invoice_id, document_type, {}, {"error": error_msg}, "Error"
            )
            return {"success": False, "error": error_msg}

    def _submit_to_fbr_api(
        self, payload: Dict, invoice_id: int, document_type: str
    ) -> Dict:
        """Submit to actual FBR API"""
        # Get FBR settings
        settings = self.session.query(FBRSettings).first()

        if not settings or not settings.api_endpoint:
            raise Exception("FBR API settings not configured")

        # headers = {
        #     "Content-Type": "application/json",
        #     "Authorization": f"Bearer {settings.pral_authorization_token}",
        # }

        try:
            # For development/testing, return mock response
            # In production, uncomment the actual API call

            # response = requests.post(
            #     settings.api_endpoint,
            #     json=payload,
            #     headers=headers,
            #     timeout=30
            # )
            # response.raise_for_status()
            # return response.json()

            # Mock response for development
            return {
                "invoiceNumber": (
                    f"FBR{invoice_id}{datetime.now().strftime('%Y%m%d%H%M%S')}"
                ),
                "dated": datetime.now().isoformat(),
                "validationResponse": {
                    "statusCode": "00",
                    "status": "Valid",
                    "error": "",
                    "invoiceStatuses": [
                        {
                            "itemSNo": "1",
                            "statusCode": "00",
                            "status": "Valid",
                            "invoiceNo": f"FBR{invoice_id}-1",
                            "errorCode": "",
                            "error": "",
                        }
                    ],
                },
            }

        except requests.exceptions.RequestException as e:
            raise Exception(f"FBR API request failed: {str(e)}")

    def _get_invoice_data(self, invoice_id: int, document_type: str) -> Dict:
        """Get invoice data from database"""
        # This is a simplified version - you'll need to implement
        # proper joins to get all related data
        invoice = self.session.query(SalesInvoice).filter_by(id=invoice_id).first()

        if not invoice:
            raise Exception(f"Invoice {invoice_id} not found")

        # Return invoice data dict
        return {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "posting_date": invoice.posting_date,
            "customer_name": "Sample Customer",  # Get from customer table
            "company_name": "Sample Company",  # Get from company table
            "province": invoice.province,
            "items": [],  # Get from invoice items table
        }

    def _update_invoice_with_response(
        self, invoice_id: int, document_type: str, response: Dict
    ):
        """Update invoice with FBR response"""
        invoice = self.session.query(SalesInvoice).filter_by(id=invoice_id).first()
        if invoice:
            invoice.fbr_invoice_number = response.get("invoiceNumber", "")
            invoice.fbr_datetime = datetime.now()
            invoice.fbr_status = response.get("validationResponse", {}).get(
                "status", ""
            )
            invoice.fbr_response = json.dumps(response)

            self.session.commit()

    def _log_submission(
        self,
        invoice_id: int,
        document_type: str,
        payload: Dict,
        response: Dict,
        status: str = "Success",
    ):
        """Log FBR submission"""
        log_entry = FBRLogs(
            document_type=document_type,
            document_id=invoice_id,
            fbr_invoice_number=response.get("invoiceNumber", ""),
            status=status,
            submitted_at=datetime.now(),
            request_payload=json.dumps(payload) if payload else "",
            response_data=json.dumps(response) if response else "",
            response_status_code="200" if status == "Success" else "500",
        )

        self.session.add(log_entry)
        self.session.commit()


class FBRQueueManager:
    """Manages FBR submission queue"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.session = db_manager.get_session()
        self.submission_service = FBRSubmissionService(db_manager)

    def add_to_queue(
        self, document_type: str, document_id: int, priority: int = 5
    ) -> Dict:
        """Add document to FBR queue"""
        try:
            # Check if already in queue
            existing = (
                self.session.query(FBRQueue)
                .filter_by(
                    document_type=document_type,
                    document_id=document_id,
                    status__in=["Pending", "Processing"],
                )
                .first()
            )

            if existing:
                existing.retry_count += 1
                existing.last_retry_at = datetime.now()
            else:
                queue_item = FBRQueue(
                    document_type=document_type,
                    document_id=document_id,
                    status="Pending",
                    priority=priority,
                    created_at=datetime.now(),
                )
                self.session.add(queue_item)

            self.session.commit()
            return {"success": True}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def process_queue(self, limit: int = 50) -> Dict:
        """Process pending queue items"""
        try:
            # Get pending items
            queue_items = (
                self.session.query(FBRQueue)
                .filter(
                    FBRQueue.status == "Pending",
                    FBRQueue.retry_count < FBRQueue.max_retries,
                )
                .order_by(FBRQueue.priority.desc(), FBRQueue.created_at.asc())
                .limit(limit)
                .all()
            )

            processed_count = 0

            for item in queue_items:
                try:
                    # Mark as processing
                    item.status = "Processing"
                    self.session.commit()

                    # Process the item
                    result = self.submission_service.submit_invoice(
                        item.document_id, item.document_type
                    )

                    if result["success"]:
                        item.status = "Completed"
                        item.completed_at = datetime.now()
                        processed_count += 1
                    else:
                        item.retry_count += 1
                        if item.retry_count >= item.max_retries:
                            item.status = "Failed"
                        else:
                            item.status = "Pending"
                        item.error_message = result.get("error", "Unknown error")
                        item.last_retry_at = datetime.now()

                    self.session.commit()

                except Exception as e:
                    item.status = "Failed"
                    item.error_message = str(e)
                    item.retry_count += 1
                    self.session.commit()

            return {"processed_count": processed_count}

        except Exception as e:
            return {"processed_count": 0, "error": str(e)}
