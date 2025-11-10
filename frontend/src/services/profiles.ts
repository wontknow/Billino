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
    if (query.length < 2) {
      console.log("🔍 Search query too short (<2 chars), returning empty");
      return [];
    }
    try {
      console.log("🔍 Searching profiles:", query);
      const results = await ApiClient.get<Profile[]>(
        `/profiles/search?q=${encodeURIComponent(query)}`
      );
      console.log("✅ Profile search results:", results.length, "items");
      return results;
    } catch (error) {
      console.error("❌ Profile search error:", error);
      throw error;
    }
  }
}
