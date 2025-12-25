import { PDFsService } from "./pdfs";
import { ApiClient } from "./base";

jest.mock("./base");

const toBase64 = (input: string) => Buffer.from(input, "utf8").toString("base64");

const createStoredPdf = (overrides: Partial<import("@/types/pdf").StoredPDF> = {}) => ({
  id: 1,
  type: "invoice" as const,
  content: toBase64("PDF-CONTENT"),
  created_at: "2025-01-01T00:00:00Z",
  invoice_id: 42,
  summary_invoice_id: null,
  ...overrides,
});

describe("PDFsService", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("holt alle PDFs und wandelt Base64 in Blobs um", async () => {
    const storedPdfs = [createStoredPdf({ id: 1 }), createStoredPdf({ id: 2, invoice_id: 43 })];
    (ApiClient.get as jest.Mock).mockResolvedValueOnce(storedPdfs);

    const result = await PDFsService.getAllPdfsList();

    expect(ApiClient.get).toHaveBeenCalledWith("/pdfs/");
    expect(result).toHaveLength(2);
    expect(result[0].blob).toBeInstanceOf(Blob);
    expect((result[0].blob as Blob).size).toBeGreaterThan(0);
    expect(result[0].filename).toBe("invoice-42.pdf");
    expect(result[0].type).toBe("invoice");
  });

  it("holt ein einzelnes PDF per ID", async () => {
    const storedPdf = createStoredPdf({ id: 5, invoice_id: 99 });
    (ApiClient.get as jest.Mock).mockResolvedValueOnce(storedPdf);

    const result = await PDFsService.getPdfById(5);

    expect(ApiClient.get).toHaveBeenCalledWith("/pdfs/5");
    expect(result.blob).toBeInstanceOf(Blob);
    expect(result.blob.size).toBeGreaterThan(0);
    expect(result.filename).toBe("invoice-99.pdf");
  });

  it("erstellt ein PDF für eine Rechnung", async () => {
    const storedPdf = createStoredPdf({ id: 7, invoice_id: 77 });
    (ApiClient.post as jest.Mock).mockResolvedValueOnce(storedPdf);

    const result = await PDFsService.createPdfForInvoice(77);

    expect(ApiClient.post).toHaveBeenCalledWith("/pdfs/invoices/77", {});
    expect(result.blob).toBeInstanceOf(Blob);
    expect(result.blob.size).toBeGreaterThan(0);
    expect(result.filename).toBe("invoice-77.pdf");
  });

  it("erstellt ein A6-PDF für mehrere Rechnungen (bare array body, kein trailing slash)", async () => {
    const storedPdf = createStoredPdf({ id: 9, type: "a6_invoices", invoice_id: null });
    (ApiClient.post as jest.Mock).mockResolvedValueOnce(storedPdf);

    const result = await PDFsService.createPdfForA6Invoices([1, 2, 3]);

    expect(ApiClient.post).toHaveBeenCalledWith("/pdfs/a6-invoices", [1, 2, 3]);
    expect(result.type).toBe("a6_invoices");
    expect(result.filename).toBe("a6Invoices-9.pdf");
  });

  it("erstellt ein Sammelrechnungs-PDF mit recipient_name, wenn angegeben", async () => {
    const storedPdf = createStoredPdf({
      id: 11,
      type: "summary_invoice",
      summary_invoice_id: 55,
      invoice_id: null,
    });
    (ApiClient.post as jest.Mock).mockResolvedValueOnce(storedPdf);

    const result = await PDFsService.createPdfForSummaryInvoice(55, "Finanzamt");

    expect(ApiClient.post).toHaveBeenCalledWith("/pdfs/summary-invoices/55", {
      recipient_name: "Finanzamt",
    });
    expect(result.filename).toBe("summaryInvoice-55.pdf");
    expect(result.type).toBe("summary_invoice");
  });
});
