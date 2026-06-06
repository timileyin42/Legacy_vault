from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.responses import success_response
from backend.app.domains.identity.models import User
from backend.app.domains.vault.schemas import (
    AssetCreateRequest,
    AssetUpdateRequest,
    DocumentCreateRequest,
    VaultItemCreateRequest,
    VaultItemUpdateRequest,
)
from backend.app.domains.vault.service import VaultService
from backend.app.integrations.storage import StorageClient, get_storage_client

router = APIRouter(prefix="/vault", tags=["Vault"])


@router.post("/items")
def create_item(
    request: VaultItemCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = VaultService(db).create_item(current_user, request)
    db.commit()
    return success_response("Vault item created.", response.model_dump())


@router.get("/items")
def list_items(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = VaultService(db).list_items(current_user)
    return success_response("Vault items retrieved.", [item.model_dump() for item in response])


@router.get("/items/{public_id}")
def get_item(public_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = VaultService(db).get_item(current_user, public_id)
    db.commit()
    return success_response("Vault item retrieved.", response.model_dump())


@router.put("/items/{public_id}")
def update_item(
    public_id: str,
    request: VaultItemUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = VaultService(db).update_item(current_user, public_id, request)
    db.commit()
    return success_response("Vault item updated.", response.model_dump())


@router.delete("/items/{public_id}")
def delete_item(public_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = VaultService(db).delete_item(current_user, public_id)
    db.commit()
    return success_response("Vault item removed.", response)


@router.post("/assets")
def create_asset(
    request: AssetCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = VaultService(db).create_asset(current_user, request)
    db.commit()
    return success_response("Asset created.", response.model_dump())


@router.get("/assets")
def list_assets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = VaultService(db).list_assets(current_user)
    return success_response("Assets retrieved.", [asset.model_dump() for asset in response])


@router.get("/assets/{public_id}")
def get_asset(public_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = VaultService(db).get_asset(current_user, public_id)
    return success_response("Asset retrieved.", response.model_dump())


@router.put("/assets/{public_id}")
def update_asset(
    public_id: str,
    request: AssetUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = VaultService(db).update_asset(current_user, public_id, request)
    db.commit()
    return success_response("Asset updated.", response.model_dump())


@router.delete("/assets/{public_id}")
def delete_asset(public_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = VaultService(db).delete_asset(current_user, public_id)
    db.commit()
    return success_response("Asset removed.", response)


@router.post("/documents")
def create_document(
    request: DocumentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = VaultService(db).create_document(current_user, request)
    db.commit()
    return success_response("Document created.", response.model_dump())


@router.post("/documents/upload")
def upload_document(
    title: str = Form(...),
    document_type: str = Form(...),
    classification: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    storage_client: StorageClient = Depends(get_storage_client),
    db: Session = Depends(get_db),
):
    response = VaultService(db).upload_document(
        current_user,
        title=title,
        document_type=document_type,
        classification=classification,
        file=file,
        storage_client=storage_client,
    )
    db.commit()
    return success_response("Document uploaded.", response.model_dump())


@router.get("/documents")
def list_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = VaultService(db).list_documents(current_user)
    return success_response("Documents retrieved.", [document.model_dump() for document in response])


@router.get("/documents/categories")
def document_categories(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = VaultService(db).document_categories(current_user)
    return success_response("Document categories retrieved.", [item.model_dump() for item in response])


@router.get("/documents/expiring")
def expiring_documents(
    within_days: int = 60,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = VaultService(db).expiring_documents(current_user, within_days=within_days)
    return success_response("Expiring documents retrieved.", [item.model_dump() for item in response])


@router.get("/documents/{public_id}")
def get_document(public_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = VaultService(db).get_document(current_user, public_id)
    return success_response("Document retrieved.", response.model_dump())


@router.delete("/documents/{public_id}")
def delete_document(public_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = VaultService(db).delete_document(current_user, public_id)
    db.commit()
    return success_response("Document removed.", response)


@router.post("/documents/{public_id}/read-url")
def create_document_read_url(
    public_id: str,
    current_user: User = Depends(get_current_user),
    storage_client: StorageClient = Depends(get_storage_client),
    db: Session = Depends(get_db),
):
    response = VaultService(db).create_document_read_url(current_user, public_id, storage_client)
    return success_response("Document read URL created.", response.model_dump())
