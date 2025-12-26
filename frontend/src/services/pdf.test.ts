import { PDFsService } from "./pdfs";
import { ApiClient, ApiError } from "./base";

// Mock only the ApiClient methods, not the entire module
jest.mock("./base", () => {
  const actual = jest.requireActual("./base");
  return {
    ...actual,
    ApiClient: {
      ...actual.ApiClient,
      get: jest.fn(),
      post: jest.fn(),
    },
  };
});

jest.mock("@/lib/logger", () => ({
  logger: {
    createScoped: () => ({
      debug: jest.fn(),
      info: jest.fn(),
      warn: jest.fn(),
      error: jest.fn(),
    }),
  },
}));

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

  describe("getPdfByInvoiceIdWithFallback", () => {
    it("returns PDF successfully when it exists", async () => {
      const storedPdf = createStoredPdf({ id: 10, invoice_id: 100 });
      (ApiClient.get as jest.Mock).mockResolvedValueOnce(storedPdf);

      const result = await PDFsService.getPdfByInvoiceIdWithFallback(100);

      expect(ApiClient.get).toHaveBeenCalledWith("/pdfs/by-invoice/100");
      expect(result.blob).toBeInstanceOf(Blob);
      expect(result.filename).toBe("invoice-100.pdf");
      expect(ApiClient.post).not.toHaveBeenCalled();
    });

    it("triggers PDF creation when 404 ApiError is returned", async () => {
      const error = new ApiError(404, "Not Found", { detail: "PDF not found" }, "PDF not found");
      const createdPdf = createStoredPdf({ id: 11, invoice_id: 100 });

      (ApiClient.get as jest.Mock).mockRejectedValueOnce(error);
      (ApiClient.post as jest.Mock).mockResolvedValueOnce(createdPdf);

      const result = await PDFsService.getPdfByInvoiceIdWithFallback(100);

      expect(ApiClient.get).toHaveBeenCalledWith("/pdfs/by-invoice/100");
      expect(ApiClient.post).toHaveBeenCalledWith("/pdfs/invoices/100", {});
      expect(result.blob).toBeInstanceOf(Blob);
      expect(result.filename).toBe("invoice-100.pdf");
    });

    it("propagates non-404 ApiError without triggering PDF creation", async () => {
      const error = new ApiError(
        500,
        "Internal Server Error",
        { detail: "Server error" },
        "Server error"
      );

      (ApiClient.get as jest.Mock).mockRejectedValueOnce(error);

      await expect(PDFsService.getPdfByInvoiceIdWithFallback(100)).rejects.toThrow(error);
      expect(ApiClient.get).toHaveBeenCalledWith("/pdfs/by-invoice/100");
      expect(ApiClient.post).not.toHaveBeenCalled();
    });

    it("propagates non-ApiError without triggering PDF creation", async () => {
      const error = new Error("Network error");

      (ApiClient.get as jest.Mock).mockRejectedValueOnce(error);

      await expect(PDFsService.getPdfByInvoiceIdWithFallback(100)).rejects.toThrow(error);
      expect(ApiClient.get).toHaveBeenCalledWith("/pdfs/by-invoice/100");
      expect(ApiClient.post).not.toHaveBeenCalled();
    });

    it("handles race condition: retries GET when POST returns 400", async () => {
      const getError = new ApiError(404, "Not Found", { detail: "PDF not found" }, "PDF not found");
      const postError = new ApiError(
        400,
        "Bad Request",
        { detail: "PDF already exists" },
        "PDF already exists"
      );
      const retryPdf = createStoredPdf({ id: 12, invoice_id: 100 });

      (ApiClient.get as jest.Mock)
        .mockRejectedValueOnce(getError) // Initial GET fails with 404
        .mockResolvedValueOnce(retryPdf); // Retry GET succeeds
      (ApiClient.post as jest.Mock).mockRejectedValueOnce(postError); // POST fails with 400

      const result = await PDFsService.getPdfByInvoiceIdWithFallback(100);

      expect(ApiClient.get).toHaveBeenCalledTimes(2);
      expect(ApiClient.get).toHaveBeenNthCalledWith(1, "/pdfs/by-invoice/100");
      expect(ApiClient.post).toHaveBeenCalledWith("/pdfs/invoices/100", {});
      expect(ApiClient.get).toHaveBeenNthCalledWith(2, "/pdfs/by-invoice/100");
      expect(result.blob).toBeInstanceOf(Blob);
      expect(result.filename).toBe("invoice-100.pdf");
    });
  });

  describe("getPdfBySummaryInvoiceIdWithFallback", () => {
    it("returns PDF successfully when it exists", async () => {
      const storedPdf = createStoredPdf({
        id: 12,
        type: "summary_invoice",
        summary_invoice_id: 200,
        invoice_id: null,
      });
      (ApiClient.get as jest.Mock).mockResolvedValueOnce(storedPdf);

      const result = await PDFsService.getPdfBySummaryInvoiceIdWithFallback(200);

      expect(ApiClient.get).toHaveBeenCalledWith("/pdfs/by-summary/200");
      expect(result.blob).toBeInstanceOf(Blob);
      expect(result.filename).toBe("summaryInvoice-200.pdf");
      expect(ApiClient.post).not.toHaveBeenCalled();
    });

    it("triggers PDF creation when 404 ApiError is returned", async () => {
      const error = new ApiError(404, "Not Found", { detail: "PDF not found" }, "PDF not found");
      const createdPdf = createStoredPdf({
        id: 13,
        type: "summary_invoice",
        summary_invoice_id: 200,
        invoice_id: null,
      });

      (ApiClient.get as jest.Mock).mockRejectedValueOnce(error);
      (ApiClient.post as jest.Mock).mockResolvedValueOnce(createdPdf);

      const result = await PDFsService.getPdfBySummaryInvoiceIdWithFallback(200);

      expect(ApiClient.get).toHaveBeenCalledWith("/pdfs/by-summary/200");
      expect(ApiClient.post).toHaveBeenCalledWith("/pdfs/summary-invoices/200", {});
      expect(result.blob).toBeInstanceOf(Blob);
      expect(result.filename).toBe("summaryInvoice-200.pdf");
    });

    it("triggers PDF creation with recipient_name when provided", async () => {
      const error = new ApiError(404, "Not Found", { detail: "PDF not found" }, "PDF not found");
      const createdPdf = createStoredPdf({
        id: 14,
        type: "summary_invoice",
        summary_invoice_id: 200,
        invoice_id: null,
      });

      (ApiClient.get as jest.Mock).mockRejectedValueOnce(error);
      (ApiClient.post as jest.Mock).mockResolvedValueOnce(createdPdf);

      const result = await PDFsService.getPdfBySummaryInvoiceIdWithFallback(200, "Test Company");

      expect(ApiClient.get).toHaveBeenCalledWith("/pdfs/by-summary/200");
      expect(ApiClient.post).toHaveBeenCalledWith("/pdfs/summary-invoices/200", {
        recipient_name: "Test Company",
      });
      expect(result.blob).toBeInstanceOf(Blob);
      expect(result.filename).toBe("summaryInvoice-200.pdf");
    });

    it("propagates non-404 ApiError without triggering PDF creation", async () => {
      const error = new ApiError(
        500,
        "Internal Server Error",
        { detail: "Server error" },
        "Server error"
      );

      (ApiClient.get as jest.Mock).mockRejectedValueOnce(error);

      await expect(PDFsService.getPdfBySummaryInvoiceIdWithFallback(200)).rejects.toThrow(error);
      expect(ApiClient.get).toHaveBeenCalledWith("/pdfs/by-summary/200");
      expect(ApiClient.post).not.toHaveBeenCalled();
    });

    it("propagates non-ApiError without triggering PDF creation", async () => {
      const error = new Error("Network error");

      (ApiClient.get as jest.Mock).mockRejectedValueOnce(error);

      await expect(PDFsService.getPdfBySummaryInvoiceIdWithFallback(200)).rejects.toThrow(error);
      expect(ApiClient.get).toHaveBeenCalledWith("/pdfs/by-summary/200");
      expect(ApiClient.post).not.toHaveBeenCalled();
    });

    it("handles race condition: retries GET when POST returns 400", async () => {
      const getError = new ApiError(404, "Not Found", { detail: "PDF not found" }, "PDF not found");
      const postError = new ApiError(
        400,
        "Bad Request",
        { detail: "PDF already exists" },
        "PDF already exists"
      );
      const retryPdf = createStoredPdf({
        id: 15,
        type: "summary_invoice",
        summary_invoice_id: 200,
        invoice_id: null,
      });

      (ApiClient.get as jest.Mock)
        .mockRejectedValueOnce(getError) // Initial GET fails with 404
        .mockResolvedValueOnce(retryPdf); // Retry GET succeeds
      (ApiClient.post as jest.Mock).mockRejectedValueOnce(postError); // POST fails with 400

      const result = await PDFsService.getPdfBySummaryInvoiceIdWithFallback(200);

      expect(ApiClient.get).toHaveBeenCalledTimes(2);
      expect(ApiClient.get).toHaveBeenNthCalledWith(1, "/pdfs/by-summary/200");
      expect(ApiClient.post).toHaveBeenCalledWith("/pdfs/summary-invoices/200", {});
      expect(ApiClient.get).toHaveBeenNthCalledWith(2, "/pdfs/by-summary/200");
      expect(result.blob).toBeInstanceOf(Blob);
      expect(result.filename).toBe("summaryInvoice-200.pdf");
    });
  });
});
