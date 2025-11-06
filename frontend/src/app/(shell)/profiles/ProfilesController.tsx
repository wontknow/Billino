import { ProfilesService } from "@/services/profiles";
import { ProfilesTable } from "@/features/profiles/ProfilesTable";

export default async function ProfilesController() {
  let error: string | null = null;
  let profiles = [] as Awaited<ReturnType<typeof ProfilesService.list>>;
  try {
    profiles = await ProfilesService.list();
  } catch (err) {
    error = err instanceof Error ? err.message : "Unbekannter Fehler";
  }

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

  return <ProfilesTable profiles={profiles} />;
}
