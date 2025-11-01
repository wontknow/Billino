### Summary Invoices
# Create, Read (list), Read (single), Delete
from database import get_session
from fastapi import APIRouter, Depends, HTTPException
from models import (SummaryInvoice, SummaryInvoiceCreate, SummaryInvoiceLink,
                    SummaryInvoiceRead)
from services import create_summary_invoice
from sqlalchemy.orm import Session
from sqlmodel import select

router = APIRouter(prefix="/summary-invoices", tags=["summary_invoices"])

## summary invoice read model
# id
# range_text
# date
# profile_id
# total_net
# total_tax
# total_gross
# invoice_ids


@router.post("/", response_model=SummaryInvoiceRead, status_code=201)
def create_summary(
    summary: SummaryInvoiceCreate, session: Session = Depends(get_session)
):
    try:
        summary_invoice = create_summary_invoice(session, summary)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=[{"loc": ["body"], "msg": str(e), "type": "value_error"}],
        )

    return summary_invoice


@router.get("/", response_model=list[SummaryInvoiceRead])
def list_summaries(session: Session = Depends(get_session)):
    summaries = session.exec(select(SummaryInvoice)).all()
    # Create list of SummaryInvoiceRead with invoice_ids from links
    summary_invoices = []
    for summary in summaries:
        # Get invoice IDs from links
        links = session.exec(
            select(SummaryInvoiceLink).where(
                SummaryInvoiceLink.summary_invoice_id == summary.id
            )
        ).all()
        invoice_ids = [link.invoice_id for link in links]

        summary_invoices.append(
            SummaryInvoiceRead(
                id=summary.id,
                range_text=summary.range_text,
                date=summary.date,
                profile_id=summary.profile_id,
                total_net=summary.total_net,
                total_tax=summary.total_tax,
                total_gross=summary.total_gross,
                invoice_ids=invoice_ids,
            )
        )
    return summary_invoices


# get summaries by profile_id
@router.get("/by-profile/{profile_id}", response_model=list[SummaryInvoiceRead])
def list_summaries_by_profile(profile_id: int, session: Session = Depends(get_session)):
    summaries = session.exec(
        select(SummaryInvoice).where(SummaryInvoice.profile_id == profile_id)
    ).all()
    # Create list of SummaryInvoiceRead with invoice_ids from links
    summary_invoices = []
    for summary in summaries:
        # Get invoice IDs from links
        links = session.exec(
            select(SummaryInvoiceLink).where(
                SummaryInvoiceLink.summary_invoice_id == summary.id
            )
        ).all()
        invoice_ids = [link.invoice_id for link in links]

        summary_invoices.append(
            SummaryInvoiceRead(
                id=summary.id,
                range_text=summary.range_text,
                date=summary.date,
                profile_id=summary.profile_id,
                total_net=summary.total_net,
                total_tax=summary.total_tax,
                total_gross=summary.total_gross,
                invoice_ids=invoice_ids,
            )
        )
    return summary_invoices


@router.get("/{summary_id}", response_model=SummaryInvoiceRead)
def read_summary(summary_id: int, session: Session = Depends(get_session)):
    summary = session.get(SummaryInvoice, summary_id)
    if not summary:
        raise HTTPException(
            status_code=404,
            detail=[
                {
                    "loc": ["path", "summary_id"],
                    "msg": "Summary Invoice not found.",
                    "type": "value_error",
                }
            ],
        )

    # Get invoice IDs from links
    links = session.exec(
        select(SummaryInvoiceLink).where(
            SummaryInvoiceLink.summary_invoice_id == summary.id
        )
    ).all()
    invoice_ids = [link.invoice_id for link in links]

    summary_invoice = SummaryInvoiceRead(
        id=summary.id,
        range_text=summary.range_text,
        date=summary.date,
        profile_id=summary.profile_id,
        total_net=summary.total_net,
        total_tax=summary.total_tax,
        total_gross=summary.total_gross,
        invoice_ids=invoice_ids,
    )
    return summary_invoice


@router.delete("/{summary_id}", status_code=204)
def delete_summary(summary_id: int, session: Session = Depends(get_session)):
    summary = session.get(SummaryInvoice, summary_id)
    if not summary:
        raise HTTPException(
            status_code=404,
            detail=[
                {
                    "loc": ["path", "summary_id"],
                    "msg": "Summary Invoice not found.",
                    "type": "value_error",
                }
            ],
        )
    # Manually delete all SummaryInvoiceLink rows for this summary invoice
    links = session.exec(
        select(SummaryInvoiceLink).where(
            SummaryInvoiceLink.summary_invoice_id == summary_id
        )
    ).all()
    for link in links:
        session.delete(link)
    session.delete(summary)
    session.commit()
    return
