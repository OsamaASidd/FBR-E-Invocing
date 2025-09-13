# fbr_core/fbr_service.py - Updated Company-Specific Version
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy import and_
from .models import (
    DatabaseManager, Invoices, SalesInvoiceItem, FBRQueue, FBRLogs, 
    FBRSettings, Company, Buyer, Item
)


class CompanySpecificFBRPayloadBuilder:
    """Builds FBR payload from invoice data for specific company"""

    def __init__(self, db_manager: DatabaseManager, company_id: str):
        self.db_manager = db_manager
        self.company_id = company_id
        self.session = db_manager.get_session()

    def build_sales_invoice_payload(self, invoice_id: int, mode: str = "sandbox") -> Dict:
        """Build FBR payload for Sales Invoice"""
        try:
            # Get invoice with all related data
            invoice = (
                self.session.query(Invoices)
                .filter_by(id=invoice_id, company_id=self.company_id)
                .first()
            )
            
            if not invoice:
                raise ValueError(f"Invoice {invoice_id} not found for company {self.company_id}")

            # Get company details
            company = self.session.query(Company).filter_by(ntn_cnic=self.company_id).first()
            if not company:
                raise ValueError(f"Company {self.company_id} not found")

            # Build main payload
            payload = {
                "invoiceType": invoice.invoice_type or "Sale Invoice",
                "invoiceDate": invoice.posting_date.strftime("%Y-%m-%d"),
                
                # Seller details (from company)
                "sellerNTNCNIC": company.ntn_cnic,
                "sellerBusinessName": company.name,
                "sellerProvince": invoice.sale_origination_province or company.province or "Sindh",
                "sellerAddress": company.address or "",
                
                # Buyer details (from invoice)
                "buyerNTNCNIC": invoice.buyer_ntn_cnic or "",
                "buyerBusinessName": invoice.buyer_name or "",
                "buyerProvince": invoice.buyer_province or "Sindh",
                "buyerAddress": invoice.buyer_address or "",
                "buyerRegistrationType": invoice.buyer_type or "Unregistered",
                
                "invoiceRefNo": "",
                "items": []
            }

            # Add scenario ID for sandbox mode
            if mode.lower() == "sandbox":
                settings = self.session.query(FBRSettings).filter_by(company_id=self.company_id).first()
                scenario_id = settings.sandbox_scenario_id if settings else "SN001"
                payload["scenarioId"] = scenario_id

            # Build items
            invoice_items = (
                self.session.query(SalesInvoiceItem)
                .filter_by(invoice_id=invoice_id)
                .all()
            )

            for item in invoice_items:
                # Calculate values
                value_excl_st = item.total_value - item.tax_amount
                
                item_entry = {
                    "hsCode": item.hs_code,
                    "productDescription": item.item_description or item.item_name,
                    "rate": f"{item.tax_rate}%",
                    "uoM": item.uom,
                    "quantity": item.quantity,
                    "totalValues": item.total_value,
                    "valueSalesExcludingST": value_excl_st,
                    "fixedNotifiedValueOrRetailPrice": item.fixed_notified_value,
                    "salesTaxApplicable": item.tax_amount,
                    "salesTaxWithheldAtSource": item.sales_tax_withheld_at_source,
                    "extraTax": item.extra_tax,
                    "furtherTax": item.further_tax,
                    "sroScheduleNo": item.sro_schedule_no or "",
                    "fedPayable": item.fed_payable,
                    "discount": item.discount,
                    "saleType": item.sale_type,
                    "sroItemSerialNo": item.sro_item_serial_no or "",
                }
                payload["items"].append(item_entry)

            return payload

        except Exception as e:
            raise Exception(f"Error building payload: {str(e)}")


