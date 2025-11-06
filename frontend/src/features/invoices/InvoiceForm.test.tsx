import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InvoiceForm } from "./InvoiceForm";
import { CustomersService } from "@/services/customers";
import { ProfilesService } from "@/services/profiles";

// Mock die Services
jest.mock("@/services/customers");
jest.mock("@/services/profiles");

const mockCustomers = [
  { id: 1, name: "Kunde A", city: "Berlin" },
  { id: 2, name: "Kunde B", city: "München" },
];

const mockProfiles = [
  { id: 1, name: "Profil 1", include_tax: true, default_tax_rate: 19.0 },
  { id: 2, name: "Profil 2", include_tax: false, default_tax_rate: 0.0 },
];

describe("InvoiceForm", () => {
  beforeEach(() => {
    // Setup mocks
    (CustomersService.list as jest.Mock).mockResolvedValue(mockCustomers);
    (ProfilesService.list as jest.Mock).mockResolvedValue(mockProfiles);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("rendert alle Formularfelder inkl. Tax-Felder", async () => {
    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Kundenname/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Profilname/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Datum/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Betrag \(€\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Bruttobetrag/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Rechnung versteuern/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Beschreibung/i)).toBeInTheDocument();
    });
  });

  it("zeigt Pflichtfeld-Marker (*) an", async () => {
    render(<InvoiceForm />);

    await waitFor(() => {
      const labels = screen.getAllByText("*");
      // Kundenname, Profilname, Datum, Betrag, Beschreibung = 5 Pflichtfelder
      expect(labels.length).toBeGreaterThanOrEqual(5);
    });
  });

  it("zeigt Submit-Button an", async () => {
    render(<InvoiceForm />);

    await waitFor(() => {
      const submitButton = screen.getByRole("button", { name: /Rechnung erstellen/i });
      expect(submitButton).toBeInTheDocument();
    });
  });

  it("setzt heutiges Datum als Default", async () => {
    render(<InvoiceForm />);

    await waitFor(() => {
      const dateInput = screen.getByLabelText(/Datum/i) as HTMLInputElement;
      const today = new Date().toISOString().split("T")[0];
      expect(dateInput.value).toBe(today);
    });
  });

  it("zeigt Validierungsfehler bei leerem Submit", async () => {
    const user = userEvent.setup();
    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Rechnung erstellen/i })).toBeInTheDocument();
    });

    const submitButton = screen.getByRole("button", { name: /Rechnung erstellen/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Kundenname ist erforderlich/i)).toBeInTheDocument();
      expect(screen.getByText(/Profilname ist erforderlich/i)).toBeInTheDocument();
      expect(screen.getByText(/Betrag muss größer als 0 sein/i)).toBeInTheDocument();
    });
  });

  it("zeigt Steuersatz-Feld nur wenn versteuert aktiviert", async () => {
    const user = userEvent.setup();
    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Rechnung versteuern/i)).toBeInTheDocument();
    });

    // Steuersatz sollte anfangs NICHT sichtbar sein
    expect(screen.queryByLabelText(/Steuersatz/i)).not.toBeInTheDocument();

    // Aktiviere "Rechnung versteuern"
    const includeTaxCheckbox = screen.getByLabelText(/Rechnung versteuern/i);
    await user.click(includeTaxCheckbox);

    // Jetzt sollte Steuersatz-Feld erscheinen
    await waitFor(() => {
      expect(screen.getByLabelText(/Steuersatz/i)).toBeInTheDocument();
    });
  });

  it("zeigt Validierungsfehler bei zu kurzer Beschreibung", async () => {
    const user = userEvent.setup();
    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Beschreibung/i)).toBeInTheDocument();
    });

    const descriptionInput = screen.getByLabelText(/Beschreibung/i);
    await user.type(descriptionInput, "AB"); // Nur 2 Zeichen

    const submitButton = screen.getByRole("button", { name: /Rechnung erstellen/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Beschreibung muss mindestens 3 Zeichen haben/i)).toBeInTheDocument();
    });
  });

  it("akzeptiert Dezimalzahlen für Betrag", async () => {
    const user = userEvent.setup();
    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Betrag \(€\)/i)).toBeInTheDocument();
    });

    const amountInput = screen.getByLabelText(/Betrag \(€\)/i) as HTMLInputElement;
    await user.clear(amountInput);
    await user.type(amountInput, "99.99");

    expect(amountInput.value).toBe("99.99");
  });

  it("hat responsive Card-Wrapper mit max-width", async () => {
    const { container } = render(<InvoiceForm />);

    await waitFor(() => {
      const card = container.querySelector(".max-w-2xl");
      expect(card).toBeInTheDocument();
    });
  });
});
