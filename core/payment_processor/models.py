"""
Payment models for BookingBot NG
Handles Nigerian payment transactions, bank accounts, and financial records
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, DECIMAL
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class PaymentStatus(str, Enum):
    """Payment transaction status"""
    PENDING = "pending"              # Payment initiated but not confirmed
    PROCESSING = "processing"        # Payment being processed by provider
    SUCCESS = "success"              # Payment completed successfully
    FAILED = "failed"                # Payment failed
    CANCELLED = "cancelled"          # Payment cancelled by user
    REFUNDED = "refunded"           # Payment refunded
    DISPUTED = "disputed"           # Payment disputed/chargeback


class PaymentMethod(str, Enum):
    """Supported payment methods in Nigeria"""
    PAYSTACK_CARD = "paystack_card"         # Card payment via Paystack
    PAYSTACK_BANK = "paystack_bank"         # Bank transfer via Paystack
    PAYSTACK_USSD = "paystack_ussd"         # USSD payment via Paystack
    BANK_TRANSFER = "bank_transfer"         # Direct bank transfer with NIP verification
    CASH = "cash"                           # Cash payment (recorded manually)
    POS = "pos"                             # Point of Sale terminal
    MOBILE_MONEY = "mobile_money"           # Mobile money (future)


class RefundStatus(str, Enum):
    """Refund status"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class PaymentTransaction(Base):
    """Payment transaction records"""
    __tablename__ = "payment_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Transaction identification
    reference = Column(String(100), unique=True, index=True, nullable=False)  # Our internal reference
    external_reference = Column(String(100), index=True, nullable=True)       # Provider's reference
    
    # Transaction details
    amount = Column(DECIMAL(12, 2), nullable=False)  # Amount in Naira
    currency = Column(String(3), default="NGN", nullable=False)
    description = Column(Text, nullable=True)
    
    # Payment method and status
    payment_method = Column(String(30), nullable=False)  # PaymentMethod enum
    status = Column(String(20), default=PaymentStatus.PENDING, nullable=False)
    
    # Provider information
    provider = Column(String(50), nullable=True)  # paystack, bank, etc.
    provider_response = Column(JSON, nullable=True)  # Raw provider response
    
    # Tenant and customer information
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    customer_email = Column(String(255), nullable=True)
    customer_name = Column(String(200), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    
    # Related booking (if applicable)
    booking_id = Column(UUID(as_uuid=True), nullable=True)  # Will be FK to booking table
    
    # Fees and charges
    platform_fee = Column(DECIMAL(8, 2), default=0, nullable=False)
    provider_fee = Column(DECIMAL(8, 2), default=0, nullable=False)
    
    # Nigerian banking details (for bank transfers)
    bank_details = Column(JSON, nullable=True)  # Bank name, account details, etc.
    nip_session_id = Column(String(100), nullable=True)  # NIP verification session
    
    # Verification and security
    is_verified = Column(Boolean, default=False)
    verification_details = Column(JSON, nullable=True)
    
    # Webhook and notification tracking
    webhook_delivered = Column(Boolean, default=False)
    webhook_attempts = Column(Integer, default=0)
    notification_sent = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)  # When payment was confirmed
    expires_at = Column(DateTime, nullable=True)    # For temporary payments
    
    # Relationships
    refunds: Mapped[list["PaymentRefund"]] = relationship("PaymentRefund", back_populates="transaction")
    
    def __repr__(self):
        return f"<PaymentTransaction(reference='{self.reference}', amount={self.amount}, status='{self.status}')>"


class PaymentRefund(Base):
    """Payment refund records"""
    __tablename__ = "payment_refunds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("payment_transactions.id"), nullable=False)
    
    # Refund details
    amount = Column(DECIMAL(12, 2), nullable=False)  # Refund amount
    reason = Column(Text, nullable=True)
    reference = Column(String(100), unique=True, index=True, nullable=False)
    external_reference = Column(String(100), nullable=True)
    
    # Status and processing
    status = Column(String(20), default=RefundStatus.PENDING, nullable=False)
    provider_response = Column(JSON, nullable=True)
    
    # Authorization
    requested_by_user_id = Column(UUID(as_uuid=True), nullable=True)  # User who requested refund
    approved_by_user_id = Column(UUID(as_uuid=True), nullable=True)   # User who approved refund
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    # Relationships
    transaction: Mapped["PaymentTransaction"] = relationship("PaymentTransaction", back_populates="refunds")
    
    def __repr__(self):
        return f"<PaymentRefund(reference='{self.reference}', amount={self.amount}, status='{self.status}')>"


