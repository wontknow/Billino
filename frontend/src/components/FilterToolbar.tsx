"use client";

import { X } from "lucide-react";
import type React from "react";
import { useCallback, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ColumnFilter, GlobalSearch } from "@/types/table-filters";

interface FilterToolbarProps {
  /**
   * Aktive Filter
   */
  filters: ColumnFilter[];

  /**
   * Aktive globale Suche
   */
  search?: GlobalSearch;

  /**
   * Callback wenn Filter geändert werden
   */
  onFiltersChange: (filters: ColumnFilter[]) => void;

  /**
   * Callback wenn Suche geändert wird
   */
  onSearchChange: (search: GlobalSearch | undefined) => void;

  /**
   * Callback zum Zurücksetzen
   */
  onReset: () => void;

  /**
   * Globale Suche ist aktiv
   */
  searchEnabled?: boolean;

  /**
   * Placeholder für Suchfeld
   */
  searchPlaceholder?: string;

  /**
   * Debounce-Verzögerung für Suche (ms)
   */
  searchDebounceMs?: number;
}

/**
 * Filter-Toolbar mit globaler Suche und aktiven Filter-Badges
 * Zeigt:
 * - Suchfeld mit Debounce
 * - Badge mit aktiven Filtern zum Löschen
 * - Reset-Button
 */
export function FilterToolbar({
  filters,
  search,
  onFiltersChange,
  onSearchChange,
  onReset,
  searchEnabled = true,
  searchPlaceholder = "Suche...",
  searchDebounceMs = 300,
}: FilterToolbarProps) {
  const [searchInput, setSearchInput] = useState(search?.query || "");
  const [searchTimeout, setSearchTimeout] = useState<NodeJS.Timeout | null>(null);

  const handleSearchChange = useCallback(
    (value: string) => {
      setSearchInput(value);

      // Clearexisting timeout
      if (searchTimeout) {
        clearTimeout(searchTimeout);
      }

      // Debounce search
      const timeout = setTimeout(() => {
        if (value.trim()) {
          onSearchChange({
            query: value.trim(),
            fields: undefined, // wird später via API-Service gesetzt
          });
        } else {
          onSearchChange(undefined);
        }
      }, searchDebounceMs);

      setSearchTimeout(timeout);
    },
    [searchTimeout, onSearchChange, searchDebounceMs]
  );

  const removeFilter = useCallback(
    (index: number) => {
      const newFilters = filters.filter((_, i) => i !== index);
      onFiltersChange(newFilters);
    },
    [filters, onFiltersChange]
  );

  const hasActiveFilters = filters.length > 0 || search?.query;

  return (
    <div className="flex flex-col gap-3 border-b bg-slate-50 p-4">
      {/* Suchfeld */}
      {searchEnabled && (
        <div className="flex-1">
          <Input
            type="text"
            placeholder={searchPlaceholder}
            value={searchInput}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="h-9"
          />
        </div>
      )}

      {/* Aktive Filter Badges */}
      {(filters.length > 0 || hasActiveFilters) && (
        <div className="flex flex-wrap gap-2">
          {search?.query && (
            <div className="flex items-center gap-1 rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700">
              <span>
                Suche: <strong>{search.query}</strong>
              </span>
              <button
                onClick={() => {
                  setSearchInput("");
                  onSearchChange(undefined);
                }}
                className="ml-1 hover:text-blue-900"
                title="Suche löschen"
              >
                <X size={14} />
              </button>
            </div>
          )}

          {filters.map((filter, index) => (
            <div
              key={`${filter.field}-${index}`}
              className="flex items-center gap-1 rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700"
            >
              <span>
                <strong>{filter.field}</strong> {filter.operator} {String(filter.value)}
              </span>
              <button
                onClick={() => removeFilter(index)}
                className="ml-1 hover:text-green-900"
                title="Filter entfernen"
              >
                <X size={14} />
              </button>
            </div>
          ))}

          {/* Reset Button */}
          {hasActiveFilters && (
            <Button
              variant="outline"
              size="sm"
              onClick={onReset}
              className="h-auto px-2 py-1 text-xs"
            >
              Zurücksetzen
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
