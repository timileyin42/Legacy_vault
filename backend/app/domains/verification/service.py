from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import EncryptionService
from backend.app.domains.identity.models import User
from backend.app.domains.notifications.models import NotificationCategory
from backend.app.domains.notifications.service import NotificationService
from backend.app.domains.security.models import AuditAction
from backend.app.domains.security.repository import AuditRepository
from backend.app.domains.verification.models import (
    DeathVerification,
    StageStatus,
    VerificationStatus,
    Witness,
    WitnessStatus,
)
from backend.app.domains.verification.repository import VerificationRepository
from backend.app.domains.verification.schemas import (
    DeathVerificationCreateRequest,
    DeathVerificationResponse,
    EmergencyAccessStatusResponse,
    StageUpdateRequest,
    WitnessCreateRequest,
    WitnessRespondRequest,
    WitnessResponse,
)

WAITING_PERIOD_DAYS = 14


class VerificationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = VerificationRepository(db)
        self.encryption = EncryptionService()
        self.audit = AuditRepository(db)
        self.notifications = NotificationService(db)

    def create_death_verification(
        self, owner: User, request: DeathVerificationCreateRequest
    ) -> DeathVerificationResponse:
        verification = DeathVerification(
            owner_id=owner.id,
            status=VerificationStatus.in_progress,
            certificate_file_name=request.certificate_file_name,
            certificate_object_encrypted=(
                self.encryption.encrypt(request.certificate_object) if request.certificate_object else None
            ),
            certificate_checksum=request.certificate_checksum,
            document_integrity_status=(
                StageStatus.validated if request.certificate_object else StageStatus.pending
            ),
            created_by=owner.id,
            updated_by=owner.id,
        )
        self.repository.create(verification)
        self.db.flush()
        for witness in request.witnesses:
            self._add_witness(owner, verification, witness)
        self.audit.record(
            action=AuditAction.death_verification_submitted,
            actor_id=owner.id,
            resource_type="death_verification",
            resource_public_id=verification.public_id,
        )
        self.notifications.notify(
            owner,
            category=NotificationCategory.inheritance_event,
            title="Death verification submitted",
            body="A death verification request has been opened on your estate.",
            metadata={"verification_id": verification.public_id},
        )
        return self._to_response(verification)

    def list_death_verifications(self, owner: User) -> list[DeathVerificationResponse]:
        return [self._to_response(item) for item in self.repository.list_for_owner(owner.id)]

    def get_death_verification(self, owner: User, public_id: str) -> DeathVerificationResponse:
        return self._to_response(self._require(owner, public_id))

    def add_witness(self, owner: User, public_id: str, request: WitnessCreateRequest) -> DeathVerificationResponse:
        verification = self._require(owner, public_id)
        self._add_witness(owner, verification, request)
        return self._to_response(verification)

    def respond_witness(
        self, owner: User, public_id: str, witness_public_id: str, request: WitnessRespondRequest
    ) -> DeathVerificationResponse:
        verification = self._require(owner, public_id)
        witness = self.repository.get_witness(verification.id, witness_public_id)
        if not witness:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Witness not found.")
        witness.status = request.status
        witness.responded_at = datetime.now(UTC)
        witness.updated_by = owner.id
        return self._to_response(verification)

    def update_stages(
        self, owner: User, public_id: str, request: StageUpdateRequest
    ) -> DeathVerificationResponse:
        verification = self._require(owner, public_id)
        if request.document_integrity_status is not None:
            verification.document_integrity_status = request.document_integrity_status
        if request.court_crosscheck_status is not None:
            verification.court_crosscheck_status = request.court_crosscheck_status
        if request.vault_unlock_status is not None:
            verification.vault_unlock_status = request.vault_unlock_status
        verification.updated_by = owner.id
        if all(
            stage == StageStatus.validated
            for stage in (
                verification.document_integrity_status,
                verification.court_crosscheck_status,
                verification.vault_unlock_status,
            )
        ):
            verification.status = VerificationStatus.completed
        return self._to_response(verification)

    def emergency_access_status(self, owner: User) -> EmergencyAccessStatusResponse:
        verification = self.repository.latest_for_owner(owner.id)
        return EmergencyAccessStatusResponse(
            has_active_verification=verification is not None,
            verification=self._to_response(verification) if verification else None,
            waiting_period_days=WAITING_PERIOD_DAYS,
            security_level="ultra_secure",
        )

    def _add_witness(self, owner: User, verification: DeathVerification, request: WitnessCreateRequest) -> Witness:
        witness = Witness(
            verification_id=verification.id,
            full_name_encrypted=self.encryption.encrypt(request.full_name),
            email=request.email.lower(),
            status=WitnessStatus.pending,
            created_by=owner.id,
            updated_by=owner.id,
        )
        self.repository.add_witness(witness)
        self.db.flush()
        return witness

    def _require(self, owner: User, public_id: str) -> DeathVerification:
        verification = self.repository.get_for_owner(owner.id, public_id)
        if not verification:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Death verification not found.")
        return verification

    def _to_response(self, verification: DeathVerification) -> DeathVerificationResponse:
        witnesses = self.repository.list_witnesses(verification.id)
        stages = [
            verification.document_integrity_status,
            verification.court_crosscheck_status,
            verification.vault_unlock_status,
        ]
        validated = sum(1 for stage in stages if stage == StageStatus.validated)
        progress = round(validated / len(stages) * 100)
        verified_witnesses = sum(1 for w in witnesses if w.status == WitnessStatus.verified)
        return DeathVerificationResponse(
            id=verification.public_id,
            status=verification.status,
            certificate_file_name=verification.certificate_file_name,
            certificate_uploaded=verification.certificate_object_encrypted is not None,
            document_integrity_status=verification.document_integrity_status,
            court_crosscheck_status=verification.court_crosscheck_status,
            vault_unlock_status=verification.vault_unlock_status,
            progress_percent=progress,
            witnesses=[
                WitnessResponse(
                    id=w.public_id,
                    full_name=self.encryption.decrypt(w.full_name_encrypted),
                    email=w.email,
                    status=w.status,
                    responded_at=w.responded_at.isoformat() if w.responded_at else None,
                )
                for w in witnesses
            ],
            witness_consensus=f"{verified_witnesses} of {len(witnesses)}",
        )
