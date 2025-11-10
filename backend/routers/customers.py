from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from database import get_session
from models import Customer
from utils import logger

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("/", response_model=Customer)
def create_customer(customer: Customer, session: Session = Depends(get_session)):
    logger.debug(f"➕ POST /customers - Creating customer: {customer.name}")
    # verify body
    if not customer.name:
        logger.error("❌ Customer name is missing")
        raise HTTPException(status_code=400, detail="Name is required")
    session.add(customer)
    session.commit()
    session.refresh(customer)
    logger.info(
        f"✅ Customer created successfully", {"id": customer.id, "name": customer.name}
    )
    return customer


@router.get("/", response_model=list[Customer])
def list_customers(session: Session = Depends(get_session)):
    logger.debug("👥 GET /customers - Listing all customers")
    customers = session.exec(select(Customer)).all()
    logger.debug(f"✅ Found {len(customers)} customers")
    return customers


@router.get("/search", response_model=list[Customer])
def search_customers(
    q: str = Query(..., min_length=2, description="Search query (min. 2 characters)"),
    limit: int = Query(10, ge=1, le=50, description="Max results (default=10, max=50)"),
    session: Session = Depends(get_session),
):
    """
    Search for customers by name (case-insensitive substring match).

    - **q**: Search query (minimum 2 characters)
    - **limit**: Maximum number of results (default=10, max=50)
    """
    logger.debug(f"🔍 GET /customers/search - Searching for: {q}")
    # Escape LIKE wildcards in user input
    escaped_q = q.replace("%", "\\%").replace("_", "\\_")
    statement = (
        select(Customer)
        .where(Customer.name.ilike(f"%{escaped_q}%", escape="\\"))
        .limit(limit)
    )
    customers = session.exec(statement).all()
    logger.debug(f"✅ Search found {len(customers)} customers")
    return customers


@router.put("/{customer_id}", response_model=Customer)
def update_customer(
    customer_id: int,
    updated_customer: Customer,
    session: Session = Depends(get_session),
):
    logger.info(f"✏️ PUT /customers/{customer_id} - Updating customer")
    customer = session.get(Customer, customer_id)
    if not customer:
        logger.error(f"❌ Customer {customer_id} not found for update")
        raise HTTPException(status_code=404, detail="Customer not found")
    if customer.name != updated_customer.name:
        customer.name = updated_customer.name
    if customer.address != updated_customer.address:
        customer.address = updated_customer.address
    if customer.city != updated_customer.city:
        customer.city = updated_customer.city
    session.add(customer)
    session.commit()
    session.refresh(customer)
    logger.info(f"✅ Customer {customer_id} updated successfully")
    return customer


@router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: int, session: Session = Depends(get_session)):
    logger.info(f"🗑️ DELETE /customers/{customer_id} - Deleting customer")
    customer = session.get(Customer, customer_id)
    if not customer:
        logger.error(f"❌ Customer {customer_id} not found for deletion")
        raise HTTPException(status_code=404, detail="Customer not found")
    session.delete(customer)
    session.commit()
    logger.info(f"✅ Customer {customer_id} deleted successfully")
    session.commit()
    return None
