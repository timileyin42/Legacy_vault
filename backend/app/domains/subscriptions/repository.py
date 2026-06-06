import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.domains.subscriptions.models import BillingRecord, PaymentTransaction, Subscription


class SubscriptionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ----- Payment transactions -----

    def create_transaction(self, transaction: PaymentTransaction) -> PaymentTransaction:
        self.db.add(transaction)
        return transaction

    def get_transaction(self, reference: str) -> PaymentTransaction | None:
        return self.db.execute(
            select(PaymentTransaction).where(PaymentTransaction.reference == reference)
        ).scalar_one_or_none()

    def get_transaction_for_owner(self, owner_id: uuid.UUID, reference: str) -> PaymentTransaction | None:
        return self.db.execute(
            select(PaymentTransaction).where(
                PaymentTransaction.owner_id == owner_id,
                PaymentTransaction.reference == reference,
            )
        ).scalar_one_or_none()

    def get_for_owner(self, owner_id: uuid.UUID) -> Subscription | None:
        return self.db.execute(
            select(Subscription)
            .where(Subscription.owner_id == owner_id, Subscription.is_deleted.is_(False))
            .order_by(Subscription.created_at.desc())
        ).scalars().first()

    def create(self, subscription: Subscription) -> Subscription:
        self.db.add(subscription)
        return subscription

    def add_billing_record(self, record: BillingRecord) -> BillingRecord:
        self.db.add(record)
        return record

    def list_billing(self, owner_id: uuid.UUID) -> list[BillingRecord]:
        return list(
            self.db.execute(
                select(BillingRecord)
                .where(BillingRecord.owner_id == owner_id, BillingRecord.is_deleted.is_(False))
                .order_by(BillingRecord.created_at.desc())
            ).scalars()
        )
