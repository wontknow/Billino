"use client";

import { useEffect, useState } from "react";
import { ProfilesService } from "@/services/profiles";
import { ProfilesTable } from "@/features/profiles/ProfilesTable";
import { ProfileDialog } from "@/features/profiles/ProfileDialog";
import type { Profile } from "@/types/profile";

export default function ProfilesController() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null);

  const loadProfiles = async () => {
    setError(null);
    try {
      const data = await ProfilesService.list();
      setProfiles(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unbekannter Fehler");
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadProfiles();
  }, []);

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

  const handleDialogSuccess = () => {
    // Reload profiles after successful create/update
    loadProfiles();
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
