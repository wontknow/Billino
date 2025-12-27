import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SummaryInvoiceDialog } from "./SummaryInvoiceDialog";
import { ProfilesService } from "@/services/profiles";
import { SummaryInvoicesService } from "@/services/summaryInvoices";
import type { Invoice } from "@/types/invoice";

jest.mock("@/services/profiles");
jest.mock("@/services/summaryInvoices");

const mockProfiles = [{ id: 1, name: "Profil A" }];
const invoices: Invoice[] = [
  {
    id: 10,
    number: "R-001",
    date: "2025-01-10",
    customer_id: 1,
    profile_id: 1,
    is_gross_amount: true,
    total_amount: 100,
  },
  {
    id: 11,
    number: "R-002",
    date: "2025-01-20",
    customer_id: 2,
    profile_id: 1,
    is_gross_amount: true,
    total_amount: 200,
  },
];

const setup = async () => {
  (ProfilesService.list as jest.Mock).mockResolvedValue(mockProfiles);
  (SummaryInvoicesService.createSummaryInvoice as jest.Mock).mockResolvedValue({
    id: 99,
    range_text: "",
    date: "2025-01-25",
    profile_id: 1,
    total_net: 0,
    total_tax: 0,
    total_gross: 0,
    invoice_ids: [10, 11],
  });

  const user = userEvent.setup();
  render(
    <SummaryInvoiceDialog isOpen invoices={invoices} onClose={jest.fn()} onSuccess={jest.fn()} />
  );

  // wait for profiles to load
  await waitFor(() => expect(ProfilesService.list).toHaveBeenCalled());
  return { user };
};

describe("SummaryInvoiceDialog", () => {
  it("erstellt Sammelrechnung mit korrekten Parametern (PDF wird im Backend generiert)", async () => {
    const { user } = await setup();

    // select both invoices
    const checkboxes = screen.getAllByRole("checkbox");
    await user.click(checkboxes[0]);
    await user.click(checkboxes[1]);

    // set recipient
    await user.type(
      screen.getByPlaceholderText("Kunde suchen oder neue Angabe..."),
      "Finanzamt Mustermann"
    );

    // submit
    await user.click(screen.getByRole("button", { name: "Sammelrechnung erstellen" }));

    await waitFor(() => {
      expect(SummaryInvoicesService.createSummaryInvoice).toHaveBeenCalledWith({
        profile_id: 1,
        invoice_ids: [10, 11],
        date: expect.any(String),
        recipient_name: "Finanzamt Mustermann",
      });
    });

    // PDF generation is now handled automatically in backend - no explicit call needed
  });
});
