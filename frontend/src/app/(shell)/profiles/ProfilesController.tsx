"use client";

import { useEffect, useState, useCallback } from "react";
import { ProfilesTable } from "@/features/profiles/ProfilesTable";
import { ProfileDialog } from "@/features/profiles/ProfileDialog";
import type { Profile } from "@/types/profile";
import { useTableState } from "@/hooks/useTableState";
import { fetchTableData } from "@/services/table-api";
import type { ColumnConfig } from "@/components/TableHeader";

export default function ProfilesController() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null);
  const { state, updateFilters, updateSort } = useTableState(10);

  const columns: ColumnConfig[] = [
    { id: "name", label: "Name", sortable: true, filterable: true, filterType: "text" },
    { id: "city", label: "Stadt", sortable: true, filterable: true, filterType: "text" },
    {
      id: "include_tax",
      label: "Steuerstatus",
      sortable: true,
      filterable: true,
      filterType: "select",
      filterOptions: [
        { label: "USt", value: "true" },
        { label: "§19 UStG", value: "false" },
      ],
    },
  ];

  const loadProfiles = useCallback(async () => {
    setError(null);
    try {
      const resp = await fetchTableData<Profile>("/profiles/", state);
      setProfiles(resp.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler");
    }
  }, [state]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadProfiles();
  }, [loadProfiles]);

  const handleProfileSelect = (profile: Profile) => {
    setSelectedProfile(profile);
    setIsDialogOpen(true);
  };

  const handleCreateProfile = () => {
    setSelectedProfile(null);
    setIsDialogOpen(true);
  };

  const handleDialogClose = () => {
    setIsDialogOpen(false);
    setSelectedProfile(null);
  };

  const handleDialogSuccess = async () => {
    // Reload profiles after successful create/update
    await loadProfiles();
  };

  if (error) {
    return (
      <ProfilesTable
        profiles={[]}
        emptyMessage={
          <>
            <span>Fehler beim Laden - Keine Profile gefunden</span>
            <br />
            <span className="text-muted-foreground">failed request</span>
          </>
        }
      />
    );
  }

  return (
    <>
      <ProfilesTable
        profiles={profiles}
        onProfileSelect={handleProfileSelect}
        onCreateProfile={handleCreateProfile}
        columns={columns}
        filters={state.filters}
        sort={state.sort}
        onFiltersChange={updateFilters}
        onSortChange={updateSort}
      />
      <ProfileDialog
        isOpen={isDialogOpen}
        profile={selectedProfile}
        onClose={handleDialogClose}
        onSuccess={handleDialogSuccess}
      />
    </>
  );
}
