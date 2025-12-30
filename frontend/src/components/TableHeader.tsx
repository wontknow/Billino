"use client";

import { ArrowDown, ArrowUp, ArrowUpDown, Filter } from "lucide-react";
import type React from "react";
import { useCallback, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DateRangePicker } from "@/components/ui/date-picker";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { ColumnFilter, SortField } from "@/types/table-filters";

export interface ColumnConfig {
  /**
   * Eindeutige Feld-ID
   */
  id: string;

  /**
   * Display-Name
   */
  label: string;

  /**
   * Sortierung möglich
   */
  sortable?: boolean;

  /**
   * Filterung möglich
   */
  filterable?: boolean;

  /**
   * Filter-Typ (für UI)
   */
  filterType?: "text" | "select" | "number" | "date" | "boolean";

  /**
   * Optionen für Select-Filter
   */
  filterOptions?: Array<{ label: string; value: string }>;
}

interface TableHeaderProps {
  /**
   * Spalten-Konfiguration
   */
  columns: ColumnConfig[];

  /**
   * Aktuelle Sortierungen (multi-sort)
   */
  sort: SortField[];

  /**
   * Aktive Filter
   */
  filters: ColumnFilter[];

  /**
   * Callback bei Sortierungsänderung
   * - Shift+Click: Zu Multi-Sort hinzufügen
   * - Click: Single-Sort
   * - Click auf aktive Spalte: Toggle Richtung
   */
  onSortChange: (sort: SortField[]) => void;

  /**
   * Callback bei Filter-Änderung
   */
  onFilterChange: (filters: ColumnFilter[]) => void;
}

/**
 * Tabellen-Header mit Mehrspaltiger Sortierung und Spalten-Filterung
 *
 * Sortierungsverhalten:
 * - Click: Single-Sort setzen (bisherige Sort-Einträge löschen)
 * - Shift+Click: Zu Multi-Sort hinzufügen/entfernen
 * - Click auf aktive Spalte: Sort-Richtung togglen
 *
 * Filterung:
 * - Dropdown-Menu pro Spalte mit Filter-Optionen
 */
