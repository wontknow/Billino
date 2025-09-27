from fastapi import APIRouter, Depends, HTTPException
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


@router.put("/{customer_id}", response_model=Customer)
def update_customer(
    customer_id: int,
    updated_customer: Customer,
    session: Session = Depends(get_session),
):
    customer = session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    customer.name = updated_customer.name
    customer.address = updated_customer.address
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
