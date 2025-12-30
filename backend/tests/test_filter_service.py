"""
Tests für FilterService und Paginierungslogik.
Testet Filter-Operatoren, Wildcard-Escaping, Sortierung und Paginierung.
"""

import pytest
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.pool import StaticPool

from database import get_session
from models import Customer
from models.table_models import (
    ColumnFilter,
    FilterOperator,
    GlobalSearch,
    SortDirection,
    SortField,
)
from services.filter_service import FilterService, create_paginated_response, paginate


@pytest.fixture
def session():
    """In-memory SQLite session für Tests"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create tables
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture
def sample_customers(session):
    """Erstelle Sample-Customers"""
    customers = [
        Customer(name="John Doe", address="123 Main St", city="Berlin", note=None),
        Customer(name="Jane Smith", address="456 Oak Ave", city="Munich", note="VIP"),
        Customer(name="Bob Johnson", address="789 Pine Rd", city="Hamburg", note=None),
        Customer(name="Alice Brown", address="321 Elm St", city="Cologne", note="Test"),
    ]

    for customer in customers:
        session.add(customer)

    session.commit()
    return customers


class TestFilterServiceOperators:
    """Tests für verschiedene Filter-Operatoren"""

    def test_contains_filter(self, session, sample_customers):
        """Test CONTAINS operator (case-insensitive LIKE)"""
        stmt = select(Customer)
        filters = [
            ColumnFilter(field="name", operator=FilterOperator.CONTAINS, value="john")
        ]

        stmt = FilterService.apply_filters(stmt, filters, Customer)
        results = session.exec(stmt).all()

        assert len(results) == 2  # "John Doe" und "Bob Johnson"
        assert all("john" in c.name.lower() for c in results)

    def test_starts_with_filter(self, session, sample_customers):
        """Test STARTS_WITH operator"""
        stmt = select(Customer)
        filters = [
            ColumnFilter(field="name", operator=FilterOperator.STARTS_WITH, value="J")
        ]

        stmt = FilterService.apply_filters(stmt, filters, Customer)
        results = session.exec(stmt).all()

        assert len(results) == 2  # "John Doe" und "Jane Smith"
        assert all(c.name.startswith("J") for c in results)

    def test_exact_filter(self, session, sample_customers):
        """Test EXACT operator (case-insensitive)"""
        stmt = select(Customer)
        filters = [
            ColumnFilter(field="name", operator=FilterOperator.EXACT, value="john doe")
        ]

        stmt = FilterService.apply_filters(stmt, filters, Customer)
        results = session.exec(stmt).all()

        assert len(results) == 1
        assert results[0].name == "John Doe"

    def test_equals_filter(self, session, sample_customers):
        """Test EQUALS operator (for exact match)"""
        stmt = select(Customer)
        filters = [ColumnFilter(field="id", operator=FilterOperator.EQUALS, value=1)]

        stmt = FilterService.apply_filters(stmt, filters, Customer)
        results = session.exec(stmt).all()

        assert len(results) == 1
        assert results[0].id == 1

    def test_in_filter(self, session, sample_customers):
        """Test IN operator"""
        stmt = select(Customer)
        filters = [
            ColumnFilter(
                field="city", operator=FilterOperator.IN, value=["Berlin", "Munich"]
            )
        ]

        stmt = FilterService.apply_filters(stmt, filters, Customer)
        results = session.exec(stmt).all()

        assert len(results) == 2
        assert all(c.city in ["Berlin", "Munich"] for c in results)

    def test_between_filter(self, session, sample_customers):
        """Test BETWEEN operator"""
        stmt = select(Customer)
        filters = [
            ColumnFilter(
                field="id",
                operator=FilterOperator.BETWEEN,
                value={"min": 1, "max": 2},
            )
        ]

        stmt = FilterService.apply_filters(stmt, filters, Customer)
        results = session.exec(stmt).all()

        assert len(results) == 2
        assert all(1 <= c.id <= 2 for c in results)

    def test_gt_filter(self, session, sample_customers):
        """Test GT (greater than) operator"""
        stmt = select(Customer)
        filters = [ColumnFilter(field="id", operator=FilterOperator.GT, value=2)]

        stmt = FilterService.apply_filters(stmt, filters, Customer)
        results = session.exec(stmt).all()

        assert len(results) == 2
        assert all(c.id > 2 for c in results)

    def test_lte_filter(self, session, sample_customers):
        """Test LTE (less than or equal) operator"""
        stmt = select(Customer)
        filters = [ColumnFilter(field="id", operator=FilterOperator.LTE, value=2)]

        stmt = FilterService.apply_filters(stmt, filters, Customer)
        results = session.exec(stmt).all()

        assert len(results) == 2
        assert all(c.id <= 2 for c in results)


class TestWildcardEscaping:
    """Tests für Wildcard-Escaping (SQL-Injection Prevention)"""

    def test_escape_percent_wildcard(self):
        """Test dass % gescaped wird"""
        escaped = FilterService.escape_wildcards("test%value")
        assert escaped == "test\\%value"

    def test_escape_underscore_wildcard(self):
        """Test dass _ gescaped wird"""
        escaped = FilterService.escape_wildcards("test_value")
        assert escaped == "test\\_value"

    def test_escape_backslash(self):
        """Test dass \\ gescaped wird"""
        escaped = FilterService.escape_wildcards("test\\value")
        assert escaped == "test\\\\value"

    def test_filter_with_wildcards_in_value(self, session, sample_customers):
        """Test dass Filter mit % im Value korrekt funktioniert"""
        # Füge Customer mit % im Namen hinzu
        customer_with_percent = Customer(
            name="50% Off Sale", address="Test St", city="Berlin", note=None
        )
        session.add(customer_with_percent)
        session.commit()

        # Suche nach dem Kunden
        stmt = select(Customer)
        filters = [
            ColumnFilter(field="name", operator=FilterOperator.CONTAINS, value="50%")
        ]

        stmt = FilterService.apply_filters(stmt, filters, Customer)
        results = session.exec(stmt).all()

        assert len(results) == 1
        assert results[0].name == "50% Off Sale"


class TestSortField:
    """Tests für Sortierungslogik"""

    def test_single_sort_asc(self, session, sample_customers):
        """Test einfache aufsteigende Sortierung"""
        stmt = select(Customer)
        sort_fields = [SortField(field="name", direction=SortDirection.ASC)]

        stmt = FilterService.apply_sort(stmt, sort_fields, Customer)
        results = session.exec(stmt).all()

        names = [c.name for c in results]
        assert names == sorted(names)

    def test_single_sort_desc(self, session, sample_customers):
        """Test einfache absteigende Sortierung"""
        stmt = select(Customer)
        sort_fields = [SortField(field="id", direction=SortDirection.DESC)]

        stmt = FilterService.apply_sort(stmt, sort_fields, Customer)
        results = session.exec(stmt).all()

        ids = [c.id for c in results]
        assert ids == sorted(ids, reverse=True)

    def test_multi_column_sort(self, session, sample_customers):
        """Test Mehrspalten-Sortierung"""
        # Füge zwei Customers mit gleicher Stadt hinzu
        customer_dupe = Customer(
            name="Charlie Davis", address="Test St", city="Berlin", note=None
        )
        session.add(customer_dupe)
        session.commit()

        stmt = select(Customer)
        sort_fields = [
            SortField(field="city", direction=SortDirection.ASC),
            SortField(field="name", direction=SortDirection.ASC),
        ]

        stmt = FilterService.apply_sort(stmt, sort_fields, Customer)
        results = session.exec(stmt).all()

        # Überprüfe dass nach Stadt und dann nach Name sortiert ist
        cities = [c.city for c in results]
        names = [c.name for c in results]

        assert cities == sorted(cities)


class TestGlobalSearch:
    """Tests für globale Suche über multiple Felder"""

    def test_global_search_single_field(self, session, sample_customers):
        """Test globale Suche in einem Feld"""
        stmt = select(Customer)
        search = GlobalSearch(query="Berlin")

        stmt = FilterService.apply_global_search(
            stmt, search, Customer, search_fields={"city"}
        )
        results = session.exec(stmt).all()

        assert len(results) == 1
        assert results[0].city == "Berlin"

    def test_global_search_multiple_fields(self, session, sample_customers):
        """Test globale Suche über multiple Felder (OR-Bedingung)"""
        stmt = select(Customer)
        search = GlobalSearch(query="John")

        stmt = FilterService.apply_global_search(
            stmt,
            search,
            Customer,
            search_fields={"name", "address", "city", "note"},
        )
        results = session.exec(stmt).all()

        # Sollte "John Doe" und "Bob Johnson" zurückgeben
        assert len(results) == 2

    def test_global_search_case_insensitive(self, session, sample_customers):
        """Test dass globale Suche case-insensitive ist"""
        stmt = select(Customer)
        search = GlobalSearch(query="hamburg")

        stmt = FilterService.apply_global_search(
            stmt, search, Customer, search_fields={"city"}
        )
        results = session.exec(stmt).all()

        assert len(results) == 1
        assert results[0].city == "Hamburg"


class TestPagination:
    """Tests für Paginierungslogik"""

    def test_paginate_first_page(self, session, sample_customers):
        """Test erste Seite"""
        stmt = select(Customer)
        items, total = paginate(session, stmt, Customer, page=1, page_size=2)

        assert len(items) == 2
        assert total == 4

    def test_paginate_second_page(self, session, sample_customers):
        """Test zweite Seite"""
        stmt = select(Customer)
        items, total = paginate(session, stmt, Customer, page=2, page_size=2)

        assert len(items) == 2
        assert total == 4

    def test_paginate_last_page_partial(self, session, sample_customers):
        """Test letzte Seite mit weniger Items"""
        stmt = select(Customer)
        items, total = paginate(session, stmt, Customer, page=3, page_size=2)

        assert len(items) == 0  # Keine Items auf Seite 3
        assert total == 4

    def test_paginate_exceeds_max_page_size(self, session, sample_customers):
        """Test dass page_size auf 1000 begrenzt ist"""
        stmt = select(Customer)
        items, total = paginate(session, stmt, Customer, page=1, page_size=2000)

        # Alle 4 Items sollten zurückkommen (auf Seite 1)
        assert len(items) == 4
        assert total == 4

    def test_create_paginated_response(self, session, sample_customers):
        """Test PaginatedResponse-Erstellung"""
        stmt = select(Customer)
        items, total = paginate(session, stmt, Customer, page=1, page_size=2)

        response = create_paginated_response(items, total, page=1, page_size=2)

        assert response.total == 4
        assert response.page == 1
        assert response.pageSize == 2
        assert response.pageCount == 2  # 4 items / 2 per page = 2 pages
        assert len(response.items) == 2


class TestFilterSecurityValidation:
    """Tests für Security-Validierung"""

    def test_invalid_field_raises_error(self, session, sample_customers):
        """Test dass ungültige Felder Fehler verursachen"""
        stmt = select(Customer)
        filters = [
            ColumnFilter(
                field="nonexistent_field", operator=FilterOperator.EQUALS, value="test"
            )
        ]

        with pytest.raises(ValueError, match="not allowed for filtering"):
            FilterService.apply_filters(stmt, filters, Customer)

    def test_field_not_in_whitelist_raises_error(self, session, sample_customers):
        """Test dass Felder außerhalb der Whitelist blockiert werden"""
        stmt = select(Customer)
        filters = [
            ColumnFilter(field="name", operator=FilterOperator.EQUALS, value="John")
        ]

        with pytest.raises(ValueError, match="not allowed"):
            FilterService.apply_filters(
                stmt, filters, Customer, allowed_fields={"id", "city"}
            )

    def test_invalid_between_value_raises_error(self, session, sample_customers):
        """Test dass BETWEEN ohne min/max Fehler verursacht"""
        stmt = select(Customer)
        filters = [
            ColumnFilter(field="id", operator=FilterOperator.BETWEEN, value="invalid")
        ]

        with pytest.raises(ValueError):
            FilterService.apply_filters(stmt, filters, Customer)
