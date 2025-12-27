import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ProfileDialog } from "./ProfileDialog";
import type { Profile } from "@/types/profile";
import { ProfilesService } from "@/services/profiles";

// Mock ProfilesService
jest.mock("@/services/profiles");

describe("ProfileDialog", () => {
  const mockOnClose = jest.fn();
  const mockOnSuccess = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders dialog in create mode", () => {
    render(<ProfileDialog isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />);

    expect(screen.getByText("Neues Profil")).toBeInTheDocument();
    expect(screen.getByLabelText(/Firmenname/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Adresse/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Stadt/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Bankdaten/)).toBeInTheDocument();
    expect(screen.getByLabelText(/Steuernummer/)).toBeInTheDocument();
  });

  it("renders dialog in edit mode with profile data", () => {
    const profile: Profile = {
      id: 1,
      name: "Tech Solutions GmbH",
      address: "Hauptstraße 123",
      city: "10115 Berlin",
      bank_data: "DE89370400440532013000",
      tax_number: "DE123456789",
      include_tax: true,
      default_tax_rate: 0.19,
    };

    render(
      <ProfileDialog
        isOpen={true}
        profile={profile}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    expect(screen.getByText("Profil bearbeiten")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Tech Solutions GmbH")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Hauptstraße 123")).toBeInTheDocument();
    expect(screen.getByDisplayValue("10115 Berlin")).toBeInTheDocument();
    expect(screen.getByDisplayValue("DE89370400440532013000")).toBeInTheDocument();
    expect(screen.getByDisplayValue("DE123456789")).toBeInTheDocument();
    expect(screen.getByDisplayValue("19")).toBeInTheDocument();
  });

  it("creates a new profile on submit", async () => {
    const newProfile: Profile = {
      id: 1,
      name: "New Company GmbH",
      address: "Neue Straße 456",
      city: "20095 Hamburg",
      bank_data: "DE12345678901234567890",
      tax_number: "DE987654321",
      include_tax: true,
      default_tax_rate: 0.19,
    };

    (ProfilesService.create as jest.Mock).mockResolvedValueOnce(newProfile);

    render(<ProfileDialog isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />);

    fireEvent.change(screen.getByLabelText(/Firmenname/), {
      target: { value: "New Company GmbH" },
    });
    fireEvent.change(screen.getByLabelText(/Adresse/), {
      target: { value: "Neue Straße 456" },
    });
    fireEvent.change(screen.getByLabelText(/Stadt/), {
      target: { value: "20095 Hamburg" },
    });
    fireEvent.change(screen.getByLabelText(/Bankdaten/), {
      target: { value: "DE12345678901234567890" },
    });
    fireEvent.change(screen.getByLabelText(/Steuernummer/), {
      target: { value: "DE987654321" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Erstellen/ }));

    await waitFor(() => {
      expect(ProfilesService.create).toHaveBeenCalledWith({
        name: "New Company GmbH",
        address: "Neue Straße 456",
        city: "20095 Hamburg",
        bank_data: "DE12345678901234567890",
        tax_number: "DE987654321",
        include_tax: true,
        default_tax_rate: 0.19,
      });
    });

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalledWith(newProfile);
    });
  });

  it("updates existing profile on submit", async () => {
    const profile: Profile = {
      id: 1,
      name: "Tech Solutions GmbH",
      address: "Hauptstraße 123",
      city: "10115 Berlin",
      bank_data: "DE89370400440532013000",
      tax_number: "DE123456789",
      include_tax: true,
      default_tax_rate: 0.19,
    };

    const updatedProfile: Profile = {
      ...profile,
      name: "Tech Solutions GmbH Updated",
    };

    (ProfilesService.update as jest.Mock).mockResolvedValueOnce(updatedProfile);

    render(
      <ProfileDialog
        isOpen={true}
        profile={profile}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );

    fireEvent.change(screen.getByLabelText(/Firmenname/), {
      target: { value: "Tech Solutions GmbH Updated" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Speichern/ }));

    await waitFor(() => {
      expect(ProfilesService.update).toHaveBeenCalledWith(1, {
        name: "Tech Solutions GmbH Updated",
        address: "Hauptstraße 123",
        city: "10115 Berlin",
        bank_data: "DE89370400440532013000",
        tax_number: "DE123456789",
        include_tax: true,
        default_tax_rate: 0.19,
      });
    });

    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalledWith(updatedProfile);
    });
  });

  it("calls onClose when cancel button is clicked", () => {
    render(<ProfileDialog isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />);

    fireEvent.click(screen.getByRole("button", { name: /Abbrechen/ }));

    expect(mockOnClose).toHaveBeenCalled();
  });

  it("disables submit button when name is empty", () => {
    render(<ProfileDialog isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />);

    const submitButton = screen.getByRole("button", { name: /Erstellen/ });
    expect(submitButton).toBeDisabled();

    // Fill in name - button should be enabled
    fireEvent.change(screen.getByLabelText(/Firmenname/), {
      target: { value: "Test Company" },
    });
    expect(submitButton).not.toBeDisabled();
  });

  it("toggles tax rate field based on include_tax checkbox", () => {
    render(<ProfileDialog isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />);

    // Tax rate field should be visible by default (include_tax = true)
    expect(screen.getByLabelText(/Standard-Steuersatz/)).toBeInTheDocument();

    // Uncheck include_tax
    const checkbox = screen.getByLabelText(/Umsatzsteuer ausweisen/);
    fireEvent.click(checkbox);

    // Tax rate field should be hidden
    expect(screen.queryByLabelText(/Standard-Steuersatz/)).not.toBeInTheDocument();

    // Check include_tax again
    fireEvent.click(checkbox);

    // Tax rate field should be visible again
    expect(screen.getByLabelText(/Standard-Steuersatz/)).toBeInTheDocument();
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
      (ProfilesService.create as jest.Mock).mockRejectedValueOnce(error);

      render(<ProfileDialog isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />);

      fireEvent.change(screen.getByLabelText(/Firmenname/), {
        target: { value: "Test Company" },
      });

      fireEvent.click(screen.getByRole("button", { name: /Erstellen/ }));

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith("Fehler beim Speichern: Network error");
      });

      expect(mockOnSuccess).not.toHaveBeenCalled();
      expect(mockOnClose).not.toHaveBeenCalled();
    });

    it("displays error alert when update fails", async () => {
      const profile: Profile = {
        id: 1,
        name: "Tech Solutions GmbH",
        address: "Hauptstraße 123",
        city: "10115 Berlin",
        bank_data: "DE89370400440532013000",
        tax_number: "DE123456789",
        include_tax: true,
        default_tax_rate: 0.19,
      };

      const error = new Error("Update failed");
      (ProfilesService.update as jest.Mock).mockRejectedValueOnce(error);

      render(
        <ProfileDialog
          isOpen={true}
          profile={profile}
          onClose={mockOnClose}
          onSuccess={mockOnSuccess}
        />
      );

      fireEvent.change(screen.getByLabelText(/Firmenname/), {
        target: { value: "Updated Name" },
      });

      fireEvent.click(screen.getByRole("button", { name: /Speichern/ }));

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith("Fehler beim Speichern: Update failed");
      });

      expect(mockOnSuccess).not.toHaveBeenCalled();
    });

    it("displays generic error message for unknown errors", async () => {
      (ProfilesService.create as jest.Mock).mockRejectedValueOnce("Unknown error type");

      render(<ProfileDialog isOpen={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />);

      fireEvent.change(screen.getByLabelText(/Firmenname/), {
        target: { value: "Test Company" },
      });

      fireEvent.click(screen.getByRole("button", { name: /Erstellen/ }));

      await waitFor(() => {
        expect(global.alert).toHaveBeenCalledWith("Fehler beim Speichern: Unbekannter Fehler");
      });
    });
  });
});