export function TableHeader({
  columns,
  sort,
  filters,
  onSortChange,
  onFilterChange,
}: TableHeaderProps) {
  // Track uncommitted filter inputs (user is typing but hasn't been debounced yet)
  const [uncommittedInputs, setUncommittedInputs] = useState<Record<string, string>>({});
  const debounceRefs = useRef<Record<string, ReturnType<typeof setTimeout> | undefined>>({});

  // Derive filter input values from filters prop, overlaying uncommitted changes
  // Use useMemo to avoid recreating the object on every render
  const filterInputs = useMemo(() => {
    const inputs: Record<string, string> = {};
    for (const col of columns) {
      const af = filters.find((f) => f.field === col.id);
      // Use uncommitted value if exists, otherwise use committed filter value
      inputs[col.id] = uncommittedInputs[col.id] ?? (af ? String(af.value ?? "") : "");
    }
    return inputs;
  }, [columns, filters, uncommittedInputs]);

  // Finde aktive Sortierung für eine Spalte
  const getColumnSort = useCallback(
    (columnId: string) => {
      return sort.find((s) => s.field === columnId);
    },
    [sort]
  );

  // Finde Index der Spalte in Multi-Sort
  const getSortIndex = useCallback(
    (columnId: string) => {
      return sort.findIndex((s) => s.field === columnId) + 1; // 1-basiert
    },
    [sort]
  );

  // Handle Sortierung
  const handleSort = useCallback(
    (columnId: string, isShiftClick: boolean) => {
      const currentSort = getColumnSort(columnId);

      if (isShiftClick) {
        // Multi-Sort: Hinzufügen/Entfernen
        if (currentSort) {
          // Entferne aus Multi-Sort
          onSortChange(sort.filter((s) => s.field !== columnId));
        } else {
          // Füge zu Multi-Sort hinzu
          onSortChange([...sort, { field: columnId, direction: "asc" }]);
        }
      } else {
        // Single-Sort: cycle asc -> desc -> none
        if (!currentSort) {
          onSortChange([{ field: columnId, direction: "asc" }]);
        } else if (currentSort.direction === "asc") {
          onSortChange([{ field: columnId, direction: "desc" }]);
        } else {
          onSortChange([]); // none
        }
      }
    },
    [sort, getColumnSort, onSortChange]
  );

  // Handle Filter (Text-Input) mit Debounce, um Navigations-Reloads zu reduzieren
  const handleTextFilter = useCallback(
    (columnId: string, value: string) => {
      // Set uncommitted input value immediately for responsive UI
      setUncommittedInputs((prev) => ({ ...prev, [columnId]: value }));

      // clear previous timer for this column
      const t = debounceRefs.current[columnId];
      if (t) clearTimeout(t);

      debounceRefs.current[columnId] = setTimeout(() => {
        const trimmed = value.trim();
        if (trimmed) {
          const newFilters = filters.filter((f) => f.field !== columnId);
          newFilters.push({ field: columnId, operator: "contains", value: trimmed });
          onFilterChange(newFilters);
        } else {
          onFilterChange(filters.filter((f) => f.field !== columnId));
        }
        // Clear uncommitted value once it's committed
        setUncommittedInputs((prev) => {
          const next = { ...prev };
          delete next[columnId];
          return next;
        });
      }, 300);
    },
    [filters, onFilterChange]
  );

  // Helper function to update date filters with smart single date vs range logic
  const updateDateFilters = useCallback(
    (
      columnId: string,
      fromValue: string | undefined,
      toValue: string | undefined,
      currentFilters: ColumnFilter[]
    ): ColumnFilter[] => {
      // Remove all date-related filters for this column
      const baseFilters = currentFilters
        .filter((f) => f.field !== `${columnId}_from`)
        .filter((f) => f.field !== `${columnId}_to`)
        .filter((f) => f.field !== columnId);

      if (toValue) {
        if (fromValue && fromValue !== toValue) {
          // Range: both dates different
          baseFilters.push({
            field: `${columnId}_from`,
            operator: "gte",
            value: fromValue,
          });
          baseFilters.push({
            field: `${columnId}_to`,
            operator: "lte",
            value: toValue,
          });
        } else {
          // Single date: exact match on the column
          baseFilters.push({
            field: columnId,
            operator: "exact",
            value: toValue,
          });
        }
      } else if (fromValue) {
        // Only from date remains: exact match on the column
        baseFilters.push({
          field: columnId,
          operator: "exact",
          value: fromValue,
        });
      }

      return baseFilters;
    },
    []
  );

  return (
    <thead>
      <tr className="border-b">
        {columns.map((column) => {
          const columnSort = getColumnSort(column.id);
          const sortIndex = getSortIndex(column.id);
          const activeFilter = filters.find((f) => f.field === column.id);
          return (
            <th
              key={column.id}
              className="whitespace-nowrap px-4 py-3 text-left text-sm font-semibold"
            >
              <div className="flex items-center gap-2 text-foreground">
                {/* Label opens filter popup */}
                {column.filterable ? (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <button
                        className={[
                          "group inline-flex items-center gap-1 rounded-md px-1.5 py-0.5",
                          activeFilter ? "ring-1 ring-black" : "hover:ring-1 hover:ring-black/30",
                        ].join(" ")}
                      >
                        <span className="leading-none text-base font-semibold">{column.label}</span>
                        <Filter className="h-3 w-3 opacity-50 group-hover:opacity-80" />
                      </button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start" className="w-60 p-2">
                      {column.filterType === "text" && (
                        <div className="flex items-center gap-1">
                          <Input
                            type="text"
                            placeholder="Filtern…"
                            value={filterInputs[column.id] || ""}
                            onChange={(e) => handleTextFilter(column.id, e.target.value)}
                            className="h-8 text-sm"
                          />
                          {activeFilter && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-8"
                              onClick={() => {
                                setUncommittedInputs((prev) => {
                                  const next = { ...prev };
                                  delete next[column.id];
                                  return next;
                                });
                                onFilterChange(filters.filter((f) => f.field !== column.id));
                              }}
                            >
                              Zurücksetzen
                            </Button>
                          )}
                        </div>
                      )}

                      {column.filterType === "select" && column.filterOptions && (
                        <div className="flex w-full flex-col gap-1">
                          <select
                            className="h-8 w-full rounded border bg-background px-2 text-sm"
                            value={(activeFilter?.value as string) || ""}
                            onChange={(e) => {
                              if (!e.target.value) {
                                onFilterChange(filters.filter((f) => f.field !== column.id));
                              } else {
                                const newFilters = filters.filter((f) => f.field !== column.id);
                                newFilters.push({
                                  field: column.id,
                                  operator: "exact",
                                  value: e.target.value,
                                });
                                onFilterChange(newFilters);
                              }
                            }}
                          >
                            <option value="">– alle –</option>
                            {column.filterOptions.map((opt) => (
                              <option key={opt.value} value={opt.value}>
                                {opt.label}
                              </option>
                            ))}
                          </select>
                          {activeFilter && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-8 self-end"
                              onClick={() =>
                                onFilterChange(filters.filter((f) => f.field !== column.id))
                              }
                            >
                              Zurücksetzen
                            </Button>
                          )}
                        </div>
                      )}

                      {column.filterType === "date" && (
                        <div className="flex w-full flex-col gap-2">
                          <DateRangePicker
                            valueFrom={
                              (filters.find((f) => f.field === `${column.id}_from`)?.value as
                                | string
                                | undefined) ||
                              (filters.find((f) => f.field === column.id)?.value as
                                | string
                                | undefined)
                            }
                            valueTo={
                              filters.find((f) => f.field === `${column.id}_to`)?.value as
                                | string
                                | undefined
                            }
                            onValueFromChange={(value) => {
                              const currentTo = filters.find((f) => f.field === `${column.id}_to`)
                                ?.value as string | undefined;

                              const updatedFilters = updateDateFilters(
                                column.id,
                                value,
                                currentTo,
                                filters
                              );

                              onFilterChange(updatedFilters);
                            }}
                            onValueToChange={(value) => {
                              const currentFrom =
                                (filters.find((f) => f.field === `${column.id}_from`)?.value as
                                  | string
                                  | undefined) ||
                                (filters.find((f) => f.field === column.id)?.value as
                                  | string
                                  | undefined);

                              const updatedFilters = updateDateFilters(
                                column.id,
                                currentFrom,
                                value,
                                filters
                              );

                              onFilterChange(updatedFilters);
                            }}
                          />
                          {(filters.find((f) => f.field === `${column.id}_from`) ||
                            filters.find((f) => f.field === `${column.id}_to`) ||
                            filters.find((f) => f.field === column.id)) && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-8 self-end"
                              onClick={() =>
                                onFilterChange(
                                  filters
                                    .filter((f) => f.field !== `${column.id}_from`)
                                    .filter((f) => f.field !== `${column.id}_to`)
                                    .filter((f) => f.field !== column.id)
                                )
                              }
                            >
                              Zurücksetzen
                            </Button>
                          )}
                        </div>
                      )}

                      <DropdownMenuSeparator />
                      <div className="text-xs text-muted-foreground px-1">
                        Esc schließt das Menü
                      </div>
                    </DropdownMenuContent>
                  </DropdownMenu>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 hover:ring-1 hover:ring-black/30">
                    <span className="leading-none text-base font-semibold">{column.label}</span>
                  </span>
                )}

                {/* Sortierungs-Buttons */}
                {column.sortable && (
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={(e) => handleSort(column.id, e.shiftKey || e.metaKey)}
                      title={`Sortieren${columnSort ? " (erneut klicken zum Entfernen)" : ""}`}
                    >
                      {columnSort ? (
                        columnSort.direction === "asc" ? (
                          <ArrowUp size={14} />
                        ) : (
                          <ArrowDown size={14} />
                        )
                      ) : (
                        <ArrowUpDown size={14} className="text-muted-foreground" />
                      )}
                    </Button>

                    {/* Multi-Sort Index: immer Platz reservieren, Sichtbarkeit togglen */}
                    <span
                      className={[
                        "inline-flex h-5 min-w-[1.25rem] items-center justify-center rounded px-1 text-[10px] font-medium",
                        // Border-Breite immer reservieren, Farbe nur bei aktivem Sort sichtbar
                        columnSort ? "border" : "border border-transparent",
                        // Wenn nicht aktiv sortiert, Platz behalten aber nicht anzeigen
                        columnSort ? "opacity-100" : "opacity-0",
                        "transition-opacity",
                      ].join(" ")}
                      aria-hidden={!columnSort}
                    >
                      {columnSort ? sortIndex : null}
                    </span>
                  </div>
                )}
              </div>
            </th>
          );
        })}
      </tr>
    </thead>
  );
}
