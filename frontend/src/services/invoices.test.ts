import { InvoicesService } from "./invoices";
import { ApiClient } from "./base";
import type { Invoice } from "@/types/invoice";

jest.mock("./base");

describe("InvoicesService", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("ruft ApiClient.get mit korrektem Pfad auf", async () => {
    const mockInvoices: Invoice[] = [
      {
        id: 1,
        number: "RE-2025-001",
        date: "2025-01-15",
        total_amount: 1234.56,
      },
    ];

    (ApiClient.get as jest.Mock).mockResolvedValueOnce(mockInvoices);

    const result = await InvoicesService.list();

    expect(ApiClient.get).toHaveBeenCalledWith("/invoices/");
    expect(result).toEqual(mockInvoices);
  });

  it("propagiert Fehler von ApiClient", async () => {
    const error = new Error("Service unavailable");
    (ApiClient.get as jest.Mock).mockRejectedValueOnce(error);

    await expect(InvoicesService.list()).rejects.toThrow("Service unavailable");
  });
});
