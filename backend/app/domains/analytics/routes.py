from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.responses import success_response
from backend.app.domains.analytics.service import AnalyticsService
from backend.app.domains.identity.models import User

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/readiness")
def readiness(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = AnalyticsService(db).readiness(current_user)
    return success_response("Readiness score retrieved.", response.model_dump())


@router.get("/asset-distribution")
def asset_distribution(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = AnalyticsService(db).asset_distribution(current_user)
    return success_response("Asset distribution retrieved.", response.model_dump())


@router.get("/beneficiary-coverage")
def beneficiary_coverage(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = AnalyticsService(db).beneficiary_coverage(current_user)
    return success_response("Beneficiary coverage retrieved.", response.model_dump())


@router.get("/security-metrics")
def security_metrics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = AnalyticsService(db).security_metrics(current_user)
    return success_response("Security metrics retrieved.", response.model_dump())


@router.get("/trends")
def trends(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = AnalyticsService(db).trends(current_user)
    return success_response("Trends retrieved.", response.model_dump())
