import { ApiClient } from "./base";
import type { Invoice } from "@/types/invoice";

/**
 * Backend payload types for invoice creation
 */
export interface InvoiceItemCreate {
  description: string;
  quantity: number;
  price: number;
}

export interface InvoiceCreatePayload {
  date: string;
  customer_id: number;
  profile_id: number;
  total_amount: number;
  invoice_items: InvoiceItemCreate[];
  include_tax?: boolean | null;
  tax_rate?: number | null;
  is_gross_amount: boolean;
}

export interface InvoiceNumberPreview {
  preview_number: string;
}

/**
 * InvoicesService - Domain-orientierter Service für Rechnungen.
 */
export class InvoicesService {
  static async list(): Promise<Invoice[]> {
    return ApiClient.get<Invoice[]>("/invoices/");
  }

  static async getNumberPreview(): Promise<InvoiceNumberPreview> {
    return ApiClient.get<InvoiceNumberPreview>("/invoices/number-preview");
  }

  static async create(payload: InvoiceCreatePayload): Promise<Invoice> {
    return ApiClient.post<Invoice>("/invoices/", payload);
  }

  static async getById(id: number): Promise<Invoice> {
    return ApiClient.get<Invoice>(`/invoices/${id}`);
  }
}
