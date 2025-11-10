import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InvoiceForm } from "./InvoiceForm";
import { InvoicesService } from "@/services/invoices";
import { ProfilesService } from "@/services/profiles";

// Mock the services
jest.mock("@/services/invoices");
jest.mock("@/services/profiles");
jest.mock("@/services/customers");
jest.mock("@/lib/logger", () => ({
  logger: {
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
  },
}));

describe("InvoiceForm", () => {
  beforeEach(() => {
    // Mock the number preview API call
    (InvoicesService.getNumberPreview as jest.Mock).mockResolvedValue({
      preview_number: "25 | 001",
    });

    // Mock the profiles API call
    (ProfilesService.list as jest.Mock).mockResolvedValue([
      { id: 1, name: "Hauptprofil", company_name: "Test GmbH" },
      { id: 2, name: "Nebenprofil", company_name: "Test2 GmbH" },
    ]);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("rendert alle Formularfelder inkl. Invoice Items und Tax-Felder", async () => {
    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Rechnungsnummer \(Vorschau\)/i)).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Kundennamen eingeben/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Profil/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Datum/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^Beschreibung/i)).toBeInTheDocument(); // Item description
      expect(screen.getByLabelText(/Menge/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Preis \(€\)/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Bruttobetrag/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Rechnung versteuern/i)).toBeInTheDocument();
    });
  });

  it("zeigt Rechnungsnummer-Vorschau nach Fetch", async () => {
    render(<InvoiceForm />);

    await waitFor(() => {
      const previewInput = screen.getByLabelText(
        /Rechnungsnummer \(Vorschau\)/i
      ) as HTMLInputElement;
      expect(previewInput.value).toBe("25 | 001");
      expect(previewInput).toBeDisabled();
    });

    expect(InvoicesService.getNumberPreview).toHaveBeenCalledTimes(1);
  });

  it("zeigt Fehlermeldung bei Fehler beim Fetch der Rechnungsnummer", async () => {
    (InvoicesService.getNumberPreview as jest.Mock).mockRejectedValue(new Error("Network error"));

    render(<InvoiceForm />);

    await waitFor(() => {
      const previewInput = screen.getByLabelText(
        /Rechnungsnummer \(Vorschau\)/i
      ) as HTMLInputElement;
      expect(previewInput.value).toBe("Fehler beim Laden");
    });
  });

  it("zeigt Pflichtfeld-Marker (*) an", async () => {
    render(<InvoiceForm />);

    await waitFor(() => {
      const labels = screen.getAllByText("*");
      // Kundenname, Profilname, Datum, Beschreibung, Menge, Preis = 6 Pflichtfelder
      expect(labels.length).toBeGreaterThanOrEqual(6);
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

  it("verhindert Submit bei leerem Formular", async () => {
    const user = userEvent.setup();
    const consoleSpy = jest.spyOn(console, "log");

    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Rechnung erstellen/i })).toBeInTheDocument();
    });

    const submitButton = screen.getByRole("button", { name: /Rechnung erstellen/i });
    await user.click(submitButton);

    // Wait for potential form submission
    await new Promise((resolve) => setTimeout(resolve, 200));

    // Verify onSubmit was NOT called (validation blocked it)
    expect(consoleSpy).not.toHaveBeenCalledWith(
      expect.stringContaining("✅ Form validation passed")
    );

    consoleSpy.mockRestore();
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

  it("validiert Beschreibung mit Mindestlänge 3", async () => {
    const user = userEvent.setup();
    const consoleSpy = jest.spyOn(console, "log");

    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /Rechnung erstellen/i })).toBeInTheDocument();
    });

    const descriptionInput = screen.getByLabelText(/^Beschreibung/i);
    await user.type(descriptionInput, "ab"); // Only 2 characters

    const submitButton = screen.getByRole("button", { name: /Rechnung erstellen/i });
    await user.click(submitButton);

    // Wait for potential form submission
    await new Promise((resolve) => setTimeout(resolve, 200));

    // Verify onSubmit was NOT called (validation blocked it)
    expect(consoleSpy).not.toHaveBeenCalledWith(
      expect.stringContaining("✅ Form validation passed")
    );

    consoleSpy.mockRestore();
  });

  it("akzeptiert Dezimalzahlen für Preis", async () => {
    const user = userEvent.setup();
    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByLabelText(/Preis \(€\)/i)).toBeInTheDocument();
    });

    const priceInput = screen.getByLabelText(/Preis \(€\)/i) as HTMLInputElement;
    await user.clear(priceInput);
    await user.type(priceInput, "99.99");

    expect(priceInput.value).toBe("99.99");
  });

  it("berechnet Gesamtsumme automatisch", async () => {
    const user = userEvent.setup();
    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByText(/Gesamtsumme:/i)).toBeInTheDocument();
    });

    // Initial sollte Gesamtsumme 0 sein (nicht Zwischensumme)
    expect(
      screen.getByText((content, element) => {
        return (
          element?.tagName === "SPAN" &&
          element?.className?.includes("text-xl") &&
          content === "0.00 €"
        );
      })
    ).toBeInTheDocument();

    // Setze Menge auf 2
    const quantityInput = screen.getByLabelText(/Menge/i);
    await user.clear(quantityInput);
    await user.type(quantityInput, "2");

    // Setze Preis auf 50
    const priceInput = screen.getByLabelText(/Preis \(€\)/i);
    await user.clear(priceInput);
    await user.type(priceInput, "50");

    // Summe sollte 100.00 € sein (Gesamtsumme, nicht Zwischensumme)
    await waitFor(() => {
      expect(
        screen.getByText((content, element) => {
          return (
            element?.tagName === "SPAN" &&
            element?.className?.includes("text-xl") &&
            content === "100.00 €"
          );
        })
      ).toBeInTheDocument();
    });
  });

  it("zeigt initial eine Rechnungsposition an", async () => {
    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByText(/Position 1/i)).toBeInTheDocument();
      expect(screen.getByText(/1 von max. 10 Positionen/i)).toBeInTheDocument();
    });
  });

  it("kann weitere Positionen hinzufügen", async () => {
    const user = userEvent.setup();
    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByText(/Position hinzufügen/i)).toBeInTheDocument();
    });

    const addButton = screen.getByRole("button", { name: /Position hinzufügen/i });
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByText(/Position 2/i)).toBeInTheDocument();
      expect(screen.getByText(/2 von max. 10 Positionen/i)).toBeInTheDocument();
    });
  });

  it("kann Positionen löschen wenn mehr als eine vorhanden", async () => {
    const user = userEvent.setup();
    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByText(/Position hinzufügen/i)).toBeInTheDocument();
    });

    // Füge zweite Position hinzu
    const addButton = screen.getByRole("button", { name: /Position hinzufügen/i });
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByText(/Position 2/i)).toBeInTheDocument();
    });

    // Lösch-Button sollte jetzt erscheinen
    const deleteButtons = screen.getAllByRole("button", { name: "" }).filter(
      (btn) => btn.querySelector("svg") // Trash2 icon button
    );

    expect(deleteButtons.length).toBeGreaterThan(0);

    // Klicke ersten Lösch-Button
    await user.click(deleteButtons[0]);

    // Position 2 sollte jetzt zu Position 1 werden (da wir die erste gelöscht haben)
    await waitFor(() => {
      expect(screen.getByText(/1 von max. 10 Positionen/i)).toBeInTheDocument();
    });
  });

  it("zeigt keine Lösch-Buttons wenn nur eine Position vorhanden", async () => {
    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByText(/Position 1/i)).toBeInTheDocument();
    });

    // Kein Lösch-Button sollte sichtbar sein (Trash2 icon)
    const deleteButtons = screen
      .queryAllByRole("button", { name: "" })
      .filter((btn) =>
        btn.querySelector("svg")?.closest("button")?.className.includes("text-destructive")
      );

    expect(deleteButtons.length).toBe(0);
  });

  it("limitiert Positionen auf maximal 10", async () => {
    const user = userEvent.setup();
    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByText(/Position hinzufügen/i)).toBeInTheDocument();
    });

    const addButton = screen.getByRole("button", { name: /Position hinzufügen/i });

    // Füge 9 weitere Positionen hinzu (zu der initialen 1 = 10 total)
    for (let i = 0; i < 9; i++) {
      await user.click(addButton);
    }

    await waitFor(() => {
      expect(screen.getByText(/10 von max. 10 Positionen/i)).toBeInTheDocument();
    });

    // Add-Button sollte jetzt verschwunden sein
    expect(screen.queryByText(/Position hinzufügen/i)).not.toBeInTheDocument();
  });

  it("berechnet Gesamtsumme über mehrere Positionen", async () => {
    const user = userEvent.setup();
    render(<InvoiceForm />);

    await waitFor(() => {
      expect(screen.getByText(/Gesamtsumme:/i)).toBeInTheDocument();
    });

    // Erste Position: 2 x 50 = 100
    const inputs = screen.getAllByLabelText(/Menge/i);
    const priceInputs = screen.getAllByLabelText(/Preis \(€\)/i);

    await user.clear(inputs[0]);
    await user.type(inputs[0], "2");
    await user.clear(priceInputs[0]);
    await user.type(priceInputs[0], "50");

    // Zweite Position hinzufügen
    const addButton = screen.getByRole("button", { name: /Position hinzufügen/i });
    await user.click(addButton);

    await waitFor(() => {
      expect(screen.getByText(/Position 2/i)).toBeInTheDocument();
    });

    // Zweite Position: 3 x 30 = 90
    const updatedInputs = screen.getAllByLabelText(/Menge/i);
    const updatedPriceInputs = screen.getAllByLabelText(/Preis \(€\)/i);

    await user.clear(updatedInputs[1]);
    await user.type(updatedInputs[1], "3");
    await user.clear(updatedPriceInputs[1]);
    await user.type(updatedPriceInputs[1], "30");

    // Gesamtsumme sollte 190.00 € sein (100 + 90)
    await waitFor(
      () => {
        const totalElement = screen.getByText((content, element) => {
          const classStr = element?.className;
          return !!(
            typeof classStr === "string" &&
            classStr.includes("text-xl") &&
            content.includes("190.00 €")
          );
        });
        expect(totalElement).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it("hat responsive Card-Wrapper mit max-width", async () => {
    const { container } = render(<InvoiceForm />);

    await waitFor(() => {
      const card = container.querySelector(".max-w-2xl");
      expect(card).toBeInTheDocument();
    });
  });
});
