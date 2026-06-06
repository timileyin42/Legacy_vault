from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import get_settings
from backend.app.core.database import Base, engine
from backend.app.core.responses import http_exception_handler, validation_exception_handler
from backend.app.domains.admin.routes import router as admin_router
from backend.app.domains.advisor.routes import router as advisor_router
from backend.app.domains.analytics.routes import router as analytics_router
from backend.app.domains.beneficiaries import models as beneficiaries_models
from backend.app.domains.beneficiaries.routes import router as beneficiaries_router
from backend.app.domains.beneficiaries.routes import trusted_contacts_router
from backend.app.domains.dashboard.routes import router as dashboard_router
from backend.app.domains.identity import models as identity_models
from backend.app.domains.identity.routes import router as identity_router
from backend.app.domains.inheritance import models as inheritance_models
from backend.app.domains.inheritance.routes import router as inheritance_router
from backend.app.domains.legacy import models as legacy_models
from backend.app.domains.legacy.routes import router as legacy_router
from backend.app.domains.notifications import models as notifications_models
from backend.app.domains.notifications.routes import router as notifications_router
from backend.app.domains.security import models as security_models
from backend.app.domains.security.routes import router as security_router
from backend.app.domains.subscriptions import models as subscriptions_models
from backend.app.domains.subscriptions.routes import router as subscriptions_router
from backend.app.domains.succession import models as succession_models
from backend.app.domains.succession.routes import router as succession_router
from backend.app.domains.vault import models as vault_models
from backend.app.domains.vault.routes import router as vault_router
from backend.app.domains.verification import models as verification_models
from backend.app.domains.verification.routes import router as verification_router

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


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", debug=settings.debug)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    from fastapi import HTTPException

    app.add_exception_handler(HTTPException, http_exception_handler)

    api_prefix = "/api/v1"
    app.include_router(identity_router, prefix=api_prefix)
    app.include_router(vault_router, prefix=api_prefix)
    app.include_router(beneficiaries_router, prefix=api_prefix)
    app.include_router(trusted_contacts_router, prefix=api_prefix)
    app.include_router(inheritance_router, prefix=api_prefix)
    app.include_router(verification_router, prefix=api_prefix)
    app.include_router(legacy_router, prefix=api_prefix)
    app.include_router(dashboard_router, prefix=api_prefix)
    app.include_router(analytics_router, prefix=api_prefix)
    app.include_router(advisor_router, prefix=api_prefix)
    app.include_router(succession_router, prefix=api_prefix)
    app.include_router(security_router, prefix=api_prefix)
    app.include_router(subscriptions_router, prefix=api_prefix)
    app.include_router(notifications_router, prefix=api_prefix)
    app.include_router(admin_router, prefix=api_prefix)

    @app.get("/health")
    def health():
        return {"success": True, "message": "Service healthy.", "data": {"service": settings.app_name}}

    return app


app = create_app()


def create_database() -> None:
    Base.metadata.create_all(bind=engine)
