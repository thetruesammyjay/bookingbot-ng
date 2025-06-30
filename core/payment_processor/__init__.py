"""
BookingBot NG Payment Processing Module

This module provides comprehensive payment processing services for Nigerian businesses
including Paystack integration, NIP verification, and multi-method payment support.
"""

from .models import (
    PaymentTransaction,
    PaymentRefund,
    BankAccount,
    PaymentPlan,
    TenantSubscription,
    PaymentWebhook,
    PaymentAnalytics,
    PaymentStatus,
    PaymentMethod,
    RefundStatus
)

from .paystack import (
    PaystackClient,
    PaystackWebhookHandler,
    NIGERIAN_BANKS,
    get_bank_code,
    kobo_to_naira,
    naira_to_kobo
)

from .nip import (
    NIPVerifier,
    BankTransferValidator,
    NIGERIAN_BANK_HOLIDAYS,
    is_banking_day,
    get_next_banking_day,
    estimate_transfer_time
)

from .exceptions import (
    PaymentError,
    PaymentValidationError,
    PaymentProviderError,
    PaymentNotFoundError,
    PaymentAlreadyProcessedError,
    PaymentExpiredError,
    InsufficientFundsError,
    PaymentMethodNotSupportedError,
    PaymentLimitExceededError,
    RefundError,
    RefundNotAllowedError,
    PartialRefundNotSupportedError,
    NigerianBankingError,
    InvalidAccountNumberError,
    BVNVerificationError,
    NINVerificationError,
    BankTransferError,
    NIPError,
    TransferVerificationError,
    PaystackError,
    PaystackWebhookError,
    PaystackAuthorizationError,
    SubscriptionError,
    SubscriptionExpiredError,
    BillingCycleError,
    PaymentRetryExceededError,
    get_payment_exception_status_code,
    format_payment_exception_response,
    is_retryable_error
)

__all__ = [
    # Models
    "PaymentTransaction",
    "PaymentRefund",
    "BankAccount",
    "PaymentPlan",
    "TenantSubscription", 
    "PaymentWebhook",
    "PaymentAnalytics",
    "PaymentStatus",
    "PaymentMethod",
    "RefundStatus",
    
    # Paystack Integration
    "PaystackClient",
    "PaystackWebhookHandler",
    "NIGERIAN_BANKS",
    "get_bank_code",
    "kobo_to_naira",
    "naira_to_kobo",
    
    # NIP and Bank Transfer
    "NIPVerifier",
    "BankTransferValidator",
    "NIGERIAN_BANK_HOLIDAYS",
    "is_banking_day",
    "get_next_banking_day",
    "estimate_transfer_time",
    
    # Exceptions
    "PaymentError",
    "PaymentValidationError",
    "PaymentProviderError",
    "PaymentNotFoundError",
    "PaymentAlreadyProcessedError",
    "PaymentExpiredError",
    "InsufficientFundsError",
    "PaymentMethodNotSupportedError",
    "PaymentLimitExceededError",
    "RefundError",
    "RefundNotAllowedError",
    "PartialRefundNotSupportedError",
    "NigerianBankingError",
    "InvalidAccountNumberError",
    "BVNVerificationError",
    "NINVerificationError",
    "BankTransferError",
    "NIPError",
    "TransferVerificationError",
    "PaystackError",
    "PaystackWebhookError",
    "PaystackAuthorizationError",
    "SubscriptionError",
    "SubscriptionExpiredError",
    "BillingCycleError",
    "PaymentRetryExceededError",
    "get_payment_exception_status_code",
    "format_payment_exception_response",
    "is_retryable_error"
]

__version__ = "1.0.0"
__author__ = "BookingBot NG Team"
__description__ = "Nigerian payment processing module with Paystack, NIP, and multi-method support"