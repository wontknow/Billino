import { ApiClient } from "./base";
import { logger } from "@/lib/logger";
import {
  SummaryInvoiceResponse,
  SummaryInvoiceCompact,
  SummaryInvoiceCreatePayload,
} from "@/types/summaryInvoices";

const log = logger.createScoped("📄 Summary Invoices");

export class SummaryInvoicesService {
  static async createSummaryInvoice(
    payload: SummaryInvoiceCreatePayload
  ): Promise<SummaryInvoiceResponse> {
    log.info("Creating summary invoice", {
      invoice_count: payload.invoice_ids.length,
      profile_id: payload.profile_id,
      has_date: Boolean(payload.date),
    });

    const created = await ApiClient.post<SummaryInvoiceResponse>("/summary-invoices/", payload);

    log.info("Summary invoice created", { id: created.id });
    return created;
  }

  static async createSummaryInvoiceForInvoices(invoiceIds: number[]): Promise<void> {
    log.info("Creating summary invoice", {
      invoice_count: invoiceIds.length,
    });
    await ApiClient.post<void>("/summary-invoices/", {
      invoice_ids: invoiceIds,
    });
    log.info("Summary invoice created successfully");
  }

  static async getSummaryInvoiceList(): Promise<SummaryInvoiceCompact[]> {
    log.debug("Fetching summary invoice list");
    const response = await ApiClient.get<SummaryInvoiceResponse[]>("/summary-invoices/");
    return response.map(this.convertResponseToCompact);
  }

  static async getSummaryInvoiceListByProfile(profileId: number): Promise<SummaryInvoiceCompact[]> {
    log.debug(`Fetching summary invoice list for profile ID: ${profileId}`);
    const response = await ApiClient.get<SummaryInvoiceResponse[]>(
      `/summary-invoices/by-profile/${profileId}`
    );
    return response.map(this.convertResponseToCompact);
  }

  private static convertResponseToCompact(
    summaryInvoice: SummaryInvoiceResponse
  ): SummaryInvoiceCompact {
    return {
      id: summaryInvoice.id,
      range_text: summaryInvoice.range_text,
      date: summaryInvoice.date,
      total_gross: summaryInvoice.total_gross,
      profile_id: summaryInvoice.profile_id,
    };
  }
}