class CompanySpecificFBRValidator:
    """Validates invoices for FBR compliance for specific company"""

    def __init__(self, db_manager: DatabaseManager, company_id: str):
        self.db_manager = db_manager
        self.company_id = company_id
        self.session = db_manager.get_session()

    def validate_invoice(self, invoice_id: int) -> Dict:
        """Validate invoice for FBR submission"""
        errors = []
        warnings = []

        try:
            invoice = (
                self.session.query(Invoices)
                .filter_by(id=invoice_id, company_id=self.company_id)
                .first()
            )
            
            if not invoice:
                errors.append(f"Invoice {invoice_id} not found")
                return {"valid": False, "errors": errors, "warnings": warnings}

            # Check required fields
            if not invoice.buyer_province:
                errors.append("Buyer Province is required for FBR submission")

            if not invoice.sale_origination_province:
                errors.append("Sale Origination Province is required for FBR submission")

            # Validate company information
            company = self.session.query(Company).filter_by(ntn_cnic=self.company_id).first()
            if not company:
                errors.append("Company information not found")
            else:
                if not company.ntn_cnic:
                    errors.append("Company NTN/CNIC is required for FBR submission")
                if not company.name:
                    errors.append("Company name is required for FBR submission")

            # Validate posting date
            if invoice.posting_date:
                today = datetime.now().date()
                invoice_date = invoice.posting_date.date()
                if abs((invoice_date - today).days) > 3:
                    warnings.append(
                        f"Invoice date ({invoice_date}) should be close to current date ({today})"
                    )

            # Validate buyer information
            if not invoice.buyer_ntn_cnic and invoice.buyer_type == "Registered":
                warnings.append("Buyer NTN/CNIC missing for registered buyer")

            if not invoice.buyer_name:
                errors.append("Buyer name is required for FBR submission")

            # Validate items
            items_errors = self._validate_invoice_items(invoice_id)
            errors.extend(items_errors)

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return {
            "valid": len(errors) == 0, 
            "errors": errors, 
            "warnings": warnings
        }

    def _validate_invoice_items(self, invoice_id: int) -> List[str]:
        """Validate invoice items"""
        errors = []

        items = (
            self.session.query(SalesInvoiceItem)
            .filter_by(invoice_id=invoice_id)
            .all()
        )

        if not items:
            errors.append("At least one item is required for FBR submission")
            return errors

        for idx, item in enumerate(items, 1):
            if not item.hs_code:
                errors.append(f"Item {idx} ({item.item_name}): HS Code is required")

            if not item.uom:
                errors.append(f"Item {idx} ({item.item_name}): UoM is required")

            if item.quantity <= 0:
                errors.append(f"Item {idx} ({item.item_name}): Quantity must be greater than 0")

            if item.total_value <= 0:
                errors.append(f"Item {idx} ({item.item_name}): Total value must be greater than 0")

            if item.tax_rate is None:
                warnings.append(f"Item {idx} ({item.item_name}): Tax rate not specified")

        return errors


