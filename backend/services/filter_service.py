"""
Service-Layer für sichere SQLModel-Filter, Sortierung und Paginierung.

Verantwortlichkeiten:
- Validierung von Filter-Parametern (Security: SQL-Injection Prevention)
- Anwendung von Filtern auf SQLModel SelectStatement
- Anwendung von Sortierung (stabil mit Primary Key)
- Paginierung mit Limit/Offset Berechnung
- Globale Suche über multiple Felder
"""

from typing import Any, Optional, Type

from sqlalchemy import and_, func, or_, select
from sqlmodel import Session, SQLModel

from models.table_models import (
    ColumnFilter,
    FilterOperator,
    GlobalSearch,
    PaginatedResponse,
    SortDirection,
    SortField,
)
from utils import logger

log = logger


class FilterService:
    """
    Sichere Anwendung von Filtern auf SQLModel Queries

    SICHERHEIT:
    - SQL-Injection Prevention: Nur vorgegebene Operatoren erlaubt
    - Wildcard-Escaping: % und _ werden escapt
    - Type-Checking: Wertetypen validieren
    """

    @staticmethod
    def escape_wildcards(value: str) -> str:
        """
        Escape Wildcard-Zeichen für LIKE-Operationen

        Args:
            value: Input-String

        Returns:
            String mit escapten Wildcards (% → \\%, _ → \\_)
        """
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    @staticmethod
    def apply_filters(
        stmt: Any,
        filters: list[ColumnFilter],
        model: Type[SQLModel],
        allowed_fields: Optional[set[str]] = None,
    ) -> Any:
        """
        Wende Liste von Filtern auf SQLAlchemy Statement an

        Args:
            stmt: SQLAlchemy Select-Statement
            filters: Liste von ColumnFilter-Objekten
            model: SQLModel-Klasse für Spalten-Validation
            allowed_fields: Whitelist erlaubter Felder (falls None: alle aus model)

        Returns:
            Modifizierter Statement mit WHERE-Klauseln

        Raises:
            ValueError: Falls Feld nicht existiert oder nicht erlaubt
        """
        if not filters:
            return stmt

        # Whitelist: erlaubte Felder (aus Model-Definition)
        if allowed_fields is None:
            allowed_fields = set(model.model_fields.keys())

        conditions = []

        for filter_obj in filters:
            field_name = filter_obj.field

            # Sicherheit: Nur erlaubte Felder
            if field_name not in allowed_fields:
                log.warning(f"🚫 Ungültiges Filter-Feld: {field_name}")
                raise ValueError(f"Field '{field_name}' not allowed for filtering")

            # Hole Spalte aus Model
            try:
                column = getattr(model, field_name)
            except AttributeError:
                log.warning(f"🚫 Spalte nicht existiert: {field_name}")
                raise ValueError(
                    f"Field '{field_name}' does not exist on model {model.__name__}"
                )

            value = filter_obj.value
            operator = filter_obj.operator

            try:
                # Wende Operator an
                if operator == FilterOperator.CONTAINS:
                    # LIKE '%value%' (case-insensitive)
                    condition = column.ilike(
                        f"%{FilterService.escape_wildcards(str(value))}%", escape="\\"
                    )

                elif operator == FilterOperator.STARTS_WITH:
                    # LIKE 'value%' (case-insensitive)
                    condition = column.ilike(
                        f"{FilterService.escape_wildcards(str(value))}%", escape="\\"
                    )

                elif operator == FilterOperator.EXACT:
                    # Exakte Übereinstimmung (case-insensitive für Strings)
                    condition = column.ilike(
                        FilterService.escape_wildcards(str(value)), escape="\\"
                    )

                elif operator == FilterOperator.EQUALS:
                    # Gleichheit (für Zahlen, Booleans)
                    condition = column == value

                elif operator == FilterOperator.BETWEEN:
                    # Bereich-Filter: value = {"min": X, "max": Y}
                    if (
                        not isinstance(value, dict)
                        or "min" not in value
                        or "max" not in value
                    ):
                        raise ValueError(
                            f"BETWEEN operator requires dict with 'min' and 'max' keys"
                        )
                    condition = and_(column >= value["min"], column <= value["max"])

                elif operator == FilterOperator.IN:
                    # Liste von Werten
                    if not isinstance(value, list):
                        raise ValueError(f"IN operator requires list value")
                    condition = column.in_(value)

                elif operator == FilterOperator.GT:
                    condition = column > value

                elif operator == FilterOperator.LT:
                    condition = column < value

                elif operator == FilterOperator.GTE:
                    condition = column >= value

                elif operator == FilterOperator.LTE:
                    condition = column <= value

                else:
                    log.warning(f"🚫 Ungültiger Operator: {operator}")
                    raise ValueError(f"Unknown operator: {operator}")

                conditions.append(condition)
                log.debug(f"✅ Filter angewendet: {field_name} {operator} {value}")

            except Exception as e:
                log.error(
                    f"❌ Fehler beim Anwenden des Filters",
                    {"field": field_name, "error": str(e)},
                )
                raise ValueError(
                    f"Error applying filter on field '{field_name}': {str(e)}"
                )

        # Kombiniere alle Conditions mit AND
        if conditions:
            stmt = stmt.where(and_(*conditions))

        return stmt

    @staticmethod
    def apply_sort(
        stmt: Any,
        sort_fields: list[SortField],
        model: Type[SQLModel],
        primary_key_field: str = "id",
        allowed_fields: Optional[set[str]] = None,
    ) -> Any:
        """
        Wende Multi-Column Sortierung auf Statement an

        STABILITÄT:
        - Primary Key wird immer am Ende hinzugefügt für stabile Sortierung
        - Verhindert inkonsistente Ergebnisse bei gleichen Werten

        Args:
            stmt: SQLAlchemy Select-Statement
            sort_fields: Liste von SortField-Objekten
            model: SQLModel-Klasse
            primary_key_field: Name des Primary Key Feldes (default: "id")
            allowed_fields: Whitelist erlaubter Felder

        Returns:
            Modifizierter Statement mit ORDER BY
        """
        if not sort_fields:
            # Fallback: Sortiere nach Primary Key
            return stmt.order_by(getattr(model, primary_key_field))

        if allowed_fields is None:
            allowed_fields = set(model.model_fields.keys())

        for sort_obj in sort_fields:
            field_name = sort_obj.field

            # Sicherheit: Nur erlaubte Felder
            if field_name not in allowed_fields:
                log.warning(f"🚫 Ungültiges Sort-Feld: {field_name}")
                raise ValueError(f"Field '{field_name}' not allowed for sorting")

            try:
                column = getattr(model, field_name)
                if sort_obj.direction == SortDirection.ASC:
                    stmt = stmt.order_by(column.asc())
                else:
                    stmt = stmt.order_by(column.desc())
                log.debug(
                    f"✅ Sortierung angewendet: {field_name} {sort_obj.direction}"
                )
            except AttributeError:
                log.warning(f"🚫 Spalte nicht existiert: {field_name}")
                raise ValueError(
                    f"Field '{field_name}' does not exist on model {model.__name__}"
                )

        # Stabile Sortierung: Immer Primary Key am Ende (falls nicht schon in sort_fields)
        if not any(s.field == primary_key_field for s in sort_fields):
            stmt = stmt.order_by(getattr(model, primary_key_field))

        return stmt

    @staticmethod
    def apply_global_search(
        stmt: Any,
        search: GlobalSearch,
        model: Type[SQLModel],
        search_fields: Optional[set[str]] = None,
    ) -> Any:
        """
        Wende globale Volltextsuche an

        Sucht in multiple Spalten mit LIKE (case-insensitive)

        Args:
            stmt: SQLAlchemy Select-Statement
            search: GlobalSearch-Objekt mit query + fields
            model: SQLModel-Klasse
            search_fields: Fallback-Felder falls search.fields leer

        Returns:
            Modifizierter Statement mit WHERE (field1 LIKE query OR field2 LIKE query ...)
        """
        if not search.query or not search.query.strip():
            return stmt

        # Felder in denen gesucht wird
        fields_to_search = search.fields or list(search_fields or [])

        if not fields_to_search:
            log.warning("🚫 Keine Felder zum Durchsuchen definiert")
            return stmt

        # Validiere Felder
        allowed_fields = set(model.model_fields.keys())
        invalid_fields = [f for f in fields_to_search if f not in allowed_fields]

        if invalid_fields:
            log.warning(f"🚫 Ungültige Suchfelder: {invalid_fields}")
            raise ValueError(f"Invalid search fields: {invalid_fields}")

        # Baue OR-Bedingung
        search_value = f"%{FilterService.escape_wildcards(search.query)}%"
        conditions = [
            getattr(model, field).ilike(search_value, escape="\\")
            for field in fields_to_search
        ]

        if conditions:
            stmt = stmt.where(or_(*conditions))
            log.info(
                f"✅ Globale Suche angewendet: '{search.query}' in {fields_to_search}"
            )

        return stmt


