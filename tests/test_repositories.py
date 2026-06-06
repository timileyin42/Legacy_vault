from sqlalchemy.orm import Session

from backend.app.core.security import hash_password
from backend.app.domains.beneficiaries.models import Beneficiary
from backend.app.domains.beneficiaries.repository import BeneficiaryRepository
from backend.app.domains.identity.models import User
from backend.app.domains.identity.repository import UserRepository
from backend.app.domains.vault.models import VaultCategory, VaultItem
from backend.app.domains.vault.repository import VaultRepository


def test_repositories_filter_soft_deleted_records(db_session: Session):
    user_repo = UserRepository(db_session)
    user = user_repo.create(
        User(
            email="repo@example.com",
            full_name="Repo User",
            password_hash=hash_password("very-secure-password"),
        )
    )
    db_session.flush()

    vault_repo = VaultRepository(db_session)
    active = vault_repo.create_item(
        VaultItem(
            owner_id=user.id,
            category=VaultCategory.crypto_wallet,
            title_encrypted="encrypted-title",
            payload_encrypted="encrypted-payload",
        )
    )
    deleted = vault_repo.create_item(
        VaultItem(
            owner_id=user.id,
            category=VaultCategory.crypto_wallet,
            title_encrypted="deleted-title",
            payload_encrypted="deleted-payload",
            is_deleted=True,
        )
    )

    beneficiary_repo = BeneficiaryRepository(db_session)
    beneficiary_repo.create(
        Beneficiary(
            owner_id=user.id,
            full_name_encrypted="encrypted-name",
            email="heir@example.com",
            relationship="child",
        )
    )
    db_session.commit()

    items = vault_repo.list_items(user.id)

    assert [item.id for item in items] == [active.id]
    assert vault_repo.get_item(user.id, deleted.public_id) is None
    assert beneficiary_repo.count_for_owner(user.id) == 1

