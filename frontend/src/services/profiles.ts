import { ApiClient } from "./base";
import type { Profile } from "@/types/profile";
import { logger } from "@/lib/logger";

const log = logger.createScoped("⚙️ PROFILES");

/**
 * ProfilesService - Domain-orientierter Service für Profile.
 * SRP: Nur Datenzugriff (keine UI-Logik).
 */
export class ProfilesService {
  static async list(): Promise<Profile[]> {
    log.debug("Fetching profiles list");
    return ApiClient.get<Profile[]>("/profiles/");
  }

  /**
   * Search profiles by name (backend filters with ilike)
   * @param query - Search term (min 2 chars required by backend)
   * @returns Filtered profile list
   */
  static async search(query: string): Promise<Profile[]> {
    return this.searchEntities<Profile>("profiles", query);
  }

  /**
   * Generic search utility for entities.
   * @param entity - The entity name (e.g., "profiles")
   * @param query - Search term
   */
  private static async searchEntities<T>(entity: string, query: string): Promise<T[]> {
    if (query.length < 2) {
      log.debug(`Search query too short (<2 chars), returning empty`);
      return [];
    }
    try {
      log.debug(`Searching ${entity}`, { query });
      const results = await ApiClient.get<T[]>(`/${entity}/search?q=${encodeURIComponent(query)}`);
      log.debug(`${entity.charAt(0).toUpperCase() + entity.slice(1)} search results`, {
        count: (results as unknown[]).length,
      });
      return results;
    } catch (error) {
      log.error(`${entity.charAt(0).toUpperCase() + entity.slice(1)} search error`, error);
      throw error;
    }
  }
}
