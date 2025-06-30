"""
Paystack integration for BookingBot NG
Handles Nigerian payments via Paystack API including cards, bank transfers, and USSD
"""

import os
import hmac
import hashlib
import json
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime, timedelta

import requests
from loguru import logger

from .models import PaymentTransaction, PaymentStatus, PaymentMethod
from .exceptions import PaymentError, PaymentProviderError, PaymentValidationError


class PaystackClient:
    """Paystack API client for Nigerian payments"""
    
    def __init__(self, secret_key: Optional[str] = None, public_key: Optional[str] = None):
        self.secret_key = secret_key or os.getenv("PAYSTACK_SECRET_KEY")
        self.public_key = public_key or os.getenv("PAYSTACK_PUBLIC_KEY")
        self.base_url = "https://api.paystack.co"
        
        if not self.secret_key:
            raise PaymentError("Paystack secret key not configured")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Paystack API requests"""
        return {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
            "User-Agent": "BookingBot-NG/1.0"
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to Paystack API"""
        
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=data, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=30)
            else:
                raise PaymentError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            raise PaymentProviderError("Request to Paystack timed out")
        except requests.exceptions.ConnectionError:
            raise PaymentProviderError("Failed to connect to Paystack")
        except requests.exceptions.HTTPError as e:
            error_data = {}
            try:
                error_data = response.json()
            except:
                pass
            
            raise PaymentProviderError(
                f"Paystack API error: {e}",
                provider_response=error_data
            )
    
    def initialize_transaction(
        self,
        amount: Decimal,
        email: str,
        reference: str,
        callback_url: Optional[str] = None,
        metadata: Optional[Dict] = None,
        channels: Optional[List[str]] = None,
        currency: str = "NGN"
    ) -> Dict[str, Any]:
        """Initialize a new payment transaction"""
        
        # Convert amount to kobo (Paystack uses kobo, not naira)
        amount_kobo = int(amount * 100)
        
        data = {
            "amount": amount_kobo,
            "email": email,
            "reference": reference,
            "currency": currency,
        }
        
        if callback_url:
            data["callback_url"] = callback_url
        
        if metadata:
            data["metadata"] = metadata
        
        if channels:
            data["channels"] = channels
        
        logger.info(f"Initializing Paystack transaction: {reference} for ₦{amount}")
        
        response = self._make_request("POST", "/transaction/initialize", data)
        
        if not response.get("status"):
            raise PaymentProviderError(
                f"Failed to initialize transaction: {response.get('message', 'Unknown error')}",
                provider_response=response
            )
        
        return response["data"]
    
    def verify_transaction(self, reference: str) -> Dict[str, Any]:
        """Verify a transaction status"""
        
        logger.info(f"Verifying Paystack transaction: {reference}")
        
        response = self._make_request("GET", f"/transaction/verify/{reference}")
        
        if not response.get("status"):
            raise PaymentProviderError(
                f"Failed to verify transaction: {response.get('message', 'Unknown error')}",
                provider_response=response
            )
        
        return response["data"]
    
    def list_transactions(
        self,
        per_page: int = 50,
        page: int = 1,
        customer: Optional[str] = None,
        status: Optional[str] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """List transactions with filters"""
        
        params = {
            "perPage": per_page,
            "page": page
        }
        
        if customer:
            params["customer"] = customer
        
        if status:
            params["status"] = status
        
        if from_date:
            params["from"] = from_date.isoformat()
        
        if to_date:
            params["to"] = to_date.isoformat()
        
        response = self._make_request("GET", "/transaction", params)
        
        if not response.get("status"):
            raise PaymentProviderError(
                f"Failed to list transactions: {response.get('message', 'Unknown error')}",
                provider_response=response
            )
        
        return response["data"]
    
    def charge_authorization(
        self,
        authorization_code: str,
        amount: Decimal,
        email: str,
        reference: str,
        currency: str = "NGN"
    ) -> Dict[str, Any]:
        """Charge a previously authorized card"""
        
        amount_kobo = int(amount * 100)
        
        data = {
            "authorization_code": authorization_code,
            "amount": amount_kobo,
            "email": email,
            "reference": reference,
            "currency": currency
        }
        
        logger.info(f"Charging authorization: {reference} for ₦{amount}")
        
        response = self._make_request("POST", "/transaction/charge_authorization", data)
        
        if not response.get("status"):
            raise PaymentProviderError(
                f"Failed to charge authorization: {response.get('message', 'Unknown error')}",
                provider_response=response
            )
        
        return response["data"]
    
    def create_transfer_recipient(
        self,
        type: str,
        name: str,
        account_number: str,
        bank_code: str,
        currency: str = "NGN"
    ) -> Dict[str, Any]:
        """Create a transfer recipient for payouts"""
        
        data = {
            "type": type,
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": currency
        }
        
        response = self._make_request("POST", "/transferrecipient", data)
        
        if not response.get("status"):
            raise PaymentProviderError(
                f"Failed to create transfer recipient: {response.get('message', 'Unknown error')}",
                provider_response=response
            )
        
        return response["data"]
    
    def initiate_transfer(
        self,
        amount: Decimal,
        recipient: str,
        reason: Optional[str] = None,
        currency: str = "NGN"
    ) -> Dict[str, Any]:
        """Initiate a transfer to a recipient"""
        
        amount_kobo = int(amount * 100)
        
        data = {
            "source": "balance",
            "amount": amount_kobo,
            "recipient": recipient,
            "currency": currency
        }
        
        if reason:
            data["reason"] = reason
        
        response = self._make_request("POST", "/transfer", data)
        
        if not response.get("status"):
            raise PaymentProviderError(
                f"Failed to initiate transfer: {response.get('message', 'Unknown error')}",
                provider_response=response
            )
        
        return response["data"]
    
    def list_banks(self, country: str = "nigeria") -> List[Dict[str, Any]]:
        """Get list of Nigerian banks"""
        
        params = {"country": country}
        response = self._make_request("GET", "/bank", params)
        
        if not response.get("status"):
            raise PaymentProviderError(
                f"Failed to get banks: {response.get('message', 'Unknown error')}",
                provider_response=response
            )
        
        return response["data"]
    
    def resolve_account_number(self, account_number: str, bank_code: str) -> Dict[str, Any]:
        """Resolve bank account number to get account name"""
        
        params = {
            "account_number": account_number,
            "bank_code": bank_code
        }
        
        response = self._make_request("GET", "/bank/resolve", params)
        
        if not response.get("status"):
            raise PaymentProviderError(
                f"Failed to resolve account: {response.get('message', 'Unknown error')}",
                provider_response=response
            )
        
        return response["data"]
    
    def create_customer(
        self,
        email: str,
        first_name: str,
        last_name: str,
        phone: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a customer on Paystack"""
        
        data = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name
        }
        
        if phone:
            data["phone"] = phone
        
        if metadata:
            data["metadata"] = metadata
        
        response = self._make_request("POST", "/customer", data)
        
        if not response.get("status"):
            raise PaymentProviderError(
                f"Failed to create customer: {response.get('message', 'Unknown error')}",
                provider_response=response
            )
        
        return response["data"]
    
    def validate_webhook(self, payload: bytes, signature: str) -> bool:
        """Validate Paystack webhook signature"""
        
        expected_signature = hmac.new(
            self.secret_key.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected_signature)
    
    def get_payment_channels(self) -> List[str]:
        """Get available payment channels for Nigerian market"""
        return [
            "card",           # Debit/credit cards
            "bank",           # Bank transfers
            "ussd",           # USSD payments
            "bank_transfer",  # Direct bank transfers
            "qr"              # QR code payments
        ]


class PaystackWebhookHandler:
    """Handle Paystack webhook events"""
    
    def __init__(self, paystack_client: PaystackClient):
        self.client = paystack_client
    
    def handle_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Process incoming webhook from Paystack"""
        
        # Validate webhook signature
        if not self.client.validate_webhook(payload, signature):
            raise PaymentValidationError("Invalid webhook signature")
        
        try:
            event_data = json.loads(payload.decode('utf-8'))
        except json.JSONDecodeError:
            raise PaymentValidationError("Invalid JSON in webhook payload")
        
        event_type = event_data.get("event")
        if not event_type:
            raise PaymentValidationError("No event type in webhook")
        
        logger.info(f"Processing Paystack webhook: {event_type}")
        
        # Route to appropriate handler
        handler_map = {
            "charge.success": self._handle_charge_success,
            "charge.failed": self._handle_charge_failed,
            "transfer.success": self._handle_transfer_success,
            "transfer.failed": self._handle_transfer_failed,
            "transfer.reversed": self._handle_transfer_reversed,
            "invoice.create": self._handle_invoice_create,
            "invoice.payment_failed": self._handle_invoice_payment_failed,
            "subscription.create": self._handle_subscription_create,
            "subscription.disable": self._handle_subscription_disable
        }
        
        handler = handler_map.get(event_type)
        if handler:
            return handler(event_data)
        else:
            logger.warning(f"Unhandled Paystack webhook event: {event_type}")
            return {"status": "ignored", "message": f"Event {event_type} not handled"}
    
    def _handle_charge_success(self, event_data: Dict) -> Dict[str, Any]:
        """Handle successful charge"""
        data = event_data.get("data", {})
        reference = data.get("reference")
        
        if not reference:
            raise PaymentValidationError("No reference in charge success event")
        
        logger.info(f"Charge successful: {reference}")
        
        # Here you would update your payment transaction status
        # This would integrate with your PaymentTransaction model
        
        return {
            "status": "processed",
            "reference": reference,
            "action": "charge_success"
        }
    
    def _handle_charge_failed(self, event_data: Dict) -> Dict[str, Any]:
        """Handle failed charge"""
        data = event_data.get("data", {})
        reference = data.get("reference")
        
        logger.info(f"Charge failed: {reference}")
        
        return {
            "status": "processed",
            "reference": reference,
            "action": "charge_failed"
        }
    
    def _handle_transfer_success(self, event_data: Dict) -> Dict[str, Any]:
        """Handle successful transfer"""
        data = event_data.get("data", {})
        transfer_code = data.get("transfer_code")
        
        logger.info(f"Transfer successful: {transfer_code}")
        
        return {
            "status": "processed",
            "transfer_code": transfer_code,
            "action": "transfer_success"
        }
    
    def _handle_transfer_failed(self, event_data: Dict) -> Dict[str, Any]:
        """Handle failed transfer"""
        data = event_data.get("data", {})
        transfer_code = data.get("transfer_code")
        
        logger.info(f"Transfer failed: {transfer_code}")
        
        return {
            "status": "processed",
            "transfer_code": transfer_code,
            "action": "transfer_failed"
        }
    
    def _handle_transfer_reversed(self, event_data: Dict) -> Dict[str, Any]:
        """Handle reversed transfer"""
        data = event_data.get("data", {})
        transfer_code = data.get("transfer_code")
        
        logger.info(f"Transfer reversed: {transfer_code}")
        
        return {
            "status": "processed",
            "transfer_code": transfer_code,
            "action": "transfer_reversed"
        }
    
    def _handle_invoice_create(self, event_data: Dict) -> Dict[str, Any]:
        """Handle invoice creation"""
        data = event_data.get("data", {})
        invoice_code = data.get("invoice_code")
        
        logger.info(f"Invoice created: {invoice_code}")
        
        return {
            "status": "processed",
            "invoice_code": invoice_code,
            "action": "invoice_create"
        }
    
    def _handle_invoice_payment_failed(self, event_data: Dict) -> Dict[str, Any]:
        """Handle failed invoice payment"""
        data = event_data.get("data", {})
        invoice_code = data.get("invoice_code")
        
        logger.info(f"Invoice payment failed: {invoice_code}")
        
        return {
            "status": "processed",
            "invoice_code": invoice_code,
            "action": "invoice_payment_failed"
        }
    
    def _handle_subscription_create(self, event_data: Dict) -> Dict[str, Any]:
        """Handle subscription creation"""
        data = event_data.get("data", {})
        subscription_code = data.get("subscription_code")
        
        logger.info(f"Subscription created: {subscription_code}")
        
        return {
            "status": "processed",
            "subscription_code": subscription_code,
            "action": "subscription_create"
        }
    
    def _handle_subscription_disable(self, event_data: Dict) -> Dict[str, Any]:
        """Handle subscription disable"""
        data = event_data.get("data", {})
        subscription_code = data.get("subscription_code")
        
        logger.info(f"Subscription disabled: {subscription_code}")
        
        return {
            "status": "processed",
            "subscription_code": subscription_code,
            "action": "subscription_disable"
        }


# Nigerian bank codes for reference
NIGERIAN_BANKS = {
    "access_bank": "044",
    "citi_bank": "023", 
    "diamond_bank": "063",
    "ecobank": "050",
    "fbn": "011",
    "fcmb": "214",
    "fidelity_bank": "070",
    "gtbank": "058",
    "heritage_bank": "030",
    "keystone_bank": "082",
    "polaris_bank": "076",
    "providus_bank": "101",
    "stanbic_ibtc": "221",
    "standard_chartered": "068",
    "sterling_bank": "232",
    "union_bank": "032",
    "uba": "033",
    "unity_bank": "215",
    "wema_bank": "035",
    "zenith_bank": "057"
}


def get_bank_code(bank_name: str) -> Optional[str]:
    """Get bank code by name (case-insensitive)"""
    bank_key = bank_name.lower().replace(" ", "_")
    return NIGERIAN_BANKS.get(bank_key)


def kobo_to_naira(kobo: int) -> Decimal:
    """Convert kobo to naira"""
    return Decimal(kobo) / 100


def naira_to_kobo(naira: Decimal) -> int:
    """Convert naira to kobo"""
    return int(naira * 100)