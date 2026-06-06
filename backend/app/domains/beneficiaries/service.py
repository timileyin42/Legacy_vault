from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import EncryptionService
from backend.app.domains.beneficiaries.models import Beneficiary, TrustedContact
from backend.app.domains.beneficiaries.repository import BeneficiaryRepository, TrustedContactRepository
from backend.app.domains.beneficiaries.schemas import (
    BeneficiaryAllocationSummary,
    BeneficiaryCreateRequest,
    BeneficiaryResponse,
    BeneficiaryUpdateRequest,
    BeneficiaryVerifyRequest,
    TrustedContactCreateRequest,
    TrustedContactResponse,
)
from backend.app.domains.identity.models import User
from backend.app.domains.security.models import AuditAction
from backend.app.domains.security.repository import AuditRepository


class BeneficiaryService:
    FREE_TIER_LIMIT = 2

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = BeneficiaryRepository(db)
        self.encryption = EncryptionService()
        self.audit = AuditRepository(db)

    def _beneficiary_limit(self, owner: User) -> int:
        """Beneficiary cap for the owner's current plan (plan-aware via subscriptions)."""
        from backend.app.domains.subscriptions.service import SubscriptionService

        return SubscriptionService(self.db).beneficiary_limit(owner)

    def create(self, owner: User, request: BeneficiaryCreateRequest) -> BeneficiaryResponse:
        limit = self._beneficiary_limit(owner)
        if limit is not None and self.repository.count_for_owner(owner.id) >= limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Your plan supports {limit} beneficiaries. Upgrade required.",
            )
        beneficiary = Beneficiary(
            owner_id=owner.id,
            full_name_encrypted=self.encryption.encrypt(request.full_name),
            email=request.email.lower(),
            relationship=request.relationship,
            allocation_percent=request.allocation_percent,
            instructions_encrypted=self.encryption.encrypt(request.instructions) if request.instructions else None,
            created_by=owner.id,
            updated_by=owner.id,
        )
        self.repository.create(beneficiary)
        self.db.flush()
        self.audit.record(
            action=AuditAction.beneficiary_created,
            actor_id=owner.id,
            resource_type="beneficiary",
            resource_public_id=beneficiary.public_id,
        )
        return self._to_response(beneficiary)

    def list_for_owner(self, owner: User) -> list[BeneficiaryResponse]:
        return [self._to_response(item) for item in self.repository.list_for_owner(owner.id)]

    def get(self, owner: User, public_id: str) -> BeneficiaryResponse:
        return self._to_response(self._require(owner, public_id))

    def update(self, owner: User, public_id: str, request: BeneficiaryUpdateRequest) -> BeneficiaryResponse:
        beneficiary = self._require(owner, public_id)
        if request.full_name is not None:
            beneficiary.full_name_encrypted = self.encryption.encrypt(request.full_name)
        if request.email is not None:
            beneficiary.email = request.email.lower()
        if request.relationship is not None:
            beneficiary.relationship = request.relationship
        if request.allocation_percent is not None:
            beneficiary.allocation_percent = request.allocation_percent
        if request.instructions is not None:
            beneficiary.instructions_encrypted = (
                self.encryption.encrypt(request.instructions) if request.instructions else None
            )
        beneficiary.updated_by = owner.id
        self.audit.record(
            action=AuditAction.beneficiary_updated,
            actor_id=owner.id,
            resource_type="beneficiary",
            resource_public_id=beneficiary.public_id,
        )
        return self._to_response(beneficiary)

    def delete(self, owner: User, public_id: str) -> dict:
        beneficiary = self._require(owner, public_id)
        beneficiary.is_deleted = True
        beneficiary.updated_by = owner.id
        self.audit.record(
            action=AuditAction.beneficiary_deleted,
            actor_id=owner.id,
            resource_type="beneficiary",
            resource_public_id=beneficiary.public_id,
        )
        return {"id": public_id, "deleted": True}

    def verify(self, owner: User, public_id: str, request: BeneficiaryVerifyRequest) -> BeneficiaryResponse:
        beneficiary = self._require(owner, public_id)
        beneficiary.status = request.status
        beneficiary.updated_by = owner.id
        self.audit.record(
            action=AuditAction.beneficiary_updated,
            actor_id=owner.id,
            resource_type="beneficiary",
            resource_public_id=beneficiary.public_id,
            metadata_json={"status": request.status.value},
        )
        return self._to_response(beneficiary)

    def allocation_summary(self, owner: User) -> BeneficiaryAllocationSummary:
        total = self.repository.total_allocation(owner.id)
        total = min(total, 100)
        return BeneficiaryAllocationSummary(
            beneficiary_count=self.repository.count_for_owner(owner.id),
            total_allocated_percent=total,
            unallocated_percent=max(0, 100 - total),
            fully_allocated=total >= 100,
        )

    def _require(self, owner: User, public_id: str) -> Beneficiary:
        beneficiary = self.repository.get_for_owner(owner.id, public_id)
        if not beneficiary:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beneficiary not found.")
        return beneficiary

    def _to_response(self, beneficiary: Beneficiary) -> BeneficiaryResponse:
        return BeneficiaryResponse(
            id=beneficiary.public_id,
            full_name=self.encryption.decrypt(beneficiary.full_name_encrypted),
            email=beneficiary.email,
            relationship=beneficiary.relationship,
            status=beneficiary.status,
            allocation_percent=beneficiary.allocation_percent,
        )


class TrustedContactService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = TrustedContactRepository(db)
        self.encryption = EncryptionService()
        self.audit = AuditRepository(db)

    def create(self, owner: User, request: TrustedContactCreateRequest) -> TrustedContactResponse:
        contact = TrustedContact(
            owner_id=owner.id,
            full_name_encrypted=self.encryption.encrypt(request.full_name),
            email=request.email.lower(),
            phone_encrypted=self.encryption.encrypt(request.phone) if request.phone else None,
            verification_weight=request.verification_weight,
            created_by=owner.id,
            updated_by=owner.id,
        )
        self.repository.create(contact)
        self.db.flush()
        self.audit.record(
            action=AuditAction.trusted_contact_created,
            actor_id=owner.id,
            resource_type="trusted_contact",
            resource_public_id=contact.public_id,
        )
        return self._to_response(contact)

    def list_for_owner(self, owner: User) -> list[TrustedContactResponse]:
        return [self._to_response(item) for item in self.repository.list_for_owner(owner.id)]

    def _to_response(self, contact: TrustedContact) -> TrustedContactResponse:
        return TrustedContactResponse(
            id=contact.public_id,
            full_name=self.encryption.decrypt(contact.full_name_encrypted),
            email=contact.email,
            verification_weight=contact.verification_weight,
        )

