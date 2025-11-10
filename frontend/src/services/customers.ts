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
}
