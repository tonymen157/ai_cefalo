from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.api.database import get_db
from src.api.models import CreditCode, DownloadToken
import uuid
import datetime

router = APIRouter()


@router.post("/redeem-code")
def redeem_code(data: dict, db: Session = Depends(get_db)):
    """Verify credit code and return 1-hour download token."""
    code_str = data.get("code", "").strip()
    if not code_str:
        raise HTTPException(status_code=400, detail="Code required")

    code_obj = (
        db.query(CreditCode)
        .filter(CreditCode.code == code_str, CreditCode.used == False)
        .first()
    )
    if not code_obj:
        raise HTTPException(status_code=404, detail="Invalid or already used code")

    code_obj.used = True
    code_obj.used_at = datetime.datetime.now(datetime.timezone.utc)

    token = str(uuid.uuid4())
    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
    download_token = DownloadToken(
        token=token, job_id=data.get("job_id", ""), used=False, expires_at=expires
    )
    db.add(download_token)
    db.commit()

    return {"token": token, "expires_at": str(expires)}


@router.get("/download-report/{token}")
def download_report(token: str, db: Session = Depends(get_db)):
    """Verify token and return PDF without watermark."""
    token_obj = (
        db.query(DownloadToken)
        .filter(DownloadToken.token == token, DownloadToken.used == False)
        .first()
    )
    if not token_obj:
        raise HTTPException(status_code=403, detail="Invalid or expired token")

    # TODO: Generate PDF without watermark
    token_obj.used = True
    db.commit()

    return {"message": "PDF download endpoint - not yet implemented"}
