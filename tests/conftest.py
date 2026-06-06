import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")

# Keep the test suite hermetic: never read real external-service credentials from
# a local .env. Env vars take precedence over the dotenv file in pydantic-settings,
# so forcing these empty guarantees Firebase/FCM/Resend are treated as unconfigured
# (tests that need them inject fakes via dependency overrides).
for _external in (
    "FIREBASE_PROJECT_ID", "FCM_SERVICE_ACCOUNT_BASE64", "FCM_SERVER_KEY",
    "RESEND_API_KEY", "PAYSTACK_SECRET_KEY", "PAYSTACK_PUBLIC_KEY", "PAYSTACK_CALLBACK_URL",
):
    os.environ[_external] = ""

from backend.app.core.database import Base, get_db
from backend.app.domains.beneficiaries import models as beneficiaries_models
from backend.app.domains.identity import models as identity_models
from backend.app.domains.inheritance import models as inheritance_models
from backend.app.domains.legacy import models as legacy_models
from backend.app.domains.notifications import models as notifications_models
from backend.app.domains.security import models as security_models
from backend.app.domains.subscriptions import models as subscriptions_models
from backend.app.domains.succession import models as succession_models
from backend.app.domains.vault import models as vault_models
from backend.app.domains.verification import models as verification_models
from backend.app.main import create_app

_ = (
    identity_models,
    vault_models,
    beneficiaries_models,
    inheritance_models,
    security_models,
    notifications_models,
    subscriptions_models,
    verification_models,
    legacy_models,
    succession_models,
)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@example.com",
            "full_name": "Estate Owner",
            "password": "very-secure-password",
            "device_fingerprint": "ios-device-1",
        },
    )
    token = response.json()["data"]["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}

