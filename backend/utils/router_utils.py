"""
Helper-Utilities für erweiterte Router-Implementierung.
Enthält Funktionen zum Parsing von Query-Parametern für Filter/Sort/Paging.
"""

from urllib.parse import unquote

from fastapi import HTTPException

from models.table_models import ColumnFilter, FilterOperator, SortDirection, SortField
from utils import logger

log = logger.createScoped("🔧 RouterUtils")


def parse_filter_params(filter_list: list[str] | None) -> list[ColumnFilter]:
    """
    Parse filter query-parameter list to ColumnFilter objects.

    Format: 'field:operator:value'
    Example: 'name:contains:John' → ColumnFilter(field='name', operator='contains', value='John')

    Args:
        filter_list: List of filter strings from Query parameter

    Returns:
        List of ColumnFilter objects

    Raises:
        HTTPException: Falls Format ungültig ist
    """
    filters: list[ColumnFilter] = []

    if not filter_list:
        return filters

    for filter_str in filter_list:
        try:
            parts = filter_str.split(":", 2)  # Split on first 2 colons
            if len(parts) < 3:
                log.warning(f"⚠️ Ungültiges Filter-Format: {filter_str}")
                continue

            field, operator_str, value = parts
            # Decode URL-encoded value (Frontend sendet encodeURIComponent)
            value = unquote(value)

            # Validiere Operator (raises ValueError if invalid)
            operator = FilterOperator(operator_str)

            filters.append(
                ColumnFilter(
                    field=field,
                    operator=operator,
                    value=value,
                )
            )
            log.debug(f"✅ Filter geparst: {field} {operator} {value}")

        except ValueError as e:
            log.error(f"❌ Ungültiger Filter-Operator: {operator_str}")
            raise HTTPException(
                status_code=400, detail=f"Invalid filter operator: {operator_str}"
            ) from e

    return filters


def parse_sort_params(sort_list: list[str] | None) -> list[SortField]:
    """
    Parse sort query-parameter list to SortField objects.

    Format: 'field:direction'
    Example: 'name:asc' → SortField(field='name', direction='asc')

    Args:
        sort_list: List of sort strings from Query parameter

    Returns:
        List of SortField objects

    Raises:
        HTTPException: Falls Format ungültig ist
    """
    sort_fields: list[SortField] = []

    if not sort_list:
        return sort_fields

    for sort_str in sort_list:
        try:
            parts = sort_str.split(":")
            if len(parts) != 2:
                log.warning(f"⚠️ Ungültiges Sort-Format: {sort_str}")
                continue

            field, direction_str = parts

            # Validiere Direction (raises ValueError if invalid)
            direction = SortDirection(direction_str)

            sort_fields.append(
                SortField(
                    field=field,
                    direction=direction,
                )
            )
            log.debug(f"✅ Sort geparst: {field} {direction}")

        except ValueError as e:
            log.error(f"❌ Ungültige Sort-Richtung: {direction_str}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sort direction: {direction_str} (use 'asc' or 'desc')",
            ) from e

    return sort_fields
