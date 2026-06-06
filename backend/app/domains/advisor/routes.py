from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.responses import success_response
from backend.app.domains.advisor.schemas import ChatRequest
from backend.app.domains.advisor.service import AdvisorService
from backend.app.domains.identity.models import User

router = APIRouter(prefix="/ai-advisor", tags=["AI Advisor"])


@router.get("/recommendations")
def recommendations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = AdvisorService(db).recommendations(current_user)
    return success_response("Recommendations retrieved.", response.model_dump())


@router.get("/estate-readiness")
def estate_readiness(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from backend.app.domains.analytics.service import AnalyticsService

    response = AnalyticsService(db).readiness(current_user)
    return success_response("Estate readiness retrieved.", response.model_dump())


@router.get("/risk-analysis")
def risk_analysis(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = AdvisorService(db).risk_analysis(current_user)
    return success_response("Risk analysis retrieved.", response.model_dump())


@router.post("/chat")
def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = AdvisorService(db).chat(current_user, request.message)
    return success_response("Advisor response generated.", response.model_dump())
