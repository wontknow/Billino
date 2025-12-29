"use client";

import { ArrowDown, ArrowUp, ArrowUpDown, ChevronDown } from "lucide-react";
import type React from "react";
import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { ColumnFilter, SortDirection, SortField } from "@/types/table-filters";

interface ColumnConfig {
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
  const [filterInputs, setFilterInputs] = useState<Record<string, string>>({});

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
        // Single-Sort
        if (currentSort) {
          // Toggle Richtung
          onSortChange([
            {
              field: columnId,
              direction: currentSort.direction === "asc" ? "desc" : "asc",
            },
          ]);
        } else {
          // Set Single-Sort
          onSortChange([{ field: columnId, direction: "asc" }]);
        }
      }
    },
    [sort, getColumnSort, onSortChange]
  );

  // Handle Filter (Text-Input)
  const handleTextFilter = useCallback(
    (columnId: string, value: string) => {
      setFilterInputs((prev) => ({ ...prev, [columnId]: value }));

      if (value.trim()) {
        // Entferne alte Filter für diese Spalte
        const newFilters = filters.filter((f) => f.field !== columnId);
        newFilters.push({
          field: columnId,
          operator: "contains",
          value: value.trim(),
        });
        onFilterChange(newFilters);
      } else {
        // Entferne Filter für diese Spalte
        onFilterChange(filters.filter((f) => f.field !== columnId));
      }
    },
    [filters, onFilterChange]
  );

  return (
    <thead>
      <tr className="border-b bg-slate-100">
        {columns.map((column) => {
          const columnSort = getColumnSort(column.id);
          const sortIndex = getSortIndex(column.id);
          const activeFilter = filters.find((f) => f.field === column.id);

          return (
            <th
              key={column.id}
              className="whitespace-nowrap px-4 py-3 text-left text-sm font-semibold"
            >
              <div className="flex items-center gap-2">
                {/* Label */}
                <span>{column.label}</span>

                {/* Sortierungs-Buttons */}
                {column.sortable && (
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 w-6 p-0"
                      onClick={(e) => handleSort(column.id, e.shiftKey || e.metaKey)}
                      title={`Click zum Sortieren${columnSort ? ", Shift+Click für Multi-Sort" : ""}`}
                    >
                      {columnSort ? (
                        columnSort.direction === "asc" ? (
                          <ArrowUp size={14} className="text-blue-600" />
                        ) : (
                          <ArrowDown size={14} className="text-blue-600" />
                        )
                      ) : (
                        <ArrowUpDown size={14} className="text-slate-400" />
                      )}
                    </Button>

                    {/* Multi-Sort Index */}
                    {sortIndex > 0 && columnSort && (
                      <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
                        {sortIndex}
                      </span>
                    )}
                  </div>
                )}

                {/* Filter-Dropdown */}
                {column.filterable && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className={`h-6 w-6 p-0 ${activeFilter ? "bg-green-100" : ""}`}
                        title="Filter für diese Spalte"
                      >
                        <ChevronDown size={14} className={activeFilter ? "text-green-600" : ""} />
                      </Button>
                    </DropdownMenuTrigger>

                    <DropdownMenuContent align="start" className="w-56">
                      {column.filterType === "text" && (
                        <>
                          <div className="px-2 py-2">
                            <input
                              type="text"
                              placeholder="Text eingeben..."
                              value={filterInputs[column.id] || ""}
                              onChange={(e) => handleTextFilter(column.id, e.target.value)}
                              className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
                            />
                          </div>

                          <DropdownMenuSeparator />

                          {activeFilter && (
                            <DropdownMenuItem
                              onClick={() => {
                                setFilterInputs((prev) => ({
                                  ...prev,
                                  [column.id]: "",
                                }));
                                onFilterChange(filters.filter((f) => f.field !== column.id));
                              }}
                              className="text-red-600"
                            >
                              Filter löschen
                            </DropdownMenuItem>
                          )}
                        </>
                      )}

                      {column.filterType === "select" && column.filterOptions && (
                        <>
                          {column.filterOptions.map((option) => (
                            <DropdownMenuItem
                              key={option.value}
                              onClick={() => {
                                const newFilters = filters.filter((f) => f.field !== column.id);
                                newFilters.push({
                                  field: column.id,
                                  operator: "exact",
                                  value: option.value,
                                });
                                onFilterChange(newFilters);
                              }}
                              className={
                                activeFilter?.value === option.value
                                  ? "bg-green-50 font-semibold"
                                  : ""
                              }
                            >
                              {option.label}
                            </DropdownMenuItem>
                          ))}

                          <DropdownMenuSeparator />

                          {activeFilter && (
                            <DropdownMenuItem
                              onClick={() => {
                                onFilterChange(filters.filter((f) => f.field !== column.id));
                              }}
                              className="text-red-600"
                            >
                              Filter löschen
                            </DropdownMenuItem>
                          )}
                        </>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </div>
            </th>
          );
        })}
      </tr>
    </thead>
  );
}
