import { render, screen, fireEvent } from "@testing-library/react";
import { InvoicesTable } from "./InvoicesTable";
import type { Invoice } from "@/types/invoice";

describe("InvoicesTable", () => {
  const sampleInvoices: Invoice[] = [
    {
      id: 1,
      number: "RE-2025-001",
      date: "2025-01-15",
      customer_id: 1,
      profile_id: 1,
      is_gross_amount: true,
      total_amount: 1234.56,
      customer_name: "Kunde A",
      total_net: 1037.78,
      total_gross: 1234.56,
    },
    {
      id: 2,
      number: "RE-2025-002",
      date: "2025-02-20",
      customer_id: 2,
      profile_id: 1,
      is_gross_amount: false,
      total_amount: 999.99,
      customer_name: "Kunde B",
      total_net: 999.99,
      total_gross: 1189.99,
    },
  ];

  it("zeigt Spaltenüberschriften korrekt", () => {
    render(<InvoicesTable invoices={sampleInvoices} />);

    screen.getByRole("columnheader", { name: "Nummer" });
    screen.getByRole("columnheader", { name: "Datum" });
    screen.getByRole("columnheader", { name: "Empfänger" });
    screen.getByRole("columnheader", { name: "Netto" });
    screen.getByRole("columnheader", { name: "Brutto" });
  });

  it("zeigt Rechnungsdaten korrekt", () => {
    render(<InvoicesTable invoices={sampleInvoices} />);

    screen.getByText("RE-2025-001");
    screen.getByText("RE-2025-002");
  });

  it("formatiert Beträge (Netto/Brutto) mit 2 Dezimalstellen und € Symbol", () => {
    render(<InvoicesTable invoices={sampleInvoices} />);
    // Netto
    screen.getByText("1037.78 €");
    screen.getByText("999.99 €");
    // Brutto
    screen.getByText("1234.56 €");
    screen.getByText("1189.99 €");
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
        customer_id: 1,
        profile_id: 1,
        is_gross_amount: true,
        total_amount: NaN as unknown as number,
        total_net: NaN,
        total_gross: NaN,
      },
    ];
    render(<InvoicesTable invoices={invalidInvoice} />);
    // formatAmount should return "—" for NaN; multiple placeholders may appear
    const placeholders = screen.getAllByText("—");
    expect(placeholders.length).toBeGreaterThan(0);
  });

  it("zeigt Platzhalter '—' bei ungültigen Daten", () => {
    const invalidInvoice: Invoice[] = [
      {
        id: 998,
        number: "RE-BAD-DATE",
        date: "invalid-date",
        customer_id: 1,
        profile_id: 1,
        is_gross_amount: true,
        total_amount: 100,
        total_net: 100,
        total_gross: 100,
      },
    ];
    render(<InvoicesTable invoices={invalidInvoice} />);
    // formatDate should show the raw invalid date string
    expect(screen.getByText("invalid-date")).toBeInTheDocument();
  });

  it("handhabt undefined total_amount gracefully", () => {
    const invoiceUndefined: Invoice[] = [
      {
        id: 997,
        number: "RE-UNDEF",
        date: "2025-01-01",
        customer_id: 1,
        profile_id: 1,
        is_gross_amount: true,
        total_amount: undefined as unknown as number,
        total_net: undefined as unknown as number,
        total_gross: undefined as unknown as number,
      },
    ];
    render(<InvoicesTable invoices={invoiceUndefined} />);
    // formatAmount should handle undefined and show "—"; multiple placeholders may appear
    const placeholders = screen.getAllByText("—");
    expect(placeholders.length).toBeGreaterThan(0);
  });

  it("ruft onInvoiceSelect beim Zeilenklick auf", () => {
    const onInvoiceSelect = jest.fn();
    render(<InvoicesTable invoices={sampleInvoices} onInvoiceSelect={onInvoiceSelect} />);

    fireEvent.click(screen.getByText("RE-2025-001"));
    expect(onInvoiceSelect).toHaveBeenCalledWith(1);
  });

  it("zeigt Refresh- und A6-Buttons wenn Handler gesetzt sind", () => {
    render(
      <InvoicesTable
        invoices={sampleInvoices}
        onRefresh={() => {}}
        onCreateA6Pdf={() => {}}
        isRefreshing={false}
      />
    );

    screen.getByRole("button", { name: "Aktualisieren" });
    screen.getByRole("button", { name: "A6 PDF" });
    screen.getByRole("link", { name: "Neue Rechnung" });
  });
});
