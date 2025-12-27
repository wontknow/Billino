import { ApiClient, ApiError } from "./base";
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

  /**
   * Get PDF for invoice with lazy loading fallback.
   * If PDF doesn't exist, it triggers generation and waits for it.
   * Implements retry logic with exponential backoff to handle race conditions.
   */
  static async getPdfByInvoiceIdWithFallback(invoiceId: number): Promise<PdfBlob> {
    log.debug(`🔄 PDF Loading: Fetching PDF for invoice ${invoiceId}`);
    try {
      const pdfResponse: StoredPDF = await ApiClient.get<StoredPDF>(
        `/pdfs/by-invoice/${invoiceId}`
      );
      log.debug(`✅ PDF Loaded: Invoice ${invoiceId} PDF found`);
      return PDFsService.convertBase64ToPdfBlob(pdfResponse);
    } catch (error: unknown) {
      if (error instanceof ApiError) {
        if (error.status === 404) {
          log.warn(`⚠️ PDF Not Found: Invoice ${invoiceId} - Triggering generation...`);
          try {
            return await PDFsService.createPdfForInvoice(invoiceId);
          } catch (createError: unknown) {
            // Handle race condition: background thread created PDF between GET and POST
            if (createError instanceof ApiError && createError.status === 400) {
              log.warn(
                `⚠️ Race Condition Detected: Invoice ${invoiceId} - Retrying GET request...`
              );
              return await PDFsService.retryGetPdfByInvoiceId(invoiceId);
            }
            throw createError;
          }
        }
        log.error(`❌ PDF Loading Error [${error.status}]: Invoice ${invoiceId}`, error.detail);
      }
      throw error;
    }
  }

  /**
   * Get PDF for summary invoice with lazy loading fallback.
   * If PDF doesn't exist, it triggers generation and waits for it.
   * Implements retry logic with exponential backoff to handle race conditions.
   */
  static async getPdfBySummaryInvoiceIdWithFallback(
    summaryInvoiceId: number,
    recipientName?: string
  ): Promise<PdfBlob> {
    log.debug(`🔄 PDF Loading: Fetching PDF for summary invoice ${summaryInvoiceId}`);
    try {
      const pdfResponse: StoredPDF = await ApiClient.get<StoredPDF>(
        `/pdfs/by-summary/${summaryInvoiceId}`
      );
      log.debug(`✅ PDF Loaded: Summary invoice ${summaryInvoiceId} PDF found`);
      return PDFsService.convertBase64ToPdfBlob(pdfResponse);
    } catch (error: unknown) {
      if (error instanceof ApiError) {
        if (error.status === 404) {
          log.warn(
            `⚠️ PDF Not Found: Summary invoice ${summaryInvoiceId} - Triggering generation...`
          );
          try {
            return await PDFsService.createPdfForSummaryInvoice(summaryInvoiceId, recipientName);
          } catch (createError: unknown) {
            // Handle race condition: background thread created PDF between GET and POST
            if (createError instanceof ApiError && createError.status === 400) {
              log.warn(
                `⚠️ Race Condition Detected: Summary invoice ${summaryInvoiceId} - Retrying GET request...`
              );
              return await PDFsService.retryGetPdfBySummaryInvoiceId(summaryInvoiceId);
            }
            throw createError;
          }
        }
        log.error(
          `❌ PDF Loading Error [${error.status}]: Summary invoice ${summaryInvoiceId}`,
          error.detail
        );
      }
      throw error;
    }
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
    const pdfResponse: StoredPDF = await ApiClient.post<StoredPDF>(
      `/pdfs/a6-invoices`,
      invoiceList
    );
    log.info(`A6 PDF created for Invoices: ${invoiceList.join(", ")}, PDF ID: ${pdfResponse.id}`);
    return PDFsService.convertBase64ToPdfBlob(pdfResponse);
  }

  /**
   * Retry fetching PDF by invoice ID with exponential backoff.
   * Used to handle race conditions where PDF was created between GET and POST.
   */
  private static async retryGetPdfByInvoiceId(
    invoiceId: number,
    maxRetries: number = 3,
    baseDelay: number = 100
  ): Promise<PdfBlob> {
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const delay = baseDelay * Math.pow(2, attempt);
        log.debug(`🔄 Retry attempt ${attempt + 1}/${maxRetries} after ${delay}ms...`);
        await new Promise((resolve) => setTimeout(resolve, delay));

        const pdfResponse: StoredPDF = await ApiClient.get<StoredPDF>(
          `/pdfs/by-invoice/${invoiceId}`
        );
        log.debug(`✅ PDF Retrieved: Invoice ${invoiceId} on retry ${attempt + 1}`);
        return PDFsService.convertBase64ToPdfBlob(pdfResponse);
      } catch (error: unknown) {
        if (attempt === maxRetries - 1) {
          log.error(`❌ All retry attempts exhausted for invoice ${invoiceId}`);
          throw error;
        }
        log.debug(`⚠️ Retry ${attempt + 1} failed, continuing...`);
      }
    }
  }

  /**
   * Retry fetching PDF by summary invoice ID with exponential backoff.
   * Used to handle race conditions where PDF was created between GET and POST.
   */
  private static async retryGetPdfBySummaryInvoiceId(
    summaryInvoiceId: number,
    maxRetries: number = 3,
    baseDelay: number = 100
  ): Promise<PdfBlob> {
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const delay = baseDelay * Math.pow(2, attempt);
        log.debug(`🔄 Retry attempt ${attempt + 1}/${maxRetries} after ${delay}ms...`);
        await new Promise((resolve) => setTimeout(resolve, delay));

        const pdfResponse: StoredPDF = await ApiClient.get<StoredPDF>(
          `/pdfs/by-summary/${summaryInvoiceId}`
        );
        log.debug(`✅ PDF Retrieved: Summary invoice ${summaryInvoiceId} on retry ${attempt + 1}`);
        return PDFsService.convertBase64ToPdfBlob(pdfResponse);
      } catch (error: unknown) {
        if (attempt === maxRetries - 1) {
          log.error(`❌ All retry attempts exhausted for summary invoice ${summaryInvoiceId}`);
          throw error;
        }
        log.debug(`⚠️ Retry ${attempt + 1} failed, continuing...`);
      }
    }
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
