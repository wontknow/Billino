from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from database import get_session
from models import Customer

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("/", response_model=Customer)
def create_customer(customer: Customer, session: Session = Depends(get_session)):
    # verify body
    if not customer.name:
        raise HTTPException(status_code=400, detail="Name is required")
    session.add(customer)
    session.commit()
    session.refresh(customer)
    return customer


@router.get("/", response_model=list[Customer])
def list_customers(session: Session = Depends(get_session)):
    return session.exec(select(Customer)).all()


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
    statement = select(Customer).where(Customer.name.ilike(f"%{q}%")).limit(limit)
    customers = session.exec(statement).all()
    return customers


@router.put("/{customer_id}", response_model=Customer)
def update_customer(
    customer_id: int,
    updated_customer: Customer,
    session: Session = Depends(get_session),
):
    customer = session.get(Customer, customer_id)
    if not customer:
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
    return customer


@router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: int, session: Session = Depends(get_session)):
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    session.delete(customer)
    session.commit()
    return None
