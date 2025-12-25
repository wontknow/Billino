from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from database import get_session
from models import Profile
from utils import logger

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.post("/", response_model=Profile, status_code=201)
def create_profile(profile: Profile, session: Session = Depends(get_session)):
    """
    Create a new profile.

    Creates a new company/seller profile. Required for creating invoices.

    **Request Body:**
    - `name` (string, required): Company/profile name
    - `address` (string, required): Company address
    - `city` (string, required): Company city
    - `bank_data` (string, optional): Bank account information
    - `tax_number` (string, optional): Tax/VAT number
    - `include_tax` (boolean, optional): Whether to include VAT (default: true)
    - `default_tax_rate` (float, optional): Default VAT rate as decimal (default: 0.19)

    **Returns:**
    - Profile object with assigned ID

    **Example Request:**
    ```json
    {
        "name": "Tech Solutions GmbH",
        "address": "Hauptstrasse 123",
        "city": "Berlin",
        "bank_data": "DE89370400440532013000",
        "tax_number": "DE123456789",
        "include_tax": true,
        "default_tax_rate": 0.19
    }
    ```

    **Example Response (201):**
    ```json
    {
        "id": 1,
        "name": "Tech Solutions GmbH",
        "address": "Hauptstrasse 123",
        "city": "Berlin",
        "bank_data": "DE89370400440532013000",
        "tax_number": "DE123456789",
        "include_tax": true,
        "default_tax_rate": 0.19
    }
    ```
    """
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
    """
    List all profiles.

    Retrieves a list of all company/seller profiles.

    **Returns:**
    - List of Profile objects

    **Example Response (200):**
    ```json
    [
        {
            "id": 1,
            "name": "Tech Solutions GmbH",
            "address": "Hauptstrasse 123",
            "city": "Berlin",
            "bank_data": "DE89370400440532013000",
            "tax_number": "DE123456789",
            "include_tax": true,
            "default_tax_rate": 0.19
        }
    ]
    ```
    """
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

    Performs a case-insensitive substring search on profile names.

    **Query Parameters:**
    - `q` (string, required): Search query (minimum 2 characters)
    - `limit` (integer, optional): Maximum number of results (default=10, max=50)

    **Returns:**
    - List of matching Profile objects (limited to max results)

    **Example Request:**
    ```
    GET /profiles/search?q=tech&limit=5
    ```

    **Example Response (200):**
    ```json
    [
        {
            "id": 1,
            "name": "Tech Solutions GmbH",
            "address": "Hauptstrasse 123",
            "city": "Berlin",
            "bank_data": "DE89370400440532013000",
            "tax_number": "DE123456789",
            "include_tax": true,
            "default_tax_rate": 0.19
        }
    ]
    ```
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
    """
    Get a single profile by ID.

    Retrieves detailed information about a specific profile.

    **Path Parameters:**
    - `profile_id` (integer, required): ID of the profile to retrieve

    **Returns:**
    - Profile object

    **Example Response (200):**
    ```json
    {
        "id": 1,
        "name": "Tech Solutions GmbH",
        "address": "Hauptstrasse 123",
        "city": "Berlin",
        "bank_data": "DE89370400440532013000",
        "tax_number": "DE123456789",
        "include_tax": true,
        "default_tax_rate": 0.19
    }
    ```
    """
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
    """
    Update an existing profile.

    Updates the profile record with the provided data.

    **Path Parameters:**
    - `profile_id` (integer, required): ID of the profile to update

    **Request Body:**
    - `name` (string, required): Company/profile name
    - `address` (string, required): Company address
    - `city` (string, required): Company city
    - `bank_data` (string, optional): Bank account information
    - `tax_number` (string, optional): Tax/VAT number
    - `include_tax` (boolean, optional): Whether to include VAT
    - `default_tax_rate` (float, optional): Default VAT rate as decimal

    **Returns:**
    - Updated Profile object

    **Example Request:**
    ```json
    {
        "name": "Tech Solutions GmbH Updated",
        "address": "Neue Strasse 456",
        "city": "Munich",
        "bank_data": "DE89370400440532013000",
        "tax_number": "DE123456789",
        "include_tax": true,
        "default_tax_rate": 0.19
    }
    ```
    """
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
    """
    Delete a profile.

    Removes a profile record from the database. All related invoices must be deleted first.

    **Path Parameters:**
    - `profile_id` (integer, required): ID of the profile to delete

    **Returns:**
    - No content (HTTP 204)
    """
    profile = session.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    session.delete(profile)
    session.commit()
    return None
