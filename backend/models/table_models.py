"""
Shared models für erweiterte Tabellenfilterung, Sortierung und Paginierung.

Diese Modelle definieren die Struktur von:
- Filteranfragen (ColumnFilter, FilterOperator)
- Sortieranfragen (SortField)
- Paginierte Responses (PaginatedResponse)
- API Query-Parameter Validierung
"""

from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from sqlmodel import SQLModel


class FilterOperator(str, Enum):
    """Unterstützte Filteroperatoren"""

    CONTAINS = "contains"  # Text: enthält (case-insensitive)
    STARTS_WITH = "startsWith"  # Text: beginnt mit
    EXACT = "exact"  # Genaue Übereinstimmung
    EQUALS = "equals"  # Zahlen, Boolean
    BETWEEN = "between"  # Bereich (min, max)
    IN = "in"  # Liste von Werten
    GT = "gt"  # Größer als
    LT = "lt"  # Kleiner als
    GTE = "gte"  # Größer oder gleich
    LTE = "lte"  # Kleiner oder gleich


class SortDirection(str, Enum):
    """Sortierrichtungen"""

    ASC = "asc"
    DESC = "desc"


class ColumnFilter(SQLModel):
    """Eine einzelne Spalten-Filter-Definition"""

    field: str
    operator: FilterOperator
    value: Any


class SortField(SQLModel):
    """Ein einzelner Sortierschritt"""

    field: str
    direction: SortDirection


class GlobalSearch(SQLModel):
    """Globale Suchparameter"""

    query: str
    fields: Optional[list[str]] = None  # Falls None: alle durchsuchbaren Felder


T = TypeVar("T")


class PaginatedResponse(SQLModel, Generic[T]):
    """
    Paginierte API-Antwort

    Beispiel:
    {
        "items": [...],
        "total": 150,
        "page": 1,
        "pageSize": 10,
        "pageCount": 15
    }
    """

    items: list[T]
    total: int  # Gesamtanzahl aller Items
    page: int  # Aktuelle Seite (1-basiert)
    pageSize: int  # Items pro Seite
    pageCount: int  # Gesamtanzahl Seiten
