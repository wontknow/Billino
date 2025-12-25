import { ApiClient } from "./base";
import { logger } from "@/lib/logger";
import { StoredPDF, PdfBlob, PdfFilename } from "@/types/pdf";

const log = logger.createScoped("PDFS");

/**
 * Payload für Customer-Erstellung
 */

/**
 * PDFsService is responsible for fetching PDFs from the backend API.
 * Single Responsibility: data access only (no UI concerns).
 */
export class PDFsService {
  static async getAllPdfsList(): Promise<PdfBlob[]> {
    log.debug("Fetching all PDFs list");
    const pdfResponses: StoredPDF[] = await ApiClient.get<StoredPDF[]>("/pdfs/");
    const pdfBlobList: PdfBlob[] = pdfResponses.map((pdfResponse) =>
      PDFsService.convertBase64ToPdfBlob(pdfResponse)
    );
    return pdfBlobList;
  }

  static async getPdfById(id: number): Promise<PdfBlob> {
    log.debug(`Fetching PDF by ID: ${id}`);
    const pdfResponse: StoredPDF = await ApiClient.get<StoredPDF>(`/pdfs/${id}`);
    return PDFsService.convertBase64ToPdfBlob(pdfResponse);
  }

  static async getPdfByInvoiceId(invoiceId: number): Promise<PdfBlob> {
    log.debug(`Fetching PDF by Invoice ID: ${invoiceId}`);
    const pdfResponse: StoredPDF = await ApiClient.get<StoredPDF>(`/pdfs/by-invoice/${invoiceId}`);
    return PDFsService.convertBase64ToPdfBlob(pdfResponse);
  }

  static async getPdfBySummaryInvoiceId(summaryInvoiceId: number): Promise<PdfBlob> {
    log.debug(`Fetching PDF by Summary Invoice ID: ${summaryInvoiceId}`);
    const pdfResponse: StoredPDF = await ApiClient.get<StoredPDF>(
      `/pdfs/by-summary/${summaryInvoiceId}`
    );
    return PDFsService.convertBase64ToPdfBlob(pdfResponse);
  }

  static async getAllA6Pdfs(): Promise<PdfBlob[]> {
    log.debug("Fetching all A6 PDFs");
    const pdfResponses: StoredPDF[] = await ApiClient.get<StoredPDF[]>(`/pdfs/a6/`);
    const pdfBlobList: PdfBlob[] = pdfResponses.map((pdfResponse) =>
      PDFsService.convertBase64ToPdfBlob(pdfResponse)
    );
    return pdfBlobList;
  }

  static async createPdfForInvoice(invoiceId: number): Promise<PdfBlob> {
    log.info(`Creating PDF for Invoice ID: ${invoiceId}`);
    const pdfResponse: StoredPDF = await ApiClient.post<StoredPDF>(
      `/pdfs/invoices/${invoiceId}`,
      {}
    );
    log.info(`PDF created for Invoice ID: ${invoiceId}, PDF ID: ${pdfResponse.id}`);
    return PDFsService.convertBase64ToPdfBlob(pdfResponse);
  }

  static async createPdfForSummaryInvoice(
    summaryInvoiceId: number,
    recipientName?: string
  ): Promise<PdfBlob> {
    log.info(`Creating PDF for Summary Invoice ID: ${summaryInvoiceId}`, {
      recipient_name: recipientName,
    });
    const payload = recipientName ? { recipient_name: recipientName } : {};
    const pdfResponse: StoredPDF = await ApiClient.post<StoredPDF>(
      `/pdfs/summary-invoices/${summaryInvoiceId}`,
      payload
    );
    log.info(`PDF created for Summary Invoice ID: ${summaryInvoiceId}, PDF ID: ${pdfResponse.id}`);
    return PDFsService.convertBase64ToPdfBlob(pdfResponse);
  }

  static async createPdfForA6Invoices(invoiceList: number[]): Promise<PdfBlob> {
    log.info(`Creating A6 PDF for Invoices: ${invoiceList.join(", ")}`);
    // Backend expects a bare array body and no trailing slash on the endpoint
    const pdfResponse: StoredPDF = await ApiClient.post<StoredPDF>(`/pdfs/a6-invoices`, invoiceList);
    log.info(`A6 PDF created for Invoices: ${invoiceList.join(", ")}, PDF ID: ${pdfResponse.id}`);
    return PDFsService.convertBase64ToPdfBlob(pdfResponse);
  }

  private static generateFileName(storedPdf: StoredPDF): PdfFilename {
    if (storedPdf.invoice_id) {
      return `invoice-${storedPdf.invoice_id}.pdf`;
    }
    if (storedPdf.summary_invoice_id) {
      return `summaryInvoice-${storedPdf.summary_invoice_id}.pdf`;
    }
    if (storedPdf.type === "a6_invoices") {
      return `a6Invoices-${storedPdf.id}.pdf`;
    }
    throw new Error("Unknown PDF type");
  }

  private static convertBase64ToPdfBlob(pdfResponse: StoredPDF): PdfBlob {
    const byteCharacters = atob(pdfResponse.content);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: "application/pdf" });
    const filename: PdfFilename = PDFsService.generateFileName(pdfResponse);
    return {
      blob,
      filename,
      type: pdfResponse.type,
    };
  }
}
