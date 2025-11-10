from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from database import get_session
from models import Profile
from utils import logger

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("/", response_model=Profile, status_code=201)
def create_profile(profile: Profile, session: Session = Depends(get_session)):
    logger.info(f"📋 POST /profiles - Creating profile: {profile.name}")
    if not profile.name or not profile.address:
        logger.error(f"❌ Profile creation failed - Missing required fields")
        raise HTTPException(status_code=400, detail="Missing required fields")
    session.add(profile)
    session.commit()
    session.refresh(profile)
    logger.info(f"✅ Profile created successfully (id={profile.id})")
    return profile


@router.get("/", response_model=list[Profile])
def list_profiles(session: Session = Depends(get_session)):
    logger.debug("📋 GET /profiles - Listing all profiles")
    profiles = session.exec(select(Profile)).all()
    logger.debug(f"✅ Found {len(profiles)} profiles")
    return profiles


@router.get("/search", response_model=list[Profile])
def search_profiles(
    q: str = Query(..., min_length=2, description="Search query (min. 2 characters)"),
    limit: int = Query(10, ge=1, le=50, description="Max results (default=10, max=50)"),
    session: Session = Depends(get_session),
):
    """
    Search for profiles by name (case-insensitive substring match).

    - **q**: Search query (minimum 2 characters)
    - **limit**: Maximum number of results (default=10, max=50)
    """
    logger.debug(f"🔍 GET /profiles/search - Searching for: '{q}' (limit={limit})")
    # Escape LIKE wildcards in user input
    escaped_q = q.replace("%", "\\%").replace("_", "\\_")
    statement = (
        select(Profile)
        .where(Profile.name.ilike(f"%{escaped_q}%", escape="\\"))
        .limit(limit)
    )
    profiles = session.exec(statement).all()
    logger.debug(f"✅ Search returned {len(profiles)} profiles")
    return profiles


@router.get("/{profile_id}", response_model=Profile)
def get_profile(profile_id: int, session: Session = Depends(get_session)):
    logger.debug(f"📖 GET /profiles/{profile_id} - Fetching profile")
    profile = session.get(Profile, profile_id)
    if not profile:
        logger.error(f"❌ Profile {profile_id} not found")
        raise HTTPException(status_code=404, detail="Profile not found")
    logger.debug(f"✅ Profile {profile_id} fetched successfully")
    return profile


@router.put("/{profile_id}", response_model=Profile)
def update_profile(
    profile_id: int,
    updated_profile: Profile,
    session: Session = Depends(get_session),
):
    logger.info(f"✏️ PUT /profiles/{profile_id} - Updating profile")
    profile = session.get(Profile, profile_id)
    if not profile:
        logger.error(f"❌ Profile {profile_id} not found for update")
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.name = updated_profile.name
    profile.address = updated_profile.address
    profile.city = updated_profile.city
    profile.bank_data = updated_profile.bank_data
    profile.tax_number = updated_profile.tax_number
    session.add(profile)
    session.commit()
    session.refresh(profile)
    logger.info(f"✅ Profile {profile_id} updated successfully")
    return profile


@router.delete("/{profile_id}", status_code=204)
def delete_profile(profile_id: int, session: Session = Depends(get_session)):
    profile = session.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    session.delete(profile)
    session.commit()
    return None
