import uuid
import string
import random
from sqlalchemy.orm import Session
from src.api.models import CreditCode


def generate_codes(db: Session, count: int, batch_id: str = None):
    """Generate N random credit codes."""
    if not batch_id:
        batch_id = str(uuid.uuid4())

    codes = []
    for _ in range(count):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        code_obj = CreditCode(
            id=str(uuid.uuid4()),
            code=code,
            used=False,
            batch_id=batch_id,
        )
        db.add(code_obj)
        codes.append(code)

    db.commit()
    return {"codes": codes, "batch_id": batch_id, "count": len(codes)}


def get_code_stats(db: Session):
    """Return used/available code counts."""
    total = db.query(CreditCode).count()
    used = db.query(CreditCode).filter(CreditCode.used == True).count()
    return {"total": total, "used": used, "available": total - used}
