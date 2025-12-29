/**
 * Service für erweiterte Tabellenabfragen mit Filter, Sort und Pagination
 * Basiert auf ApiClient, erweitert um Query-Parameter für Filter/Sort
 */

import { ApiClient } from "./base";
import type {
  ColumnFilter,
  GlobalSearch,
  PaginatedResponse,
  SortField,
  TableState,
} from "@/types/table-filters";
import { logger } from "@/lib/logger";

const log = logger.createScoped("📊 TableAPI");

/**
 * Query-Parameter Builder für Filter/Sort/Paging
 */
export class TableQueryBuilder {
  private params: URLSearchParams = new URLSearchParams();

  /**
   * Füge Filterung hinzu
   */
  addFilters(filters: ColumnFilter[]): this {
    filters.forEach((filter, index) => {
      const value =
        typeof filter.value === "object" ? JSON.stringify(filter.value) : String(filter.value);

      this.params.append(`filter[${index}].field`, filter.field);
      this.params.append(`filter[${index}].operator`, filter.operator);
      this.params.append(`filter[${index}].value`, value);
    });

    return this;
  }

  /**
   * Füge Sortierung hinzu
   */
  addSort(sort: SortField[]): this {
    sort.forEach((s, index) => {
      this.params.append(`sort[${index}].field`, s.field);
      this.params.append(`sort[${index}].direction`, s.direction);
    });

    return this;
  }

  /**
   * Füge Paginierung hinzu
   */
  addPagination(page: number, pageSize: number): this {
    this.params.set("page", String(page));
    this.params.set("pageSize", String(pageSize));
    return this;
  }

  /**
   * Füge globale Suche hinzu
   */
  addSearch(search: GlobalSearch): this {
    this.params.set("q", search.query);
    if (search.fields?.length) {
      this.params.set("searchFields", search.fields.join(","));
    }
    return this;
  }

  /**
   * Gebe Query-String zurück
   */
  build(): string {
    return this.params.toString();
  }
}

/**
 * Helper für erweiterte Tabellenabfragen
 * Konvertiert TableState zu API-Anfrage
 */
export async function fetchTableData<T>(
  endpoint: string,
  state: TableState
): Promise<PaginatedResponse<T>> {
  const queryBuilder = new TableQueryBuilder();

  if (state.filters.length > 0) {
    queryBuilder.addFilters(state.filters);
  }

  if (state.sort.length > 0) {
    queryBuilder.addSort(state.sort);
  }

  if (state.search?.query) {
    queryBuilder.addSearch(state.search);
  }

  queryBuilder.addPagination(state.pagination.page, state.pagination.pageSize);

  const queryString = queryBuilder.build();
  const url = queryString ? `${endpoint}?${queryString}` : endpoint;

  log.debug(`📤 Fetching from ${endpoint}`, {
    filters: state.filters.length,
    sorts: state.sort.length,
    page: state.pagination.page,
    pageSize: state.pagination.pageSize,
  });

  try {
    const response = await ApiClient.get<PaginatedResponse<T>>(url);
    log.info(`✅ Fetched ${response.items.length} items`, {
      total: response.total,
      page: response.page,
    });
    return response;
  } catch (error) {
    log.error("❌ Failed to fetch table data", { error, endpoint, url });
    throw error;
  }
}
