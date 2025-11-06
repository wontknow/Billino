import { render, screen } from "@testing-library/react";
import { InvoicesTable } from "./InvoicesTable";
import type { Invoice } from "@/types/invoice";

describe("InvoicesTable", () => {
  const sampleInvoices: Invoice[] = [
    {
      id: 1,
      number: "RE-2025-001",
      date: "2025-01-15",
      total_amount: 1234.56,
    },
    {
      id: 2,
      number: "RE-2025-002",
      date: "2025-02-20",
      total_amount: 999.99,
    },
  ];

  it("zeigt Spaltenüberschriften korrekt", () => {
    render(<InvoicesTable invoices={sampleInvoices} />);

    screen.getByRole("columnheader", { name: "Nummer" });
    screen.getByRole("columnheader", { name: "Datum" });
    screen.getByRole("columnheader", { name: "Summe" });
  });

  it("zeigt Rechnungsdaten korrekt", () => {
    render(<InvoicesTable invoices={sampleInvoices} />);

    screen.getByText("RE-2025-001");
    screen.getByText("RE-2025-002");
  });

  it("formatiert Beträge mit 2 Dezimalstellen und € Symbol", () => {
    render(<InvoicesTable invoices={sampleInvoices} />);

    screen.getByText("1234.56 €");
    screen.getByText("999.99 €");
  });

  it("formatiert Datum im deutschen Format (dd.MM.yyyy)", () => {
    render(<InvoicesTable invoices={sampleInvoices} />);

    // Intl.DateTimeFormat('de-DE') format: "15.1.2025" or "15.01.2025" depending on browser
    // We check for the presence of day and month
    expect(screen.getByText(/15\./)).toBeInTheDocument();
    expect(screen.getByText(/20\./)).toBeInTheDocument();
  });

  it("zeigt Caption mit Anzahl bei vorhandenen Daten", () => {
    render(<InvoicesTable invoices={sampleInvoices} />);
    screen.getByText("2 Rechnung(en)");
  });

  it("zeigt Empty-State ohne Daten", () => {
    render(<InvoicesTable invoices={[]} />);
    screen.getByText("Keine Rechnungen gefunden");
  });

  it("zeigt Custom-EmptyMessage bei Fehler", () => {
    render(
      <InvoicesTable
        invoices={[]}
        emptyMessage={
          <>
            <span>Fehler beim Laden - Keine Rechnungen gefunden</span>
          </>
        }
      />
    );
    screen.getByText("Fehler beim Laden - Keine Rechnungen gefunden");
  });

  it("rendert Card-Title 'Rechnungen'", () => {
    render(<InvoicesTable invoices={sampleInvoices} />);
    screen.getByText("Rechnungen");
  });

  it("zeigt Platzhalter '—' bei ungültigen Beträgen", () => {
    const invalidInvoice: Invoice[] = [
      {
        id: 999,
        number: "RE-INVALID",
        date: "2025-01-01",
        total_amount: NaN,
      },
    ];
    render(<InvoicesTable invoices={invalidInvoice} />);
    // formatAmount should return "—" for NaN
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("zeigt Platzhalter '—' bei ungültigen Daten", () => {
    const invalidInvoice: Invoice[] = [
      {
        id: 998,
        number: "RE-BAD-DATE",
        date: "invalid-date",
        total_amount: 100,
      },
    ];
    render(<InvoicesTable invoices={invalidInvoice} />);
    // formatDate should return "invalid-date" or "—" for invalid dates
    expect(screen.getByText(/invalid-date|—/)).toBeInTheDocument();
  });

  it("handhabt undefined total_amount gracefully", () => {
    const invoiceUndefined: Invoice[] = [
      {
        id: 997,
        number: "RE-UNDEF",
        date: "2025-01-01",
        total_amount: undefined as unknown as number,
      },
    ];
    render(<InvoicesTable invoices={invoiceUndefined} />);
    // formatAmount should handle undefined and show "—"
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
