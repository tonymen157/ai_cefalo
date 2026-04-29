from functools import wraps
import secrets
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session


from os import getenv
ADMIN_PASSWORD = getenv("ADMIN_PASSWORD", "aicefalo2025")  # TODO: usar .env en producción

security = HTTPBasic()


def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def validate_download_token(token: str, db: Session):
    """Validate download token and return job_id if valid."""
    from src.api.models import DownloadToken

    token_obj = (
        db.query(DownloadToken)
        .filter(DownloadToken.token == token, DownloadToken.used == False)
        .first()
    )
    if not token_obj:
        return None
    return token_obj.job_id
