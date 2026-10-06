from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import User
from backend.app.services.auth_service import decode_access_token
from backend.app.services.demo_dashboard_service import DEMO_ACCOUNT_ASSIGNMENTS


def get_demo_dashboard_context(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> tuple[User, dict[str, str]]:
    scheme, _, token = authorization.partition(" ")
    claims = decode_access_token(token) if scheme.lower() == "bearer" else None
    if not claims:
        raise HTTPException(status_code=401, detail="Sign in to view this dashboard")
    user = db.get(User, claims.get("sub"))
    if user is None or user.email != claims.get("email"):
        raise HTTPException(status_code=401, detail="Sign in to view this dashboard")
    assignment = DEMO_ACCOUNT_ASSIGNMENTS.get(user.email)
    if assignment is None or claims.get("role") != assignment["role"]:
        raise HTTPException(status_code=403, detail="No dashboard is assigned to this user")
    return user, assignment
