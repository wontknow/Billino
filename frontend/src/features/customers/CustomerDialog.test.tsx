import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { CustomerDialog } from "./CustomerDialog";
import type { Customer } from "@/types/customer";
import { CustomersService } from "@/services/customers";

// Mock CustomersService
jest.mock("@/services/customers");

describe("CustomerDialog", () => {
  const mockOnClose = jest.fn();
  const mockOnSuccess = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders dialog in create mode", () => {
    render(<CustomerDialog isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />);

    expect(screen.getByText("Neuer Kunde")).toBeInTheDocument();
    expect(screen.getByLabelText(/Name/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Adresse/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Stadt/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Notizen/)).toBeInTheDocument();
  });

  it("renders dialog in edit mode with customer data", () => {
    const customer: Customer = {
      id: 1,
      name: "Max Mustermann",
      address: "Teststraße 123",
      city: "12345 Berlin",
      note: "Bevorzugt blaue Farben",
    };

    render(
      <CustomerDialog
        isOpen={true}
        customer={customer}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    expect(screen.getByText("Kunde bearbeiten")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Max Mustermann")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Teststraße 123")).toBeInTheDocument();
    expect(screen.getByDisplayValue("12345 Berlin")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Bevorzugt blaue Farben")).toBeInTheDocument();
  });

  it("creates a new customer on submit", async () => {
    const newCustomer: Customer = {
      id: 1,
      name: "Neuer Kunde",
      address: "Neue Straße 1",
      city: "10115 Berlin",
      note: "Test Notiz",
    };

    (CustomersService.create as jest.Mock).mockResolvedValueOnce(newCustomer);

    render(<CustomerDialog isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />);

    fireEvent.change(screen.getByLabelText(/Name/), {
      target: { value: "Neuer Kunde" },
    });
    fireEvent.change(screen.getByLabelText(/Adresse/), {
      target: { value: "Neue Straße 1" },
    });
    fireEvent.change(screen.getByLabelText(/Stadt/), {
      target: { value: "10115 Berlin" },
    });
    fireEvent.change(screen.getByLabelText(/Notizen/), {
      target: { value: "Test Notiz" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Erstellen/ }));

    await waitFor(() => {
      expect(CustomersService.create).toHaveBeenCalledWith({
        name: "Neuer Kunde",
        address: "Neue Straße 1",
        city: "10115 Berlin",
        note: "Test Notiz",
      });
    });

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalledWith(newCustomer);
    });
  });

  it("updates existing customer on submit", async () => {
    const customer: Customer = {
      id: 1,
      name: "Max Mustermann",
      address: "Teststraße 123",
      city: "12345 Berlin",
      note: "Original Notiz",
    };

    const updatedCustomer: Customer = {
      ...customer,
      name: "Max Mustermann Aktualisiert",
    };

    (CustomersService.update as jest.Mock).mockResolvedValueOnce(updatedCustomer);

    render(
      <CustomerDialog
        isOpen={true}
        customer={customer}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    fireEvent.change(screen.getByLabelText(/Name/), {
      target: { value: "Max Mustermann Aktualisiert" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Speichern/ }));

    await waitFor(() => {
      expect(CustomersService.update).toHaveBeenCalledWith(1, {
        name: "Max Mustermann Aktualisiert",
        address: "Teststraße 123",
        city: "12345 Berlin",
        note: "Original Notiz",
      });
    });

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalledWith(updatedCustomer);
    });
  });

  it("calls onClose when cancel button is clicked", () => {
    render(<CustomerDialog isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />);

    fireEvent.click(screen.getByRole("button", { name: /Abbrechen/ }));

    expect(mockOnClose).toHaveBeenCalled();
  });

  it("disables submit button when name is empty", () => {
    render(<CustomerDialog isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />);

    const submitButton = screen.getByRole("button", { name: /Erstellen/ });
    expect(submitButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/Name/), {
      target: { value: "Test Name" },
    });

    expect(submitButton).not.toBeDisabled();
  });

  describe("Error handling", () => {
    beforeEach(() => {
      // Mock window.alert
      global.alert = jest.fn();
    });

    afterEach(() => {
      jest.restoreAllMocks();
    });

    it("displays error alert when create fails", async () => {
      const error = new Error("Network error");
      (CustomersService.create as jest.Mock).mockRejectedValueOnce(error);

      render(<CustomerDialog isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />);

      fireEvent.change(screen.getByLabelText(/Name/), {
        target: { value: "Test Customer" },
      });

      fireEvent.click(screen.getByRole("button", { name: /Erstellen/ }));

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith("Fehler beim Speichern: Network error");
      });

      expect(mockOnSuccess).not.toHaveBeenCalled();
      expect(mockOnClose).not.toHaveBeenCalled();
    });

    it("displays error alert when update fails", async () => {
      const customer: Customer = {
        id: 1,
        name: "Max Mustermann",
        address: "Teststraße 123",
        city: "12345 Berlin",
        note: null,
      };

      const error = new Error("Update failed");
      (CustomersService.update as jest.Mock).mockRejectedValueOnce(error);

      render(
        <CustomerDialog
          isOpen={true}
          customer={customer}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );

      fireEvent.change(screen.getByLabelText(/Name/), {
        target: { value: "Updated Name" },
      });

      fireEvent.click(screen.getByRole("button", { name: /Speichern/ }));

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith("Fehler beim Speichern: Update failed");
      });

      expect(mockOnSuccess).not.toHaveBeenCalled();
    });

    it("displays generic error message for unknown errors", async () => {
      (CustomersService.create as jest.Mock).mockRejectedValueOnce("Unknown error type");

      render(<CustomerDialog isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />);

      fireEvent.change(screen.getByLabelText(/Name/), {
        target: { value: "Test Customer" },
      });

      fireEvent.click(screen.getByRole("button", { name: /Erstellen/ }));

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith("Fehler beim Speichern: Unbekannter Fehler");
      });
    });
  });
});
