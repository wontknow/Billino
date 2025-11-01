from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Profile

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("/", response_model=Profile, status_code=201)
def create_profile(profile: Profile, session: Session = Depends(get_session)):
    if not profile.name or not profile.address:
        raise HTTPException(status_code=400, detail="Missing required fields")
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


@router.get("/", response_model=list[Profile])
def list_profiles(session: Session = Depends(get_session)):
    return session.exec(select(Profile)).all()


@router.get("/{profile_id}", response_model=Profile)
def get_profile(profile_id: int, session: Session = Depends(get_session)):
    profile = session.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/{profile_id}", response_model=Profile)
def update_profile(
    profile_id: int,
    updated_profile: Profile,
    session: Session = Depends(get_session),
):
    profile = session.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.name = updated_profile.name
    profile.address = updated_profile.address
    profile.city = updated_profile.city
    profile.bank_data = updated_profile.bank_data
    profile.tax_number = updated_profile.tax_number
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, session: Session = Depends(get_session)):
    profile = session.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    session.delete(profile)
    session.commit()
    return None
