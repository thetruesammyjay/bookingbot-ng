"""
Payment-specific exceptions for BookingBot NG
Handles errors related to payment processing, Nigerian banking, and provider integrations
"""

from typing import Optional, Dict, Any
from decimal import Decimal


class PaymentError(Exception):
    """Base exception for payment-related errors"""
    
    def __init__(
        self, 
        message: str, 
        code: Optional[str] = None, 
        details: Optional[Dict[str, Any]] = None,
        amount: Optional[Decimal] = None,
        reference: Optional[str] = None
    ):
        self.message = message
        self.code = code or "PAYMENT_ERROR"
        self.details = details or {}
        self.amount = amount
        self.reference = reference
        super().__init__(self.message)


class PaymentValidationError(PaymentError):
    """Raised when payment validation fails"""
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None, 
        value: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if field:
            details["field"] = field
        if value:
            details["value"] = value
        
        super().__init__(
            message, 
            code="PAYMENT_VALIDATION_ERROR", 
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"}
        )


class PaymentProviderError(PaymentError):
    """Raised when payment provider (Paystack, NIBSS, etc.) returns an error"""
    
    def __init__(
        self, 
        message: str, 
        provider: Optional[str] = None,
        provider_response: Optional[Dict] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if provider:
            details["provider"] = provider
        if provider_response:
            details["provider_response"] = provider_response
        
        super().__init__(
            message, 
            code="PAYMENT_PROVIDER_ERROR", 
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"}
        )


class PaymentNotFoundError(PaymentError):
    """Raised when payment transaction is not found"""
    
    def __init__(self, reference: str):
        super().__init__(
            f"Payment transaction not found: {reference}",
            code="PAYMENT_NOT_FOUND",
            details={"reference": reference},
            reference=reference
        )


class PaymentAlreadyProcessedError(PaymentError):
    """Raised when attempting to process an already processed payment"""
    
    def __init__(self, reference: str, current_status: str):
        super().__init__(
            f"Payment {reference} already processed with status: {current_status}",
            code="PAYMENT_ALREADY_PROCESSED",
            details={"reference": reference, "current_status": current_status},
            reference=reference
        )


class PaymentExpiredError(PaymentError):
    """Raised when payment has expired"""
    
    def __init__(self, reference: str, expired_at: str):
        super().__init__(
            f"Payment {reference} expired at {expired_at}",
            code="PAYMENT_EXPIRED",
            details={"reference": reference, "expired_at": expired_at},
            reference=reference
        )


class InsufficientFundsError(PaymentError):
    """Raised when customer has insufficient funds"""
    
    def __init__(self, amount: Decimal, available: Optional[Decimal] = None):
        message = f"Insufficient funds for ₦{amount:,.2f}"
        if available:
            message += f" (available: ₦{available:,.2f})"
        
        super().__init__(
            message,
            code="INSUFFICIENT_FUNDS",
            details={"requested_amount": str(amount), "available_amount": str(available) if available else None},
            amount=amount
        )


class PaymentMethodNotSupportedError(PaymentError):
    """Raised when payment method is not supported"""
    
    def __init__(self, payment_method: str, tenant_id: Optional[str] = None):
        super().__init__(
            f"Payment method '{payment_method}' is not supported",
            code="PAYMENT_METHOD_NOT_SUPPORTED",
            details={"payment_method": payment_method, "tenant_id": tenant_id}
        )


class PaymentLimitExceededError(PaymentError):
    """Raised when payment exceeds limits"""
    
    def __init__(
        self, 
        amount: Decimal, 
        limit: Decimal, 
        limit_type: str,
        period: Optional[str] = None
    ):
        message = f"Payment amount ₦{amount:,.2f} exceeds {limit_type} limit of ₦{limit:,.2f}"
        if period:
            message += f" for {period}"
        
        super().__init__(
            message,
            code="PAYMENT_LIMIT_EXCEEDED",
            details={
                "amount": str(amount),
                "limit": str(limit),
                "limit_type": limit_type,
                "period": period
            },
            amount=amount
        )


class RefundError(PaymentError):
    """Raised for refund-related errors"""
    
    def __init__(self, message: str, refund_reference: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if refund_reference:
            details["refund_reference"] = refund_reference
        
        super().__init__(
            message,
            code="REFUND_ERROR",
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"}
        )


class RefundNotAllowedError(RefundError):
    """Raised when refund is not allowed for the payment"""
    
    def __init__(self, reference: str, reason: str):
        super().__init__(
            f"Refund not allowed for payment {reference}: {reason}",
            code="REFUND_NOT_ALLOWED",
            details={"payment_reference": reference, "reason": reason},
            reference=reference
        )


class PartialRefundNotSupportedError(RefundError):
    """Raised when partial refunds are not supported"""
    
    def __init__(self, reference: str, provider: str):
        super().__init__(
            f"Partial refunds not supported by {provider} for payment {reference}",
            code="PARTIAL_REFUND_NOT_SUPPORTED",
            details={"payment_reference": reference, "provider": provider},
            reference=reference
        )


# Nigerian Banking Specific Exceptions

class NigerianBankingError(PaymentError):
    """Base exception for Nigerian banking errors"""
    
    def __init__(self, message: str, bank_code: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if bank_code:
            details["bank_code"] = bank_code
        
        super().__init__(
            message,
            code="NIGERIAN_BANKING_ERROR",
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"}
        )


class InvalidAccountNumberError(NigerianBankingError):
    """Raised when Nigerian account number is invalid"""
    
    def __init__(self, account_number: str, bank_code: Optional[str] = None):
        super().__init__(
            f"Invalid account number: {account_number}",
            code="INVALID_ACCOUNT_NUMBER",
            details={"account_number": account_number},
            bank_code=bank_code
        )


class BVNVerificationError(NigerianBankingError):
    """Raised when BVN verification fails"""
    
    def __init__(self, bvn: str, reason: Optional[str] = None):
        message = f"BVN verification failed: {bvn[:3]}********"
        if reason:
            message += f" ({reason})"
        
        super().__init__(
            message,
            code="BVN_VERIFICATION_FAILED",
            details={"bvn_masked": f"{bvn[:3]}********", "reason": reason}
        )


class NINVerificationError(NigerianBankingError):
    """Raised when NIN verification fails"""
    
    def __init__(self, nin: str, reason: Optional[str] = None):
        message = f"NIN verification failed: {nin[:3]}********"
        if reason:
            message += f" ({reason})"
        
        super().__init__(
            message,
            code="NIN_VERIFICATION_FAILED",
            details={"nin_masked": f"{nin[:3]}********", "reason": reason}
        )


class BankTransferError(NigerianBankingError):
    """Raised for bank transfer related errors"""
    
    def __init__(
        self, 
        message: str, 
        session_id: Optional[str] = None,
        sender_bank: Optional[str] = None,
        recipient_bank: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.get("details", {})
        if session_id:
            details["session_id"] = session_id
        if sender_bank:
            details["sender_bank"] = sender_bank
        if recipient_bank:
            details["recipient_bank"] = recipient_bank
        
        super().__init__(
            message,
            code="BANK_TRANSFER_ERROR",
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"}
        )


class NIPError(NigerianBankingError):
    """Raised for NIP (Nigeria Inter-Bank Settlement System) errors"""
    
    def __init__(self, message: str, nip_response: Optional[Dict] = None, **kwargs):
        details = kwargs.get("details", {})
        if nip_response:
            details["nip_response"] = nip_response
        
        super().__init__(
            message,
            code="NIP_ERROR",
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"}
        )


class TransferVerificationError(BankTransferError):
    """Raised when bank transfer verification fails"""
    
    def __init__(
        self, 
        reference: str, 
        expected_amount: Decimal, 
        received_amount: Optional[Decimal] = None,
        **kwargs
    ):
        if received_amount:
            message = f"Transfer verification failed for {reference}: expected ₦{expected_amount:,.2f}, received ₦{received_amount:,.2f}"
        else:
            message = f"Transfer verification failed for {reference}: transfer not found"
        
        details = kwargs.get("details", {})
        details.update({
            "expected_amount": str(expected_amount),
            "received_amount": str(received_amount) if received_amount else None
        })
        
        super().__init__(
            message,
            code="TRANSFER_VERIFICATION_FAILED",
            details=details,
            reference=reference,
            **{k: v for k, v in kwargs.items() if k != "details"}
        )


# Paystack Specific Exceptions

class PaystackError(PaymentProviderError):
    """Raised for Paystack-specific errors"""
    
    def __init__(self, message: str, paystack_response: Optional[Dict] = None, **kwargs):
        super().__init__(
            message,
            provider="paystack",
            provider_response=paystack_response,
            code="PAYSTACK_ERROR",
            **kwargs
        )


class PaystackWebhookError(PaystackError):
    """Raised for Paystack webhook errors"""
    
    def __init__(self, message: str, event_type: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if event_type:
            details["event_type"] = event_type
        
        super().__init__(
            message,
            code="PAYSTACK_WEBHOOK_ERROR",
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"}
        )


class PaystackAuthorizationError(PaystackError):
    """Raised when Paystack authorization fails"""
    
    def __init__(self, authorization_code: str, reason: Optional[str] = None):
        message = f"Paystack authorization failed: {authorization_code}"
        if reason:
            message += f" ({reason})"
        
        super().__init__(
            message,
            code="PAYSTACK_AUTHORIZATION_FAILED",
            details={"authorization_code": authorization_code, "reason": reason}
        )


# Subscription and Billing Exceptions

class SubscriptionError(PaymentError):
    """Raised for subscription-related errors"""
    
    def __init__(self, message: str, subscription_id: Optional[str] = None, **kwargs):
        details = kwargs.get("details", {})
        if subscription_id:
            details["subscription_id"] = subscription_id
        
        super().__init__(
            message,
            code="SUBSCRIPTION_ERROR",
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"}
        )


class SubscriptionExpiredError(SubscriptionError):
    """Raised when subscription has expired"""
    
    def __init__(self, subscription_id: str, expired_at: str):
        super().__init__(
            f"Subscription {subscription_id} expired at {expired_at}",
            code="SUBSCRIPTION_EXPIRED",
            details={"subscription_id": subscription_id, "expired_at": expired_at},
            subscription_id=subscription_id
        )


class BillingCycleError(SubscriptionError):
    """Raised for billing cycle errors"""
    
    def __init__(self, message: str, billing_cycle: str, **kwargs):
        details = kwargs.get("details", {})
        details["billing_cycle"] = billing_cycle
        
        super().__init__(
            message,
            code="BILLING_CYCLE_ERROR",
            details=details,
            **{k: v for k, v in kwargs.items() if k != "details"}
        )


class PaymentRetryExceededError(PaymentError):
    """Raised when payment retry attempts are exceeded"""
    
    def __init__(self, reference: str, attempts: int, max_attempts: int):
        super().__init__(
            f"Payment retry exceeded for {reference}: {attempts}/{max_attempts} attempts",
            code="PAYMENT_RETRY_EXCEEDED",
            details={
                "reference": reference,
                "attempts": attempts,
                "max_attempts": max_attempts
            },
            reference=reference
        )


# Exception mapping for HTTP status codes
PAYMENT_EXCEPTION_STATUS_MAP = {
    PaymentError: 400,
    PaymentValidationError: 400,
    PaymentProviderError: 502,
    PaymentNotFoundError: 404,
    PaymentAlreadyProcessedError: 409,
    PaymentExpiredError: 410,
    InsufficientFundsError: 402,
    PaymentMethodNotSupportedError: 400,
    PaymentLimitExceededError: 403,
    RefundError: 400,
    RefundNotAllowedError: 403,
    PartialRefundNotSupportedError: 400,
    NigerianBankingError: 400,
    InvalidAccountNumberError: 400,
    BVNVerificationError: 400,
    NINVerificationError: 400,
    BankTransferError: 400,
    NIPError: 502,
    TransferVerificationError: 400,
    PaystackError: 502,
    PaystackWebhookError: 400,
    PaystackAuthorizationError: 401,
    SubscriptionError: 400,
    SubscriptionExpiredError: 402,
    BillingCycleError: 400,
    PaymentRetryExceededError: 429
}


def get_payment_exception_status_code(exception: PaymentError) -> int:
    """Get HTTP status code for payment exception"""
    return PAYMENT_EXCEPTION_STATUS_MAP.get(type(exception), 500)


def format_payment_exception_response(exception: PaymentError) -> Dict[str, Any]:
    """Format payment exception for API response"""
    return {
        "error": {
            "message": exception.message,
            "code": exception.code,
            "details": exception.details,
            "amount": str(exception.amount) if exception.amount else None,
            "reference": exception.reference
        }
    }


def is_retryable_error(exception: PaymentError) -> bool:
    """Check if a payment error is retryable"""
    
    retryable_types = [
        PaymentProviderError,
        NIPError,
        PaystackError
    ]
    
    non_retryable_codes = [
        "INSUFFICIENT_FUNDS",
        "PAYMENT_ALREADY_PROCESSED",
        "PAYMENT_EXPIRED",
        "INVALID_ACCOUNT_NUMBER",
        "BVN_VERIFICATION_FAILED",
        "NIN_VERIFICATION_FAILED"
    ]
    
    return (
        type(exception) in retryable_types and 
        exception.code not in non_retryable_codes
    )