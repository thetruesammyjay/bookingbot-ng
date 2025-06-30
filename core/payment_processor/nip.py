"""
NIP (Nigeria Inter-Bank Settlement System) verification for BookingBot NG
Handles bank transfer verification and validation for Nigerian payments
"""

import os
import re
import time
import uuid
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime, timedelta

import requests
from loguru import logger

from .exceptions import PaymentError, PaymentValidationError, PaymentProviderError


class NIPVerifier:
    """
    Nigerian Inter-Bank Settlement System (NIBSS) integration
    Handles bank transfer verification and account validation
    """
    
    def __init__(self, api_key: Optional[str] = None, sandbox: bool = True):
        self.api_key = api_key or os.getenv("NIBSS_API_KEY")
        self.sandbox = sandbox
        
        # NIBSS endpoints (sandbox vs production)
        if sandbox:
            self.base_url = "https://sandbox.nibss-plc.com.ng"
        else:
            self.base_url = "https://api.nibss-plc.com.ng"
        
        if not self.api_key:
            logger.warning("NIBSS API key not configured - NIP verification will be simulated")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for NIBSS API requests"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "BookingBot-NG/1.0"
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to NIBSS API"""
        
        if not self.api_key:
            # Simulate API response for development
            return self._simulate_nibss_response(endpoint, data)
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=data, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            else:
                raise PaymentError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            raise PaymentProviderError("Request to NIBSS timed out")
        except requests.exceptions.ConnectionError:
            raise PaymentProviderError("Failed to connect to NIBSS")
        except requests.exceptions.HTTPError as e:
            error_data = {}
            try:
                error_data = response.json()
            except:
                pass
            
            raise PaymentProviderError(
                f"NIBSS API error: {e}",
                provider_response=error_data
            )
    
    def verify_account_number(self, account_number: str, bank_code: str) -> Dict[str, Any]:
        """Verify bank account number and get account details"""
        
        # Validate inputs
        if not self._validate_account_number(account_number):
            raise PaymentValidationError("Invalid account number format")
        
        if not self._validate_bank_code(bank_code):
            raise PaymentValidationError("Invalid bank code")
        
        data = {
            "accountNumber": account_number,
            "bankCode": bank_code
        }
        
        logger.info(f"Verifying account: {account_number} at bank {bank_code}")
        
        response = self._make_request("POST", "/accounts/verify", data)
        
        if not response.get("success"):
            raise PaymentProviderError(
                f"Failed to verify account: {response.get('message', 'Unknown error')}",
                provider_response=response
            )
        
        return response["data"]
    
    def verify_bvn(self, bvn: str, date_of_birth: str) -> Dict[str, Any]:
        """Verify Bank Verification Number (BVN)"""
        
        if not self._validate_bvn(bvn):
            raise PaymentValidationError("Invalid BVN format")
        
        data = {
            "bvn": bvn,
            "dateOfBirth": date_of_birth  # Format: YYYY-MM-DD
        }
        
        logger.info(f"Verifying BVN: {bvn[:3]}********")
        
        response = self._make_request("POST", "/bvn/verify", data)
        
        if not response.get("success"):
            raise PaymentProviderError(
                f"BVN verification failed: {response.get('message', 'Unknown error')}",
                provider_response=response
            )
        
        return response["data"]
    
    def verify_nin(self, nin: str) -> Dict[str, Any]:
        """Verify National Identification Number (NIN)"""
        
        if not self._validate_nin(nin):
            raise PaymentValidationError("Invalid NIN format")
        
        data = {"nin": nin}
        
        logger.info(f"Verifying NIN: {nin[:3]}********")
        
        response = self._make_request("POST", "/nin/verify", data)
        
        if not response.get("success"):
            raise PaymentProviderError(
                f"NIN verification failed: {response.get('message', 'Unknown error')}",
                provider_response=response
            )
        
        return response["data"]
    
    def initiate_bank_transfer_verification(
        self,
        amount: Decimal,
        sender_account: str,
        sender_bank: str,
        recipient_account: str,
        recipient_bank: str,
        reference: str,
        narration: str
    ) -> Dict[str, Any]:
        """Initiate bank transfer verification session"""
        
        data = {
            "amount": str(amount),
            "senderAccountNumber": sender_account,
            "senderBankCode": sender_bank,
            "recipientAccountNumber": recipient_account,
            "recipientBankCode": recipient_bank,
            "reference": reference,
            "narration": narration,
            "sessionId": str(uuid.uuid4())
        }
        
        logger.info(f"Initiating transfer verification: {reference}")
        
        response = self._make_request("POST", "/transfers/initiate", data)
        
        if not response.get("success"):
            raise PaymentProviderError(
                f"Failed to initiate transfer verification: {response.get('message', 'Unknown error')}",
                provider_response=response
            )
        
        return response["data"]
    
    def check_transfer_status(self, session_id: str, reference: str) -> Dict[str, Any]:
        """Check the status of a bank transfer verification"""
        
        params = {
            "sessionId": session_id,
            "reference": reference
        }
        
        logger.info(f"Checking transfer status: {reference}")
        
        response = self._make_request("GET", "/transfers/status", params)
        
        if not response.get("success"):
            raise PaymentProviderError(
                f"Failed to check transfer status: {response.get('message', 'Unknown error')}",
                provider_response=response
            )
        
        return response["data"]
    
    def get_bank_list(self) -> List[Dict[str, Any]]:
        """Get list of Nigerian banks with their codes"""
        
        response = self._make_request("GET", "/banks")
        
        if not response.get("success"):
            raise PaymentProviderError(
                f"Failed to get bank list: {response.get('message', 'Unknown error')}",
                provider_response=response
            )
        
        return response["data"]
    
    def validate_transfer_details(
        self,
        account_number: str,
        bank_code: str,
        amount: Decimal,
        purpose_code: str = "01"  # General purpose
    ) -> Dict[str, Any]:
        """Validate transfer details before processing"""
        
        # Check account validity
        account_info = self.verify_account_number(account_number, bank_code)
        
        # Validate amount
        if amount <= 0:
            raise PaymentValidationError("Transfer amount must be greater than zero")
        
        # Check transfer limits (Nigerian CBN limits)
        daily_limit = Decimal("5000000")  # ₦5M daily limit for individuals
        if amount > daily_limit:
            raise PaymentValidationError(f"Amount exceeds daily transfer limit of ₦{daily_limit:,.2f}")
        
        return {
            "valid": True,
            "account_name": account_info.get("accountName"),
            "bank_name": account_info.get("bankName"),
            "amount": amount,
            "fees": self._calculate_transfer_fees(amount)
        }
    
    def _calculate_transfer_fees(self, amount: Decimal) -> Dict[str, Decimal]:
        """Calculate NIP transfer fees based on CBN guidelines"""
        
        # Nigerian Central Bank NIP fee structure (as of 2024)
        if amount <= Decimal("5000"):
            nip_fee = Decimal("10")
        elif amount <= Decimal("50000"):
            nip_fee = Decimal("25")
        else:
            nip_fee = Decimal("50")
        
        # VAT on fees (7.5%)
        vat = nip_fee * Decimal("0.075")
        
        return {
            "nip_fee": nip_fee,
            "vat": vat,
            "total_fees": nip_fee + vat
        }
    
    def _validate_account_number(self, account_number: str) -> bool:
        """Validate Nigerian account number format"""
        # Nigerian account numbers are typically 10 digits
        return bool(re.match(r'^\d{10}$', account_number))
    
    def _validate_bank_code(self, bank_code: str) -> bool:
        """Validate Nigerian bank code format"""
        # Nigerian bank codes are typically 3 digits
        return bool(re.match(r'^\d{3}$', bank_code))
    
    def _validate_bvn(self, bvn: str) -> bool:
        """Validate Bank Verification Number format"""
        # BVN is 11 digits
        return bool(re.match(r'^\d{11}$', bvn))
    
    def _validate_nin(self, nin: str) -> bool:
        """Validate National Identification Number format"""
        # NIN is 11 digits
        return bool(re.match(r'^\d{11}$', nin))
    
    def _simulate_nibss_response(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Simulate NIBSS API responses for development"""
        
        logger.info(f"Simulating NIBSS response for {endpoint}")
        
        if "accounts/verify" in endpoint:
            return {
                "success": True,
                "data": {
                    "accountName": "JOHN DOE",
                    "accountNumber": data.get("accountNumber"),
                    "bankName": "GUARANTY TRUST BANK PLC",
                    "bankCode": data.get("bankCode"),
                    "verified": True
                }
            }
        
        elif "bvn/verify" in endpoint:
            return {
                "success": True,
                "data": {
                    "bvn": data.get("bvn"),
                    "firstName": "JOHN",
                    "lastName": "DOE",
                    "dateOfBirth": data.get("dateOfBirth"),
                    "phoneNumber": "+2348012345678",
                    "verified": True
                }
            }
        
        elif "nin/verify" in endpoint:
            return {
                "success": True,
                "data": {
                    "nin": data.get("nin"),
                    "firstName": "JOHN",
                    "lastName": "DOE",
                    "verified": True
                }
            }
        
        elif "transfers/initiate" in endpoint:
            return {
                "success": True,
                "data": {
                    "sessionId": str(uuid.uuid4()),
                    "reference": data.get("reference"),
                    "status": "initiated",
                    "message": "Transfer verification initiated"
                }
            }
        
        elif "transfers/status" in endpoint:
            return {
                "success": True,
                "data": {
                    "sessionId": data.get("sessionId"),
                    "reference": data.get("reference"),
                    "status": "completed",
                    "verified": True,
                    "message": "Transfer verified successfully"
                }
            }
        
        elif "banks" in endpoint:
            return {
                "success": True,
                "data": [
                    {"name": "ACCESS BANK PLC", "code": "044"},
                    {"name": "GUARANTY TRUST BANK PLC", "code": "058"},
                    {"name": "UNITED BANK FOR AFRICA PLC", "code": "033"},
                    {"name": "ZENITH BANK PLC", "code": "057"},
                    {"name": "FIRST BANK OF NIGERIA LIMITED", "code": "011"}
                ]
            }
        
        return {
            "success": False,
            "message": "Endpoint not supported in simulation"
        }


