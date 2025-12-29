"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";
import type {
  ColumnFilter,
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
export function useTableState(defaultPageSize: number = 10) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Dekodiere den aktuellen State aus URL-Parametern
  const state = useMemo<TableState>(() => {
    const filters: ColumnFilter[] = [];
    const sort: SortField[] = [];

    // Parse Filters: "filter_field:operator:value"
    const filterParams = searchParams.getAll("filter");
    filterParams.forEach((filterStr) => {
      const [field, operator, ...valueParts] = filterStr.split(":");
      if (field && operator) {
        const value = valueParts.join(":"); // Value kann auch Doppelpunkte enthalten
        try {
          // Versuche JSON zu parsen (für komplexe Werte)
          const parsedValue = JSON.parse(decodeURIComponent(value));
          filters.push({
            field,
            operator: operator as any,
            value: parsedValue,
          });
        } catch {
          // Fallback auf String
          filters.push({
            field,
            operator: operator as any,
            value: decodeURIComponent(value),
          });
        }
      }
    });

    // Parse Sort: "field:direction"
    const sortParams = searchParams.getAll("sort");
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
    const page = parseInt(searchParams.get("page") || "1", 10);
    const pageSize = parseInt(searchParams.get("pageSize") || defaultPageSize.toString(), 10);

    // Parse Global Search
    const search: GlobalSearch | undefined = searchParams.get("q")
      ? {
          query: decodeURIComponent(searchParams.get("q") || ""),
          fields: (searchParams.get("searchFields") || "").split(",").filter(Boolean),
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
  }, [searchParams, defaultPageSize]);

  /**
   * Aktualisiere die URL mit neuen Parametern
   */
  const updateUrl = useCallback(
    (newState: Partial<TableState>) => {
      const params = new URLSearchParams(searchParams);

      // Entferne alte Filter
      params.delete("filter");

      // Setze neue Filter
      if (newState.filters) {
        newState.filters.forEach((filter) => {
          const value =
            typeof filter.value === "object"
              ? encodeURIComponent(JSON.stringify(filter.value))
              : encodeURIComponent(String(filter.value));
          params.append("filter", `${filter.field}:${filter.operator}:${value}`);
        });
      }

      // Entferne alte Sort
      params.delete("sort");

      // Setze neue Sort
      if (newState.sort) {
        newState.sort.forEach((s) => {
          params.append("sort", `${s.field}:${s.direction}`);
        });
      }

      // Aktualisiere Pagination
      if (newState.pagination) {
        params.set("page", newState.pagination.page.toString());
        params.set("pageSize", newState.pagination.pageSize.toString());
      }

      // Aktualisiere Search
      if (newState.search) {
        params.set("q", encodeURIComponent(newState.search.query));
        if (newState.search.fields?.length) {
          params.set("searchFields", newState.search.fields.join(","));
        }
      } else {
        params.delete("q");
        params.delete("searchFields");
      }

      // Setze bei Filter/Sort/Search-Änderung auf Seite 1 zurück
      if (newState.filters || newState.sort || newState.search !== undefined) {
        params.set("page", "1");
      }

      router.push(`?${params.toString()}`, { scroll: false });
    },
    [router, searchParams]
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
    router.push("?", { scroll: false });
  }, [router]);

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
): Record<string, string | number | boolean> {
  const params: Record<string, any> = {
    page: state.pagination.page,
    pageSize: state.pagination.pageSize,
  };

  // Konvertiere Filters zu Backend-Format
  state.filters.forEach((filter, idx) => {
    params[`filter[${idx}].field`] = filter.field;
    params[`filter[${idx}].operator`] = filter.operator;
    params[`filter[${idx}].value`] =
      typeof filter.value === "object" ? JSON.stringify(filter.value) : filter.value;
  });

  // Konvertiere Sort zu Backend-Format
  state.sort.forEach((sort, idx) => {
    params[`sort[${idx}].field`] = sort.field;
    params[`sort[${idx}].direction`] = sort.direction;
  });

  // Konvertiere Search
  if (state.search) {
    params.q = state.search.query;
    if (state.search.fields?.length) {
      params.searchFields = state.search.fields.join(",");
    }
  }

  return params;
}
