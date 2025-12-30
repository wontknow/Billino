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
        customer_id: 1,
        profile_id: 1,
        is_gross_amount: true,
        total_amount: 1234.56,
        total_net: 1037.78,
        total_gross: 1234.56,
        customer_name: "Kunde A",
      },
    ];

    (ApiClient.get as jest.Mock).mockResolvedValueOnce({
      items: mockInvoices,
      total: 1,
      page: 1,
      pageSize: 50,
      pageCount: 1,
    });

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
