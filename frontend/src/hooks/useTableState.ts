"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";
import type {
  ColumnFilter,
  FilterOperator,
  GlobalSearch,
  PaginationParams,
  SortField,
  TableState,
} from "@/types/table-filters";

/**
 * Hook für Synchronisation von Tabellen-State mit URL-Query-Parametern
 * Ermöglicht Sharing von Filter-/Sort-/Suchzuständen via URL
 *
 * @example
 * const { state, updateFilters, updateSort, updateSearch, updatePagination, reset } = useTableState();
 *
 * // Filter hinzufügen
 * updateFilters([...state.filters, { field: 'name', operator: 'contains', value: 'John' }]);
 *
 * // Sortierung ändern
 * updateSort([{ field: 'name', direction: 'asc' }]);
 */
export function useTableState(defaultPageSize: number = 10, namespace: string = "") {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Dekodiere den aktuellen State aus URL-Parametern
  const state = useMemo<TableState>(() => {
    const filters: ColumnFilter[] = [];
    const sort: SortField[] = [];

    // Parse Filters: "filter_field:operator:value"
    const filterParams = searchParams.getAll(`${namespace}filter`);
    filterParams.forEach((filterStr) => {
      const [field, operator, ...valueParts] = filterStr.split(":");
      if (field && operator && isFilterOperator(operator)) {
        const value = valueParts.join(":"); // Value kann auch Doppelpunkte enthalten
        try {
          // Versuche JSON zu parsen (für komplexe Werte)
          const parsedValue = JSON.parse(decodeURIComponent(value));
          filters.push({
            field,
            operator,
            value: parsedValue,
          });
        } catch {
          // Fallback auf String
          filters.push({
            field,
            operator,
            value: decodeURIComponent(value),
          });
        }
      }
    });

    // Parse Sort: "field:direction"
    const sortParams = searchParams.getAll(`${namespace}sort`);
    sortParams.forEach((sortStr) => {
      const [field, direction] = sortStr.split(":");
      if (field && direction) {
        sort.push({
          field,
          direction: direction as "asc" | "desc",
        });
      }
    });

    // Parse Pagination
    const page = parseInt(searchParams.get(`${namespace}page`) || "1", 10);
    const pageSize = parseInt(
      searchParams.get(`${namespace}pageSize`) || defaultPageSize.toString(),
      10
    );

    // Parse Global Search
    const search: GlobalSearch | undefined = searchParams.get(`${namespace}q`)
      ? {
          query: decodeURIComponent(searchParams.get(`${namespace}q`) || ""),
          fields: (searchParams.get(`${namespace}searchFields`) || "").split(",").filter(Boolean),
        }
      : undefined;

    return {
      filters,
      sort,
      search,
      pagination: {
        page: Math.max(1, page),
        pageSize: Math.max(1, pageSize),
      },
    };
  }, [searchParams, defaultPageSize, namespace]);

  /**
   * Aktualisiere die URL mit neuen Parametern
   */
  const updateUrl = useCallback(
    (newState: Partial<TableState>) => {
      const params = new URLSearchParams(searchParams);

      // Entferne alte Filter
      params.delete(`${namespace}filter`);

      // Setze neue Filter
      if (newState.filters) {
        newState.filters.forEach((filter) => {
          const value =
            typeof filter.value === "object"
              ? encodeURIComponent(JSON.stringify(filter.value))
              : encodeURIComponent(String(filter.value));
          params.append(`${namespace}filter`, `${filter.field}:${filter.operator}:${value}`);
        });
      }

      // Entferne alte Sort
      params.delete(`${namespace}sort`);

      // Setze neue Sort
      if (newState.sort) {
        newState.sort.forEach((s) => {
          params.append(`${namespace}sort`, `${s.field}:${s.direction}`);
        });
      }

      // Aktualisiere Pagination
      if (newState.pagination) {
        params.set(`${namespace}page`, newState.pagination.page.toString());
        params.set(`${namespace}pageSize`, newState.pagination.pageSize.toString());
      }

      // Aktualisiere Search
      if (newState.search) {
        params.set(`${namespace}q`, encodeURIComponent(newState.search.query));
        if (newState.search.fields?.length) {
          params.set(`${namespace}searchFields`, newState.search.fields.join(","));
        }
      } else {
        params.delete(`${namespace}q`);
        params.delete(`${namespace}searchFields`);
      }

      // Setze bei Filter/Sort/Search-Änderung auf Seite 1 zurück
      if (newState.filters || newState.sort || newState.search !== undefined) {
        params.set(`${namespace}page`, "1");
      }

      router.push(`?${params.toString()}`, { scroll: false });
    },
    [router, searchParams, namespace]
  );

  const updateFilters = useCallback(
    (filters: ColumnFilter[]) => {
      updateUrl({ ...state, filters });
    },
    [state, updateUrl]
  );

  const updateSort = useCallback(
    (sort: SortField[]) => {
      updateUrl({ ...state, sort });
    },
    [state, updateUrl]
  );

  const updateSearch = useCallback(
    (search: GlobalSearch | undefined) => {
      updateUrl({ ...state, search });
    },
    [state, updateUrl]
  );

  const updatePagination = useCallback(
    (pagination: PaginationParams) => {
      updateUrl({ ...state, pagination });
    },
    [state, updateUrl]
  );

  const reset = useCallback(() => {
    const params = new URLSearchParams(searchParams);
    ["filter", "sort", "page", "pageSize", "q", "searchFields"].forEach((key) =>
      params.delete(`${namespace}${key}`)
    );
    const qs = params.toString();
    router.push(qs ? `?${qs}` : "?", { scroll: false });
  }, [router, searchParams, namespace]);

  return {
    state,
    updateFilters,
    updateSort,
    updateSearch,
    updatePagination,
    reset,
  };
}

/**
 * Utility: Konvertiere TableState in Query-Parameter für API-Request
 */
export function tableStateToQueryParams(
  state: TableState
): Record<string, string | number | boolean | string[]> {
  type QueryParamValue = string | number | boolean | string[];

  const params: Record<string, QueryParamValue> = {
    page: state.pagination.page,
    pageSize: state.pagination.pageSize,
  };

  // Konvertiere Filters zu Backend-Format
  const filterParams: string[] = [];
  state.filters.forEach((filter) => {
    const rawValue =
      typeof filter.value === "object" ? JSON.stringify(filter.value) : String(filter.value);
    const value = encodeURIComponent(rawValue);
    filterParams.push(`${filter.field}:${filter.operator}:${value}`);
  });
  if (filterParams.length) {
    params.filter = filterParams;
  }

  // Konvertiere Sort zu Backend-Format
  const sortParams: string[] = [];
  state.sort.forEach((s) => {
    sortParams.push(`${s.field}:${s.direction}`);
  });
  if (sortParams.length) {
    params.sort = sortParams;
  }

  // Konvertiere Search
  if (state.search) {
    params.q = state.search.query;
    if (state.search.fields?.length) {
      params.searchFields = state.search.fields.join(",");
    }
  }

  return params;
}

function isFilterOperator(value: string): value is FilterOperator {
  return (
    value === "contains" ||
    value === "startsWith" ||
    value === "exact" ||
    value === "equals" ||
    value === "between" ||
    value === "in" ||
    value === "gt" ||
    value === "lt" ||
    value === "gte" ||
    value === "lte"
  );
}
