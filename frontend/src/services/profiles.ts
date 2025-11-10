import { ApiClient } from "./base";
import type { Profile } from "@/types/profile";

/**
 * ProfilesService - Domain-orientierter Service für Profile.
 * SRP: Nur Datenzugriff (keine UI-Logik).
 */
export class ProfilesService {
  static async list(): Promise<Profile[]> {
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
      console.log(`🔍 Search query too short (<2 chars), returning empty`);
      return [];
    }
    try {
      console.log(`🔍 Searching ${entity}:`, query);
      const results = await ApiClient.get<T[]>(
        `/${entity}/search?q=${encodeURIComponent(query)}`
      );
      console.log(`✅ ${entity.charAt(0).toUpperCase() + entity.slice(1)} search results:`, results.length, "items");
      return results;
    } catch (error) {
      console.error(`❌ ${entity.charAt(0).toUpperCase() + entity.slice(1)} search error:`, error);
      throw error;
    }
  }
}