class BankAccount(Base):
    """Nigerian bank account information for tenants"""
    __tablename__ = "bank_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Bank details
    bank_name = Column(String(100), nullable=False)
    bank_code = Column(String(10), nullable=False)  # Nigerian bank codes (e.g., 058 for GTBank)
    account_number = Column(String(20), nullable=False)
    account_name = Column(String(200), nullable=False)
    
    # Account type and purpose
    account_type = Column(String(20), default="savings", nullable=False)  # savings, current, etc.
    purpose = Column(String(50), default="primary", nullable=False)  # primary, escrow, etc.
    
    # Verification status
    is_verified = Column(Boolean, default=False)
    verification_method = Column(String(30), nullable=True)  # bvn, nin, manual
    verification_details = Column(JSON, nullable=True)
    
    # Status and settings
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Default account for this tenant
    
    # Limits and controls
    daily_limit = Column(DECIMAL(12, 2), nullable=True)
    monthly_limit = Column(DECIMAL(12, 2), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<BankAccount(bank='{self.bank_name}', account='{self.account_number}', tenant='{self.tenant_id}')>"


class PaymentPlan(Base):
    """Subscription and payment plans for tenants"""
    __tablename__ = "payment_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Plan details
    name = Column(String(100), nullable=False)  # Basic, Pro, Enterprise
    description = Column(Text, nullable=True)
    
    # Pricing (monthly in Naira)
    monthly_price = Column(DECIMAL(10, 2), nullable=False)
    annual_price = Column(DECIMAL(10, 2), nullable=True)  # Discounted annual price
    setup_fee = Column(DECIMAL(10, 2), default=0, nullable=False)
    
    # Plan limits
    max_staff = Column(Integer, default=5, nullable=False)
    max_bookings_per_month = Column(Integer, default=100, nullable=False)
    max_services = Column(Integer, default=10, nullable=False)
    
    # Features
    features = Column(JSON, nullable=True)  # List of included features
    
    # Nigerian market specifics
    includes_paystack = Column(Boolean, default=True)
    includes_bank_transfer = Column(Boolean, default=True)
    includes_whatsapp = Column(Boolean, default=False)
    includes_custom_domain = Column(Boolean, default=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_popular = Column(Boolean, default=False)  # Featured plan
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PaymentPlan(name='{self.name}', monthly_price={self.monthly_price})>"


class TenantSubscription(Base):
    """Tenant subscription to payment plans"""
    __tablename__ = "tenant_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("payment_plans.id"), nullable=False)
    
    # Subscription details
    billing_cycle = Column(String(20), default="monthly", nullable=False)  # monthly, annual
    amount = Column(DECIMAL(10, 2), nullable=False)  # Amount being charged
    
    # Status and dates
    status = Column(String(20), default="active", nullable=False)  # active, cancelled, suspended
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    
    # Trial information
    trial_start = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    
    # Payment information
    last_payment_date = Column(DateTime, nullable=True)
    next_payment_date = Column(DateTime, nullable=True)
    failed_payment_attempts = Column(Integer, default=0)
    
    # Cancellation
    cancelled_at = Column(DateTime, nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<TenantSubscription(tenant='{self.tenant_id}', plan='{self.plan_id}', status='{self.status}')>"


class PaymentWebhook(Base):
    """Webhook event records for audit and replay"""
    __tablename__ = "payment_webhooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Webhook details
    provider = Column(String(50), nullable=False)  # paystack, bank, etc.
    event_type = Column(String(100), nullable=False)  # charge.success, transfer.failed, etc.
    event_id = Column(String(100), nullable=True)  # Provider's event ID
    
    # Request details
    headers = Column(JSON, nullable=True)
    payload = Column(JSON, nullable=False)
    signature = Column(String(500), nullable=True)
    
    # Processing
    is_verified = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)
    processing_attempts = Column(Integer, default=0)
    processing_errors = Column(JSON, nullable=True)
    
    # Related transaction
    transaction_reference = Column(String(100), nullable=True)
    
    # Timestamps
    received_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<PaymentWebhook(provider='{self.provider}', event='{self.event_type}', processed={self.is_processed})>"


class PaymentAnalytics(Base):
    """Aggregated payment analytics for reporting"""
    __tablename__ = "payment_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Time period
    date = Column(DateTime, nullable=False)  # Date for this analytics record
    period_type = Column(String(20), nullable=False)  # daily, weekly, monthly
    
    # Transaction counts
    total_transactions = Column(Integer, default=0)
    successful_transactions = Column(Integer, default=0)
    failed_transactions = Column(Integer, default=0)
    
    # Amount metrics (in Naira)
    total_amount = Column(DECIMAL(12, 2), default=0)
    successful_amount = Column(DECIMAL(12, 2), default=0)
    average_transaction = Column(DECIMAL(10, 2), default=0)
    
    # Payment method breakdown
    card_transactions = Column(Integer, default=0)
    bank_transfer_transactions = Column(Integer, default=0)
    cash_transactions = Column(Integer, default=0)
    
    # Fees
    total_platform_fees = Column(DECIMAL(10, 2), default=0)
    total_provider_fees = Column(DECIMAL(10, 2), default=0)
    
    # Performance metrics
    success_rate = Column(DECIMAL(5, 2), default=0)  # Percentage
    average_processing_time = Column(Integer, default=0)  # Seconds
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PaymentAnalytics(tenant='{self.tenant_id}', date='{self.date}', total={self.total_amount})>"