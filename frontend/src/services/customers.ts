import { Customer } from "@/types/customer";

/**
 * CustomersService is responsible for fetching customers from the backend API.
 * Single Responsibility: data access only (no UI concerns).
 */
export class CustomersService {
  static apiBase(): string {
    return process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || "http://localhost:8000/api";
  }

  static async list(): Promise<Customer[]> {
    const res = await fetch(`${this.apiBase()}/customers/`, {
      // Avoid caching to always reflect latest data
      cache: "no-store",
      // Ensure request from server has a sensible timeout in the future enhancement
    });
    if (!res.ok) {
      throw new Error(`Fehler beim Laden der Kunden: ${res.status} ${res.statusText}`);
    }
    return res.json();
  }
}
