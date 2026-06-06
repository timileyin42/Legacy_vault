import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.domains.vault.models import Asset, Document, VaultItem


class VaultRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_item(self, item: VaultItem) -> VaultItem:
        self.db.add(item)
        return item

    def list_items(self, owner_id: uuid.UUID) -> list[VaultItem]:
        return list(
            self.db.execute(
                select(VaultItem)
                .where(VaultItem.owner_id == owner_id, VaultItem.is_deleted.is_(False))
                .order_by(VaultItem.created_at.desc())
            ).scalars()
        )

    def get_item(self, owner_id: uuid.UUID, public_id: str) -> VaultItem | None:
        return self.db.execute(
            select(VaultItem).where(
                VaultItem.owner_id == owner_id,
                VaultItem.public_id == public_id,
                VaultItem.is_deleted.is_(False),
            )
        ).scalar_one_or_none()

    def create_asset(self, asset: Asset) -> Asset:
        self.db.add(asset)
        return asset

    def list_assets(self, owner_id: uuid.UUID) -> list[Asset]:
        return list(
            self.db.execute(
                select(Asset)
                .where(Asset.owner_id == owner_id, Asset.is_deleted.is_(False))
                .order_by(Asset.created_at.desc())
            ).scalars()
        )

    def get_asset(self, owner_id: uuid.UUID, public_id: str) -> Asset | None:
        return self.db.execute(
            select(Asset).where(
                Asset.owner_id == owner_id,
                Asset.public_id == public_id,
                Asset.is_deleted.is_(False),
            )
        ).scalar_one_or_none()

    def create_document(self, document: Document) -> Document:
        self.db.add(document)
        return document

    def list_documents(self, owner_id: uuid.UUID) -> list[Document]:
        return list(
            self.db.execute(
                select(Document)
                .where(Document.owner_id == owner_id, Document.is_deleted.is_(False))
                .order_by(Document.created_at.desc())
            ).scalars()
        )

    def get_document(self, owner_id: uuid.UUID, public_id: str) -> Document | None:
        return self.db.execute(
            select(Document).where(
                Document.owner_id == owner_id,
                Document.public_id == public_id,
                Document.is_deleted.is_(False),
            )
        ).scalar_one_or_none()

    def count_items(self, owner_id: uuid.UUID) -> int:
        return self.db.execute(
            select(func.count()).select_from(VaultItem).where(
                VaultItem.owner_id == owner_id,
                VaultItem.is_deleted.is_(False),
            )
        ).scalar_one()