class BankTransferValidator:
    """Validate and process bank transfer payments"""
    
    def __init__(self, nip_verifier: NIPVerifier):
        self.nip_verifier = nip_verifier
    
    def validate_transfer_notification(
        self,
        notification_data: Dict[str, Any],
        expected_amount: Decimal,
        expected_reference: str,
        recipient_account: str
    ) -> Dict[str, Any]:
        """Validate a bank transfer notification"""
        
        # Extract notification details
        transfer_amount = Decimal(str(notification_data.get("amount", "0")))
        transfer_reference = notification_data.get("reference", "")
        transfer_account = notification_data.get("recipientAccount", "")
        sender_name = notification_data.get("senderName", "")
        sender_account = notification_data.get("senderAccount", "")
        sender_bank = notification_data.get("senderBank", "")
        
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "transfer_details": notification_data
        }
        
        # Validate amount
        if transfer_amount != expected_amount:
            validation_result["valid"] = False
            validation_result["errors"].append(
                f"Amount mismatch: expected ₦{expected_amount}, received ₦{transfer_amount}"
            )
        
        # Validate reference
        if expected_reference.lower() not in transfer_reference.lower():
            validation_result["valid"] = False
            validation_result["errors"].append(
                f"Reference mismatch: expected '{expected_reference}', received '{transfer_reference}'"
            )
        
        # Validate recipient account
        if transfer_account != recipient_account:
            validation_result["valid"] = False
            validation_result["errors"].append(
                f"Account mismatch: expected '{recipient_account}', received '{transfer_account}'"
            )
        
        # Additional validations
        if not sender_name:
            validation_result["warnings"].append("Sender name not provided")
        
        if not sender_account:
            validation_result["warnings"].append("Sender account not provided")
        
        # Verify sender account if provided
        if sender_account and sender_bank:
            try:
                account_info = self.nip_verifier.verify_account_number(sender_account, sender_bank)
                validation_result["sender_verified"] = True
                validation_result["sender_details"] = account_info
            except Exception as e:
                validation_result["warnings"].append(f"Could not verify sender account: {str(e)}")
                validation_result["sender_verified"] = False
        
        return validation_result
    
    def generate_payment_instructions(
        self,
        amount: Decimal,
        reference: str,
        recipient_account: str,
        recipient_bank: str,
        recipient_name: str
    ) -> Dict[str, Any]:
        """Generate payment instructions for customer"""
        
        fees = self.nip_verifier._calculate_transfer_fees(amount)
        
        return {
            "payment_method": "bank_transfer",
            "amount": amount,
            "reference": reference,
            "recipient": {
                "account_number": recipient_account,
                "account_name": recipient_name,
                "bank_name": recipient_bank,
                "bank_code": self._get_bank_code_by_name(recipient_bank)
            },
            "fees": fees,
            "instructions": [
                f"Transfer ₦{amount:,.2f} to the account details above",
                f"Use reference: {reference}",
                "Ensure the reference is included in your transfer description",
                "Your payment will be verified automatically",
                "Contact support if payment is not confirmed within 30 minutes"
            ],
            "expected_total": amount + fees["total_fees"],
            "expires_at": datetime.utcnow() + timedelta(hours=24)
        }
    
    def _get_bank_code_by_name(self, bank_name: str) -> str:
        """Get bank code by bank name"""
        # This is a simplified mapping - in production you'd use the NIBSS bank list
        bank_codes = {
            "ACCESS BANK": "044",
            "GUARANTY TRUST BANK": "058",
            "UNITED BANK FOR AFRICA": "033",
            "ZENITH BANK": "057",
            "FIRST BANK OF NIGERIA": "011",
            "FIRST CITY MONUMENT BANK": "214"
        }
        
        for bank, code in bank_codes.items():
            if bank in bank_name.upper():
                return code
        
        return "000"  # Unknown bank code


