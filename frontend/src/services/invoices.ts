import { ApiClient } from "./base";
import type { Invoice } from "@/types/invoice";
import { logger } from "@/lib/logger";

const log = logger.createScoped("📄 INVOICES");

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
    log.debug("Fetching invoices list");
    return ApiClient.get<Invoice[]>("/invoices/");
  }

  static async getNumberPreview(): Promise<InvoiceNumberPreview> {
    log.debug("Fetching invoice number preview");
    return ApiClient.get<InvoiceNumberPreview>("/invoices/number-preview");
  }

  static async create(payload: InvoiceCreatePayload): Promise<Invoice> {
    log.info("Creating invoice", {
      profile_id: payload.profile_id,
      customer_id: payload.customer_id,
      items: payload.invoice_items.length,
      total: payload.total_amount,
    });
    const result = await ApiClient.post<Invoice>("/invoices/", payload);
    log.info("Invoice created successfully", { id: result.id, number: result.number });
    return result;
  }

  static async getById(id: number): Promise<Invoice> {
    log.debug(`Fetching invoice ${id}`);
    return ApiClient.get<Invoice>(`/invoices/${id}`);
  }
}
