import { ApiClient } from "./base";
import type { Invoice } from "@/types/invoice";

/**
 * InvoicesService - Domain-orientierter Service für Rechnungen.
 */
export class InvoicesService {
  static async list(): Promise<Invoice[]> {
    return ApiClient.get<Invoice[]>("/invoices/");
  }
}
