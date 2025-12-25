/**
 * PDF-related types for the application
 */

/**
 * StoredPDF response from backend
 * Content is base64-encoded PDF data
 */
export type StoredPDF = {
  id: number;
  type: "invoice" | "summary_invoice" | "a6_invoices";
  content: string; // Base64-encoded PDF content
  created_at: string; // ISO 8601 datetime
  invoice_id: number | null;
  summary_invoice_id: number | null;
};
/**
 * Filename generation for PDF types
 */
export type PdfFilename =
  | `summaryInvoice-${number}.pdf`
  | `invoice-${number}.pdf`
  | `a6Invoices-${number}.pdf`;

/**
 * PDF Blob with metadata for client-side handling
 */
export type PdfBlob = {
  blob: Blob;
  filename: PdfFilename;
  type: StoredPDF["type"];
};
