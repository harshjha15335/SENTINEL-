import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import (
    DataOrigin,
    EventProcessing,
    EventVerification,
    MerchantEnvironment,
    Role,
    TransactionStatus,
)


def _enum(cls: type, name: str) -> Enum:
    return Enum(cls, name=name, native_enum=True, validate_strings=True)


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Merchant(TimestampMixin, Base):
    __tablename__ = "merchants"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    environment: Mapped[MerchantEnvironment] = mapped_column(
        _enum(MerchantEnvironment, "merchant_environment"), nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(_enum(Role, "user_role"), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    merchant: Mapped[Merchant] = relationship(lazy="joined")


class UserSession(Base):
    """Server-side session. Only SHA-256 digests of the tokens are stored."""

    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    csrf_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(lazy="joined")


class Product(TimestampMixin, Base):
    """Merchant catalogue item. The server-side price here is the only trusted amount."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("merchant_id", "sku"),
        CheckConstraint("price_minor > 0", name="price_positive"),
        CheckConstraint("char_length(currency) = 3", name="currency_iso"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    active: Mapped[bool] = mapped_column(nullable=False, default=True)


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("paypal_order_id"),
        UniqueConstraint("paypal_capture_id"),
        UniqueConstraint("merchant_id", "create_idempotency_key"),
        CheckConstraint("amount_minor > 0", name="amount_positive"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        Index("ix_transactions_merchant_created", "merchant_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    merchant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("merchants.id", ondelete="RESTRICT"), nullable=False
    )
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL")
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    paypal_order_id: Mapped[str | None] = mapped_column(String(64))
    paypal_capture_id: Mapped[str | None] = mapped_column(String(64))
    amount_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[TransactionStatus] = mapped_column(
        _enum(TransactionStatus, "transaction_status"), nullable=False, index=True
    )
    provider_status: Mapped[str | None] = mapped_column(String(64))
    payer_reference: Mapped[str | None] = mapped_column(String(64))
    create_idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    paypal_request_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    data_origin: Mapped[DataOrigin] = mapped_column(
        _enum(DataOrigin, "data_origin"), nullable=False, index=True
    )
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    product: Mapped[Product | None] = relationship(lazy="joined")


class PaymentEvent(Base):
    """Inbound provider event. The raw body is stored separately, keyed by digest."""

    __tablename__ = "payment_events"
    __table_args__ = (UniqueConstraint("provider_event_id"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("merchants.id", ondelete="RESTRICT"), index=True
    )
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), index=True
    )
    provider_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(64), index=True)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_reference: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("raw_payloads.id", ondelete="RESTRICT"), nullable=False
    )
    transmission_id: Mapped[str | None] = mapped_column(String(128))
    verification_status: Mapped[EventVerification] = mapped_column(
        _enum(EventVerification, "event_verification"), nullable=False
    )
    processing_status: Mapped[EventProcessing] = mapped_column(
        _enum(EventProcessing, "event_processing"), nullable=False, index=True
    )
    delivery_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_origin: Mapped[DataOrigin] = mapped_column(
        _enum(DataOrigin, "data_origin"), nullable=False
    )
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_reason: Mapped[str | None] = mapped_column(Text)


class RawPayload(Base):
    """Restricted store for raw webhook bodies (exact bytes, needed for signature checks).

    Not exposed through any API. Kept apart so ordinary queries never touch full payloads.
    """

    __tablename__ = "raw_payloads"

    id: Mapped[uuid.UUID] = _uuid_pk()
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    body: Mapped[bytes] = mapped_column(nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_merchant_created", "merchant_id", "created_at"),)

    id: Mapped[uuid.UUID] = _uuid_pk()
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("merchants.id", ondelete="RESTRICT")
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="USER")
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(128))
    correlation_id: Mapped[str | None] = mapped_column(String(64))
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
