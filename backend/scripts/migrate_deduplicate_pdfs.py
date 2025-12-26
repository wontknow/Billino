#!/usr/bin/env python3
"""
Database migration script to deduplicate existing PDFs before applying unique constraints.

This script should be run before deploying the unique constraint changes to production.
It handles the case where multiple PDFs may exist for the same invoice or summary invoice.

The script will:
1. Identify duplicate PDFs for the same invoice_id
2. Keep the most recent PDF (by created_at timestamp)
3. Delete older duplicate PDFs
4. Repeat for summary_invoice_id duplicates
5. Apply the unique constraints

Usage:
    python scripts/migrate_deduplicate_pdfs.py [--dry-run]

Options:
    --dry-run: Show what would be deleted without actually deleting
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import from backend
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select
from sqlalchemy import func

from database import get_engine
from models.stored_pdf import StoredPDF
from utils import logger


def find_duplicate_pdfs_by_invoice(session: Session) -> list[tuple[int, int]]:
    """
    Find invoice_ids that have multiple PDFs.

    Returns:
        List of (invoice_id, count) tuples for invoices with multiple PDFs
    """
    stmt = (
        select(StoredPDF.invoice_id, func.count(StoredPDF.id).label("count"))
        .where(StoredPDF.invoice_id.isnot(None))
        .group_by(StoredPDF.invoice_id)
        .having(func.count(StoredPDF.id) > 1)
    )
    result = session.exec(stmt).all()
    return [(row[0], row[1]) for row in result]


def find_duplicate_pdfs_by_summary_invoice(session: Session) -> list[tuple[int, int]]:
    """
    Find summary_invoice_ids that have multiple PDFs.

    Returns:
        List of (summary_invoice_id, count) tuples for summary invoices with multiple PDFs
    """
    stmt = (
        select(
            StoredPDF.summary_invoice_id, func.count(StoredPDF.id).label("count")
        )
        .where(StoredPDF.summary_invoice_id.isnot(None))
        .group_by(StoredPDF.summary_invoice_id)
        .having(func.count(StoredPDF.id) > 1)
    )
    result = session.exec(stmt).all()
    return [(row[0], row[1]) for row in result]


def deduplicate_invoice_pdfs(
    session: Session, invoice_id: int, dry_run: bool = False
) -> int:
    """
    Keep the most recent PDF for an invoice and delete older duplicates.

    Args:
        session: Database session
        invoice_id: ID of the invoice with duplicate PDFs
        dry_run: If True, don't actually delete, just log what would be deleted

    Returns:
        Number of PDFs that were (or would be) deleted
    """
    # Get all PDFs for this invoice, ordered by created_at descending
    stmt = (
        select(StoredPDF)
        .where(StoredPDF.invoice_id == invoice_id)
        .order_by(StoredPDF.created_at.desc())
    )
    pdfs = session.exec(stmt).all()

    if len(pdfs) <= 1:
        return 0

    # Keep the first (most recent), delete the rest
    pdfs_to_keep = pdfs[0]
    pdfs_to_delete = pdfs[1:]

    logger.info(
        f"📄 Invoice {invoice_id}: Keeping PDF {pdfs_to_keep.id} "
        f"(created {pdfs_to_keep.created_at}), deleting {len(pdfs_to_delete)} older PDFs"
    )

    deleted_count = 0
    for pdf in pdfs_to_delete:
        if dry_run:
            logger.info(
                f"  [DRY RUN] Would delete PDF {pdf.id} (created {pdf.created_at})"
            )
        else:
            logger.info(f"  🗑️ Deleting PDF {pdf.id} (created {pdf.created_at})")
            session.delete(pdf)
        deleted_count += 1

    return deleted_count


def deduplicate_summary_invoice_pdfs(
    session: Session, summary_invoice_id: int, dry_run: bool = False
) -> int:
    """
    Keep the most recent PDF for a summary invoice and delete older duplicates.

    Args:
        session: Database session
        summary_invoice_id: ID of the summary invoice with duplicate PDFs
        dry_run: If True, don't actually delete, just log what would be deleted

    Returns:
        Number of PDFs that were (or would be) deleted
    """
    # Get all PDFs for this summary invoice, ordered by created_at descending
    stmt = (
        select(StoredPDF)
        .where(StoredPDF.summary_invoice_id == summary_invoice_id)
        .order_by(StoredPDF.created_at.desc())
    )
    pdfs = session.exec(stmt).all()

    if len(pdfs) <= 1:
        return 0

    # Keep the first (most recent), delete the rest
    pdfs_to_keep = pdfs[0]
    pdfs_to_delete = pdfs[1:]

    logger.info(
        f"📄 Summary Invoice {summary_invoice_id}: Keeping PDF {pdfs_to_keep.id} "
        f"(created {pdfs_to_keep.created_at}), deleting {len(pdfs_to_delete)} older PDFs"
    )

    deleted_count = 0
    for pdf in pdfs_to_delete:
        if dry_run:
            logger.info(
                f"  [DRY RUN] Would delete PDF {pdf.id} (created {pdf.created_at})"
            )
        else:
            logger.info(f"  🗑️ Deleting PDF {pdf.id} (created {pdf.created_at})")
            session.delete(pdf)
        deleted_count += 1

    return deleted_count


def run_migration(dry_run: bool = False) -> None:
    """
    Run the deduplication migration.

    Args:
        dry_run: If True, don't actually delete, just show what would happen
    """
    logger.info("=" * 80)
    logger.info("PDF Deduplication Migration")
    logger.info("=" * 80)
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No changes will be made")
    logger.info("")

    engine = get_engine()
    session = Session(engine)

    try:
        # Check for invoice PDF duplicates
        logger.info("🔍 Checking for duplicate invoice PDFs...")
        invoice_duplicates = find_duplicate_pdfs_by_invoice(session)

        if not invoice_duplicates:
            logger.info("✅ No duplicate invoice PDFs found")
        else:
            logger.info(
                f"⚠️ Found {len(invoice_duplicates)} invoices with duplicate PDFs"
            )
            total_deleted = 0
            for invoice_id, count in invoice_duplicates:
                deleted = deduplicate_invoice_pdfs(session, invoice_id, dry_run)
                total_deleted += deleted

            logger.info(
                f"{'Would delete' if dry_run else 'Deleted'} {total_deleted} duplicate invoice PDFs"
            )

        logger.info("")

        # Check for summary invoice PDF duplicates
        logger.info("🔍 Checking for duplicate summary invoice PDFs...")
        summary_duplicates = find_duplicate_pdfs_by_summary_invoice(session)

        if not summary_duplicates:
            logger.info("✅ No duplicate summary invoice PDFs found")
        else:
            logger.info(
                f"⚠️ Found {len(summary_duplicates)} summary invoices with duplicate PDFs"
            )
            total_deleted = 0
            for summary_invoice_id, count in summary_duplicates:
                deleted = deduplicate_summary_invoice_pdfs(
                    session, summary_invoice_id, dry_run
                )
                total_deleted += deleted

            logger.info(
                f"{'Would delete' if dry_run else 'Deleted'} {total_deleted} duplicate summary invoice PDFs"
            )

        # Commit if not dry run
        if not dry_run:
            session.commit()
            logger.info("")
            logger.info("✅ Migration completed successfully")
            logger.info("")
            logger.info(
                "ℹ️ You can now safely deploy the unique constraint changes"
            )
        else:
            logger.info("")
            logger.info(
                "ℹ️ This was a dry run. Run without --dry-run to apply changes"
            )

    except Exception as e:
        session.rollback()
        logger.error(f"❌ Migration failed: {str(e)}", exc_info=True)
        raise
    finally:
        session.close()

    logger.info("=" * 80)


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description="Deduplicate PDFs before applying unique constraints"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )
    args = parser.parse_args()

    run_migration(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
