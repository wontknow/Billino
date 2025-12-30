/**
 * Types für erweiterte Tabellen-Funktionalität
 * Unterstützt Filterung, Sortierung und Paginierung
 */

/**
 * Filtertypen für verschiedene Spalten
 */
export type FilterOperator =
  | "contains" // Text: enthält
  | "startsWith" // Text: beginnt mit
  | "exact" // Text/Enum: genaue Übereinstimmung
  | "equals" // Zahlen/Bool
  | "between" // Zahlen/Datum: Bereich
  | "in" // Auswahl: eines der Werte
  | "gt" // Größer als
  | "lt" // Kleiner als
  | "gte" // Größer oder gleich
  | "lte"; // Kleiner oder gleich

/**
 * Ein einzelner Filter für eine Spalte
 */
export interface ColumnFilter {
  field: string;
  operator: FilterOperator;
  value: string | number | boolean | string[] | { min?: number; max?: number };
}

/**
 * Sortierrichtung
 */
export type SortDirection = "asc" | "desc";

/**
 * Ein einzelner Sortierschritt (Spalte + Richtung)
 */
export interface SortField {
  field: string;
  direction: SortDirection;
}

/**
 * Globale Suchparameter
 */
export interface GlobalSearch {
  query: string;
  fields?: string[]; // Felder, in denen gesucht wird
}

/**
 * Paginierungsparameter
 */
export interface PaginationParams {
  page: number; // 1-basiert
  pageSize: number; // Einträge pro Seite
}

/**
 * Vollständige Tabellen-Zustandsparameter
 */
export interface TableState {
  filters: ColumnFilter[];
  sort: SortField[];
  search?: GlobalSearch;
  pagination: PaginationParams;
}

/**
 * Paginierte API-Antwort
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  pageCount: number;
}

/**
 * Query-Parameter-String-Repräsentation
 * für URL-Serialisierung
 */
export interface QueryParams {
  [key: string]: string | number | boolean;
}
