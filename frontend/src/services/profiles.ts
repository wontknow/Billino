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
}
