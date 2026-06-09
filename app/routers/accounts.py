"""CRUD + on-demand collection for tracked accounts."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..collector import collect_account
from ..database import get_db
from ..instagram import InstagramError
from ..models import Account
from ..schemas import AccountCreate, AccountOut, SnapshotOut

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def _to_out(account: Account) -> AccountOut:
    return AccountOut(
        id=account.id,
        username=account.username,
        full_name=account.full_name,
        label=account.label,
        created_at=account.created_at,
        snapshot_count=len(account.snapshots),
    )


@router.get("", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    accounts = db.scalars(select(Account).order_by(Account.username)).all()
    return [_to_out(a) for a in accounts]


@router.post("", response_model=AccountOut, status_code=201)
def add_account(payload: AccountCreate, db: Session = Depends(get_db)):
    username = payload.username.lstrip("@").strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="username is required")
    existing = db.scalar(select(Account).where(Account.username == username))
    if existing:
        raise HTTPException(status_code=409, detail="account already tracked")
    account = Account(username=username, label=payload.label)
    db.add(account)
    db.commit()
    db.refresh(account)
    return _to_out(account)


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    db.delete(account)
    db.commit()


@router.get("/{account_id}/snapshots", response_model=list[SnapshotOut])
def list_snapshots(account_id: int, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    return [SnapshotOut.model_validate(s) for s in account.snapshots]


@router.post("/{account_id}/collect", response_model=SnapshotOut)
def collect_now(account_id: int, db: Session = Depends(get_db)):
    account = db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account not found")
    try:
        snapshot = collect_account(db, account)
    except InstagramError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return SnapshotOut.model_validate(snapshot)
