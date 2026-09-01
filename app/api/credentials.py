from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import SNMPCredential
from app.schemas import SNMPCredentialIn, SNMPCredentialOut
from app.security import encrypt_secret

router = APIRouter(prefix="/api/snmp-credentials", tags=["snmp-credentials"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[SNMPCredentialOut])
def list_credentials(db: Session = Depends(get_db)):
    # Only the reference name/version ever leaves the server — the
    # community string itself is write-only from the API's perspective.
    return db.query(SNMPCredential).order_by(SNMPCredential.name).all()


@router.post("", response_model=SNMPCredentialOut)
def create_credential(payload: SNMPCredentialIn, db: Session = Depends(get_db)):
    credential = SNMPCredential(
        name=payload.name,
        version=payload.version,
        encrypted_secret=encrypt_secret(payload.community),
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    return credential
