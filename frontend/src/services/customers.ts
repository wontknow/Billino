import { Customer } from "@/types/customer";
import { ApiClient } from "./base";

/**
 * CustomersService is responsible for fetching customers from the backend API.
 * Single Responsibility: data access only (no UI concerns).
 */
export class CustomersService {
  static async list(): Promise<Customer[]> {
    return ApiClient.get<Customer[]>("/customers/");
  }
}