# Nigerian bank holidays that affect transfer processing
NIGERIAN_BANK_HOLIDAYS = [
    "01-01",  # New Year's Day
    "10-01",  # Armed Forces Remembrance Day  
    "05-01",  # Workers' Day
    "06-12",  # Democracy Day
    "10-01",  # Independence Day
    "12-25",  # Christmas Day
    "12-26",  # Boxing Day
    # Note: Religious holidays like Eid vary by year
]


def is_banking_day(date: datetime) -> bool:
    """Check if a date is a banking day in Nigeria"""
    
    # Check if it's a weekend
    if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Check if it's a public holiday
    date_str = date.strftime("%m-%d")
    if date_str in NIGERIAN_BANK_HOLIDAYS:
        return False
    
    return True


def get_next_banking_day(date: datetime) -> datetime:
    """Get the next banking day after the given date"""
    
    next_day = date + timedelta(days=1)
    
    while not is_banking_day(next_day):
        next_day += timedelta(days=1)
    
    return next_day


def estimate_transfer_time(amount: Decimal, bank_code: str) -> Dict[str, Any]:
    """Estimate transfer processing time based on amount and bank"""
    
    # NIP transfers are typically instant, but can have delays
    base_minutes = 5  # Base processing time
    
    # Large amounts may take longer
    if amount > Decimal("1000000"):  # Over ₦1M
        base_minutes += 15
    elif amount > Decimal("500000"):  # Over ₦500K
        base_minutes += 10
    
    # Some banks are faster than others
    fast_banks = ["058", "033", "044", "057"]  # GTB, UBA, Access, Zenith
    if bank_code not in fast_banks:
        base_minutes += 10
    
    return {
        "estimated_minutes": base_minutes,
        "estimated_completion": datetime.utcnow() + timedelta(minutes=base_minutes),
        "maximum_minutes": base_minutes * 3,  # Maximum expected time
        "notes": [
            "NIP transfers are typically processed within 5-30 minutes",
            "Large amounts may require additional verification",
            "Transfers outside banking hours may be delayed"
        ]
    }