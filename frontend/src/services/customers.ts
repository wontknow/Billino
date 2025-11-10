import { Customer } from "@/types/customer";
import { ApiClient } from "./base";

/**
 * Payload für Customer-Erstellung
 */
export interface CustomerCreatePayload {
  name: string;
  address?: string | null;
  city?: string | null;
}

/**
 * CustomersService is responsible for fetching customers from the backend API.
 * Single Responsibility: data access only (no UI concerns).
 */
export class CustomersService {
  static async list(): Promise<Customer[]> {
    return ApiClient.get<Customer[]>("/customers/");
  }

  static async create(payload: CustomerCreatePayload): Promise<Customer> {
    return ApiClient.post<Customer>("/customers/", payload);
  }

  /**
   * Sucht einen Customer nach exaktem Namen
   */
  static async findByName(name: string): Promise<Customer | null> {
    const customers = await this.list();
    const found = customers.find((c) => c.name.toLowerCase() === name.toLowerCase());
    return found || null;
  }

  /**
   * Generic search for entities by name (backend filters with ilike)
   * @param entity - The entity endpoint (e.g., "customers")
   * @param query - Search term (min 2 chars required by backend)
   * @returns Filtered entity list
   */
  private static async searchEntities<T>(entity: string, query: string): Promise<T[]> {
    if (query.length < 2) {
      console.log(`🔍 Search query too short (<2 chars) for ${entity}, returning empty`);
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

  /**
   * Search customers by name (backend filters with ilike)
   * @param query - Search term (min 2 chars required by backend)
   * @returns Filtered customer list
   */
  static async search(query: string): Promise<Customer[]> {
    return this.searchEntities<Customer>("customers", query);
  }
}
