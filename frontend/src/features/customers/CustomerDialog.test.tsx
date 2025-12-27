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
  });

  it("renders dialog in edit mode with customer data", () => {
    const customer: Customer = {
      id: 1,
      name: "Max Mustermann",
      address: "Teststraße 123",
      city: "12345 Berlin",
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
  });

  it("creates a new customer on submit", async () => {
    const newCustomer: Customer = {
      id: 1,
      name: "Neuer Kunde",
      address: "Neue Straße 1",
      city: "10115 Berlin",
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

    fireEvent.click(screen.getByRole("button", { name: /Erstellen/ }));

    await waitFor(() => {
      expect(CustomersService.create).toHaveBeenCalledWith({
        name: "Neuer Kunde",
        address: "Neue Straße 1",
        city: "10115 Berlin",
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
});
