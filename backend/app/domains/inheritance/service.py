from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import EncryptionService
from backend.app.domains.beneficiaries.repository import BeneficiaryRepository
from backend.app.domains.identity.models import User
from backend.app.domains.inheritance.models import AccessRequest, AccessRequestStatus, InheritanceRule
from backend.app.domains.inheritance.repository import InheritanceRepository
from backend.app.domains.inheritance.schemas import (
    AccessRequestCreateRequest,
    AccessRequestResponse,
    AccessRequestStatusRequest,
    DistributionEntry,
    DistributionSummaryResponse,
    InheritanceRuleCreateRequest,
    InheritanceRuleResponse,
    InheritanceRuleUpdateRequest,
    RuleToggleRequest,
)
from backend.app.domains.security.models import AuditAction
from backend.app.domains.security.repository import AuditRepository
from backend.app.domains.vault.repository import VaultRepository


class InheritanceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = InheritanceRepository(db)
        self.beneficiaries = BeneficiaryRepository(db)
        self.vault = VaultRepository(db)
        self.encryption = EncryptionService()
        self.audit = AuditRepository(db)

    def create_rule(self, owner: User, request: InheritanceRuleCreateRequest) -> InheritanceRuleResponse:
        beneficiary = self.beneficiaries.get_for_owner(owner.id, request.beneficiary_id)
        if not beneficiary:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beneficiary not found.")
        vault_item = None
        if request.vault_item_id:
            vault_item = self.vault.get_item(owner.id, request.vault_item_id)
            if not vault_item:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vault item not found.")
        rule = InheritanceRule(
            owner_id=owner.id,
            beneficiary_id=beneficiary.id,
            vault_item_id=vault_item.id if vault_item else None,
            trigger=request.trigger,
            conditions=request.conditions,
            instructions_encrypted=self.encryption.encrypt(request.instructions) if request.instructions else None,
            created_by=owner.id,
            updated_by=owner.id,
        )
        self.repository.create_rule(rule)
        self.db.flush()
        return InheritanceRuleResponse(
            id=rule.public_id,
            beneficiary_id=beneficiary.public_id,
            vault_item_id=vault_item.public_id if vault_item else None,
            trigger=rule.trigger,
            conditions=rule.conditions,
            active=rule.active,
        )

    def list_rules(self, owner: User) -> list[InheritanceRuleResponse]:
        beneficiary_map = {b.id: b.public_id for b in self.beneficiaries.list_for_owner(owner.id)}
        return [
            self._to_rule_response(rule, beneficiary_map.get(rule.beneficiary_id, "unknown"))
            for rule in self.repository.list_rules(owner.id)
        ]

    def get_rule(self, owner: User, public_id: str) -> InheritanceRuleResponse:
        rule = self._require_rule(owner, public_id)
        beneficiary_map = {b.id: b.public_id for b in self.beneficiaries.list_for_owner(owner.id)}
        return self._to_rule_response(rule, beneficiary_map.get(rule.beneficiary_id, "unknown"))

    def update_rule(
        self, owner: User, public_id: str, request: InheritanceRuleUpdateRequest
    ) -> InheritanceRuleResponse:
        rule = self._require_rule(owner, public_id)
        if request.trigger is not None:
            rule.trigger = request.trigger
        if request.conditions is not None:
            rule.conditions = request.conditions
        if request.instructions is not None:
            rule.instructions_encrypted = (
                self.encryption.encrypt(request.instructions) if request.instructions else None
            )
        if request.active is not None:
            rule.active = request.active
        rule.updated_by = owner.id
        self.audit.record(
            action=AuditAction.inheritance_rule_updated,
            actor_id=owner.id,
            resource_type="inheritance_rule",
            resource_public_id=rule.public_id,
        )
        beneficiary_map = {b.id: b.public_id for b in self.beneficiaries.list_for_owner(owner.id)}
        return self._to_rule_response(rule, beneficiary_map.get(rule.beneficiary_id, "unknown"))

    def toggle_rule(self, owner: User, public_id: str, request: RuleToggleRequest) -> InheritanceRuleResponse:
        rule = self._require_rule(owner, public_id)
        rule.active = request.active
        rule.updated_by = owner.id
        self.audit.record(
            action=AuditAction.inheritance_rule_updated,
            actor_id=owner.id,
            resource_type="inheritance_rule",
            resource_public_id=rule.public_id,
            metadata_json={"active": request.active},
        )
        beneficiary_map = {b.id: b.public_id for b in self.beneficiaries.list_for_owner(owner.id)}
        return self._to_rule_response(rule, beneficiary_map.get(rule.beneficiary_id, "unknown"))

    def distribution_summary(self, owner: User) -> DistributionSummaryResponse:
        entries: list[DistributionEntry] = []
        total = 0
        for beneficiary in self.beneficiaries.list_for_owner(owner.id):
            total += beneficiary.allocation_percent
            entries.append(
                DistributionEntry(
                    beneficiary_id=beneficiary.public_id,
                    full_name=self.encryption.decrypt(beneficiary.full_name_encrypted),
                    relationship=beneficiary.relationship,
                    allocation_percent=beneficiary.allocation_percent,
                )
            )
        active_rules = [rule for rule in self.repository.list_rules(owner.id) if rule.active]
        capped_total = min(total, 100)
        engine_status = "optimal" if total <= 100 else "over_allocated"
        return DistributionSummaryResponse(
            entries=entries,
            total_allocated_percent=capped_total,
            unallocated_percent=max(0, 100 - capped_total),
            active_rule_count=len(active_rules),
            engine_status=engine_status,
        )

    def _require_rule(self, owner: User, public_id: str) -> InheritanceRule:
        rule = self.repository.get_rule(owner.id, public_id)
        if not rule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inheritance rule not found.")
        return rule

    @staticmethod
    def _to_rule_response(rule: InheritanceRule, beneficiary_public_id: str) -> InheritanceRuleResponse:
        return InheritanceRuleResponse(
            id=rule.public_id,
            beneficiary_id=beneficiary_public_id,
            vault_item_id=None,
            trigger=rule.trigger,
            conditions=rule.conditions,
            active=rule.active,
        )

    def create_access_request(self, owner: User, request: AccessRequestCreateRequest) -> AccessRequestResponse:
        beneficiary = self.beneficiaries.get_for_owner(owner.id, request.beneficiary_id)
        if not beneficiary:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beneficiary not found.")
        access_request = AccessRequest(
            owner_id=owner.id,
            beneficiary_id=beneficiary.id,
            request_type=request.request_type,
            evidence_summary_encrypted=self.encryption.encrypt(request.evidence_summary),
            status=AccessRequestStatus.identity_verification,
            waiting_period_days=14,
            risk_score=35,
            created_by=owner.id,
            updated_by=owner.id,
        )
        self.repository.create_access_request(access_request)
        self.db.flush()
        self.audit.record(
            action=AuditAction.access_request_created,
            actor_id=owner.id,
            resource_type="access_request",
            resource_public_id=access_request.public_id,
        )
        return self._to_access_response(access_request, beneficiary.public_id)

    def list_access_requests(self, owner: User) -> list[AccessRequestResponse]:
        beneficiaries = {b.id: b.public_id for b in self.beneficiaries.list_for_owner(owner.id)}
        return [
            self._to_access_response(item, beneficiaries.get(item.beneficiary_id, "unknown"))
            for item in self.repository.list_access_requests(owner.id)
        ]

    def update_access_status(
        self, owner: User, public_id: str, request: AccessRequestStatusRequest
    ) -> AccessRequestResponse:
        access_request = self.repository.get_access_request(owner.id, public_id)
        if not access_request:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Access request not found.")
        access_request.status = request.status
        access_request.updated_by = owner.id
        if request.reviewer_notes:
            access_request.reviewer_notes_encrypted = self.encryption.encrypt(request.reviewer_notes)
        if request.status == AccessRequestStatus.waiting_period:
            access_request.release_at = datetime.now(UTC) + timedelta(days=access_request.waiting_period_days)
        self.audit.record(
            action=AuditAction.access_request_status_changed,
            actor_id=owner.id,
            resource_type="access_request",
            resource_public_id=access_request.public_id,
            metadata_json={"status": request.status.value},
        )
        beneficiary = self.beneficiaries.get_for_owner(owner.id, self._beneficiary_public_id(owner, access_request))
        return self._to_access_response(
            access_request,
            beneficiary.public_id if beneficiary else str(access_request.beneficiary_id),
        )

    def _beneficiary_public_id(self, owner: User, access_request: AccessRequest) -> str:
        for beneficiary in self.beneficiaries.list_for_owner(owner.id):
            if beneficiary.id == access_request.beneficiary_id:
                return beneficiary.public_id
        return ""

    @staticmethod
    def _to_access_response(access_request: AccessRequest, beneficiary_public_id: str) -> AccessRequestResponse:
        return AccessRequestResponse(
            id=access_request.public_id,
            beneficiary_id=beneficiary_public_id,
            request_type=access_request.request_type,
            status=access_request.status,
            waiting_period_days=access_request.waiting_period_days,
            release_at=access_request.release_at.isoformat() if access_request.release_at else None,
            risk_score=access_request.risk_score,
        )

