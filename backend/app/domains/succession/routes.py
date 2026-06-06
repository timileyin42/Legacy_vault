from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.core.deps import get_current_user
from backend.app.core.responses import success_response
from backend.app.domains.identity.models import User
from backend.app.domains.succession.schemas import SuccessionReportCreateRequest
from backend.app.domains.succession.service import SuccessionService

router = APIRouter(prefix="/succession-reports", tags=["Succession Reports"])


@router.post("")
def generate_report(
    request: SuccessionReportCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response = SuccessionService(db).generate(current_user, request)
    db.commit()
    return success_response("Succession report generated.", response.model_dump())


@router.get("")
def list_reports(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = SuccessionService(db).list_reports(current_user)
    return success_response("Succession reports retrieved.", [item.model_dump() for item in response])


@router.get("/{public_id}")
def get_report(public_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = SuccessionService(db).get_report(current_user, public_id)
    return success_response("Succession report retrieved.", response.model_dump())


@router.get("/{public_id}/pdf")
def download_report_pdf(
    public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reference, pdf_bytes = SuccessionService(db).render_pdf(current_user, public_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{reference}.pdf"'},
    )


@router.post("/{public_id}/share")
def share_report(public_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response = SuccessionService(db).share(current_user, public_id)
    db.commit()
    return success_response("Succession report shared.", response.model_dump())