class FBRSubmissionService:
    """Handles FBR API submissions for specific company"""

    def __init__(self, db_manager: DatabaseManager, company_id: str):
        self.db_manager = db_manager
        self.company_id = company_id
        self.session = db_manager.get_session()
        self.payload_builder = CompanySpecificFBRPayloadBuilder(db_manager, company_id)
        self.validator = CompanySpecificFBRValidator(db_manager, company_id)

    def submit_invoice(self, invoice_id: int, mode: str = "sandbox") -> Dict:
        """Submit invoice to FBR"""
        start_time = datetime.utcnow()
        
        try:
            # Validate invoice first
            validation_result = self.validator.validate_invoice(invoice_id)
            
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": "Validation failed",
                    "errors": validation_result["errors"],
                    "warnings": validation_result.get("warnings", [])
                }

            # Build payload
            payload = self.payload_builder.build_sales_invoice_payload(invoice_id, mode)

            # Get FBR settings
            settings = self.session.query(FBRSettings).filter_by(company_id=self.company_id).first()
            if not settings or not settings.api_endpoint:
                return {
                    "success": False,
                    "error": "FBR API settings not configured for this company"
                }

            # Submit to FBR API
            response = self._submit_to_fbr_api(payload, settings, mode)

            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            # Update invoice with response
            self._update_invoice_with_response(invoice_id, response)

            # Log submission
            self._log_submission(
                invoice_id, "Sales Invoice", payload, response, 
                processing_time, mode, settings.api_endpoint
            )

            # Create audit log
            self._create_audit_log("SUBMIT", "sales_invoices", str(invoice_id), response)

            return {"success": True, "response": response}

        except Exception as e:
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            error_msg = str(e)
            
            # Log error
            self._log_submission(
                invoice_id, "Sales Invoice", payload if 'payload' in locals() else {}, 
                {"error": error_msg}, processing_time, mode, 
                settings.api_endpoint if 'settings' in locals() else ""
            )
            
            return {"success": False, "error": error_msg}

    def validate_invoice_with_fbr(self, invoice_id: int, mode: str = "sandbox") -> Dict:
        """Validate invoice using FBR API without submitting"""
        try:
            # Build payload
            payload = self.payload_builder.build_sales_invoice_payload(invoice_id, mode)

            # Get FBR settings
            settings = self.session.query(FBRSettings).filter_by(company_id=self.company_id).first()
            if not settings:
                return {
                    "success": False,
                    "error": "FBR API settings not configured for this company"
                }

            # Use validation endpoint
            validation_url = settings.validation_endpoint or "https://gw.fbr.gov.pk/di_data/v1/di/validateinvoicedata_sb"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.pral_authorization_token}",
            }

            response = requests.post(
                validation_url,
                json=payload,
                headers=headers,
                timeout=settings.timeout_seconds or 30
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Log validation
            self._log_submission(
                invoice_id, "Sales Invoice Validation", payload, result, 0, 
                mode, validation_url, "Validation"
            )
            
            return {"success": True, "response": result}

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"FBR API request failed: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Validation failed: {str(e)}"}

    def _submit_to_fbr_api(self, payload: Dict, settings: FBRSettings, mode: str) -> Dict:
        """Submit to actual FBR API"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.pral_authorization_token}",
        }

        try:
            # For development/testing, you can enable this mock response
            # In production, use the actual API call below
            
            response = requests.post(
                settings.api_endpoint,
                json=payload,
                headers=headers,
                timeout=settings.timeout_seconds or 30
            )
            response.raise_for_status()
            return response.json()

            # Mock response for development (comment out for production)
            # return {
            #     "invoiceNumber": f"FBR{datetime.now().strftime('%Y%m%d%H%M%S')}",
            #     "dated": datetime.now().isoformat(),
            #     "validationResponse": {
            #         "statusCode": "00",
            #         "status": "Valid",
            #         "error": "",
            #         "invoiceStatuses": [
            #             {
            #                 "itemSNo": "1",
            #                 "statusCode": "00", 
            #                 "status": "Valid",
            #                 "invoiceNo": f"FBR{datetime.now().strftime('%Y%m%d%H%M%S')}-1",
            #                 "errorCode": "",
            #                 "error": "",
            #             }
            #         ],
            #     },
            # }

        except requests.exceptions.RequestException as e:
            raise Exception(f"FBR API request failed: {str(e)}")

    def _update_invoice_with_response(self, invoice_id: int, response: Dict):
        """Update invoice with FBR response"""
        try:
            invoice = (
                self.session.query(Invoices)
                .filter_by(id=invoice_id, company_id=self.company_id)
                .first()
            )
            
            if invoice:
                # Update invoice with FBR response data
                invoice.fbr_invoice_number = response.get("invoiceNumber", "")
                
                # Parse FBR datetime
                fbr_dated = response.get("dated", "")
                if fbr_dated:
                    try:
                        # Handle different datetime formats from FBR
                        if "T" in fbr_dated:
                            invoice.fbr_datetime = datetime.fromisoformat(fbr_dated.replace("Z", "+00:00"))
                        else:
                            invoice.fbr_datetime = datetime.strptime(fbr_dated, "%Y-%m-%d %H:%M:%S")
                    except:
                        invoice.fbr_datetime = datetime.utcnow()
                else:
                    invoice.fbr_datetime = datetime.utcnow()
                
                # Update status based on validation response
                validation_response = response.get("validationResponse", {})
                invoice.fbr_status = validation_response.get("status", "Unknown")
                invoice.fbr_response = json.dumps(response, indent=2)
                
                # Update invoice status
                if invoice.fbr_status == "Valid":
                    invoice.status = "Submitted"
                else:
                    invoice.status = "Failed"
                
                invoice.updated_at = datetime.utcnow()
                self.session.commit()
                
        except Exception as e:
            self.session.rollback()
            print(f"Error updating invoice with response: {e}")

    def _log_submission(self, invoice_id: int, document_type: str, payload: Dict, 
                       response: Dict, processing_time: float, mode: str, 
                       api_endpoint: str, status_override: str = None):
        """Enhanced logging with detailed information"""
        try:
            # Determine actual status from response
            if status_override:
                actual_status = status_override
                error_details = ""
            elif response and "validationResponse" in response:
                validation_response = response["validationResponse"]
                actual_status = validation_response.get("status", "Unknown")
                error_details = validation_response.get("error", "")
            elif response and "error" in response:
                actual_status = "Error"
                error_details = response.get("error", "")
            else:
                actual_status = "Success" if response else "Error"
                error_details = ""
            
            log_entry = FBRLogs(
                company_id=self.company_id,
                document_type=document_type,
                document_id=invoice_id,
                fbr_invoice_number=response.get("invoiceNumber", "") if response else "",
                status=actual_status,
                submitted_at=datetime.utcnow(),
                processing_time=processing_time,
                api_endpoint=api_endpoint,
                request_payload=json.dumps(payload, indent=2) if payload else "",
                response_data=json.dumps(response, indent=2) if response else "",
                response_status_code="200" if actual_status in ["Valid", "Success"] else "400",
                validation_errors=error_details,
                mode=mode,
                api_version="v1"
            )
            
            self.session.add(log_entry)
            self.session.commit()
            
        except Exception as e:
            self.session.rollback()
            print(f"Error logging submission: {e}")

    def _create_audit_log(self, action: str, table_name: str, record_id: str, 
                         new_values: Dict):
        """Create audit log entry"""
        try:
            audit_entry = AuditLog(
                company_id=self.company_id,
                action=action,
                table_name=table_name,
                record_id=record_id,
                new_values=json.dumps(new_values, default=str)
            )
            
            self.session.add(audit_entry)
            self.session.commit()
            
        except Exception as e:
            print(f"Error creating audit log: {e}")


class FBRQueueManager:
    """Manages FBR submission queue for specific company"""

    def __init__(self, db_manager: DatabaseManager, company_id: str):
        self.db_manager = db_manager
        self.company_id = company_id
        self.session = db_manager.get_session()
        self.submission_service = CompanySpecificFBRSubmissionService(db_manager, company_id)

    def add_to_queue(self, document_type: str, document_id: int, 
                    priority: int = 5) -> Dict:
        """Add document to FBR queue"""
        try:
            # Check if already in queue
            existing = (
                self.session.query(FBRQueue)
                .filter_by(
                    company_id=self.company_id,
                    document_type=document_type,
                    document_id=document_id,
                    status="Pending"
                )
                .first()
            )

            if existing:
                existing.retry_count += 1
                existing.last_retry_at = datetime.utcnow()
                existing.priority = min(existing.priority, priority)  # Higher priority wins
            else:
                queue_item = FBRQueue(
                    company_id=self.company_id,
                    document_type=document_type,
                    document_id=document_id,
                    status="Pending",
                    priority=priority,
                    created_at=datetime.utcnow()
                )
                self.session.add(queue_item)

            self.session.commit()
            return {"success": True}

        except Exception as e:
            self.session.rollback()
            return {"success": False, "error": str(e)}

    def process_queue(self, limit: int = 50, mode: str = "sandbox") -> Dict:
        """Process pending queue items for this company"""
        try:
            # Get pending items for this company
            queue_items = (
                self.session.query(FBRQueue)
                .filter(
                    FBRQueue.company_id == self.company_id,
                    FBRQueue.status == "Pending",
                    FBRQueue.retry_count < FBRQueue.max_retries
                )
                .order_by(FBRQueue.priority.desc(), FBRQueue.created_at.asc())
                .limit(limit)
                .all()
            )

            processed_count = 0
            failed_count = 0
            errors = []

            for item in queue_items:
                try:
                    # Mark as processing
                    item.status = "Processing"
                    item.last_retry_at = datetime.utcnow()
                    self.session.commit()

                    # Process the item
                    result = self.submission_service.submit_invoice(
                        item.document_id, mode
                    )

                    if result["success"]:
                        item.status = "Completed"
                        item.completed_at = datetime.utcnow()
                        processed_count += 1
                    else:
                        item.retry_count += 1
                        if item.retry_count >= item.max_retries:
                            item.status = "Failed"
                            failed_count += 1
                        else:
                            item.status = "Pending"
                            # Schedule next retry (exponential backoff)
                            retry_delay = min(300, 30 * (2 ** item.retry_count))  # Max 5 minutes
                            item.next_retry_at = datetime.utcnow() + timedelta(seconds=retry_delay)
                        
                        item.error_message = result.get("error", "Unknown error")
                        if result.get("errors"):
                            item.error_message += f" | Errors: {'; '.join(result['errors'])}"

                    self.session.commit()

                except Exception as e:
                    item.status = "Failed"
                    item.error_message = str(e)
                    item.retry_count += 1
                    failed_count += 1
                    errors.append(f"Item {item.id}: {str(e)}")
                    self.session.commit()

            return {
                "processed_count": processed_count,
                "failed_count": failed_count,
                "errors": errors
            }

        except Exception as e:
            return {
                "processed_count": 0, 
                "failed_count": 0,
                "error": str(e)
            }

    def retry_failed_items(self, max_retry_count: int = 3) -> Dict:
        """Retry failed items that haven't exceeded max retries"""
        try:
            # Get failed items that can be retried
            failed_items = (
                self.session.query(FBRQueue)
                .filter(
                    FBRQueue.company_id == self.company_id,
                    FBRQueue.status == "Failed",
                    FBRQueue.retry_count < max_retry_count
                )
                .all()
            )

            retry_count = 0
            for item in failed_items:
                item.status = "Pending"
                item.next_retry_at = datetime.utcnow() + timedelta(minutes=5)
                retry_count += 1

            self.session.commit()
            return {"success": True, "retry_count": retry_count}

        except Exception as e:
            self.session.rollback()
            return {"success": False, "error": str(e)}

    def clear_completed_items(self, older_than_days: int = 7) -> Dict:
        """Clear completed queue items older than specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
            
            deleted_count = (
                self.session.query(FBRQueue)
                .filter(
                    FBRQueue.company_id == self.company_id,
                    FBRQueue.status == "Completed",
                    FBRQueue.completed_at < cutoff_date
                )
                .delete()
            )

            self.session.commit()
            return {"success": True, "deleted_count": deleted_count}

        except Exception as e:
            self.session.rollback()
            return {"success": False, "error": str(e)}

    def get_queue_status(self) -> Dict:
        """Get queue status for this company"""
        try:
            status_counts = {}
            
            # Get counts by status
            results = (
                self.session.query(FBRQueue.status, self.session.query(FBRQueue).filter_by(company_id=self.company_id).count())
                .filter_by(company_id=self.company_id)
                .group_by(FBRQueue.status)
                .all()
            )

            for status, count in results:
                status_counts[status] = count

            return {"success": True, "status_counts": status_counts}

        except Exception as e:
            return {"success": False, "error": str(e)}


# Convenience functions for company-specific operations
def get_company_fbr_service(db_manager: DatabaseManager, company_id: str):
    """Get FBR service instance for specific company"""
    return CompanySpecificFBRSubmissionService(db_manager, company_id)


def get_company_fbr_queue_manager(db_manager: DatabaseManager, company_id: str):
    """Get FBR queue manager for specific company"""
    return CompanySpecificFBRQueueManager(db_manager, company_id)


def process_company_queue(db_manager: DatabaseManager, company_id: str, 
                         limit: int = 50, mode: str = "sandbox") -> Dict:
    """Process FBR queue for specific company"""
    queue_manager = CompanySpecificFBRQueueManager(db_manager, company_id)
    return queue_manager.process_queue(limit, mode)


def submit_company_invoice(db_manager: DatabaseManager, company_id: str, 
                          invoice_id: int, mode: str = "sandbox") -> Dict:
    """Submit invoice for specific company"""
    service = CompanySpecificFBRSubmissionService(db_manager, company_id)
    return service.submit_invoice(invoice_id, mode)


def validate_company_invoice(db_manager: DatabaseManager, company_id: str, 
                           invoice_id: int, mode: str = "sandbox") -> Dict:
    """Validate invoice for specific company"""
    service = CompanySpecificFBRSubmissionService(db_manager, company_id)
    return service.validate_invoice_with_fbr(invoice_id, mode)