def paginate(
    session: Session,
    stmt: Any,
    model: Type[SQLModel],
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[SQLModel], int]:
    """
    Paginiere Query-Ergebnisse

    Args:
        session: Database Session
        stmt: SQLAlchemy Select-Statement (mit Filters/Sort angewendet)
        model: SQLModel-Klasse (für Typ-Info)
        page: Seite (1-basiert)
        page_size: Items pro Seite

    Returns:
        Tuple: (items, total_count)
    """
    # Validiere Parameter
    page = max(1, page)
    page_size = max(1, min(page_size, 1000))  # Max 1000 pro Seite

    # Hole Gesamtanzahl aus dem gefilterten Statement
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = session.scalar(count_stmt) or 0

    # Paginiere
    offset = (page - 1) * page_size
    items = session.exec(stmt.offset(offset).limit(page_size)).all()

    log.debug(
        f"📄 Paginiert: Page {page}, Size {page_size}, Offset {offset}, Total {total}"
    )

    return items, total


def create_paginated_response(
    items: list[SQLModel],
    total: int,
    page: int,
    page_size: int,
) -> PaginatedResponse:
    """
    Erstelle PaginatedResponse-Objekt

    Args:
        items: Liste von Items
        total: Gesamtanzahl Items
        page: Aktuelle Seite
        page_size: Items pro Seite

    Returns:
        PaginatedResponse mit berechneter pageCount
    """
    page_count = (total + page_size - 1) // page_size  # Ceiling Division

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        pageSize=page_size,
        pageCount=page_count,
    )
