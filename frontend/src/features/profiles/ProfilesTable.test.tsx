import { render, screen } from "@testing-library/react";
import { ProfilesTable } from "./ProfilesTable";
import type { Profile } from "@/types/profile";

describe("ProfilesTable", () => {
  const sampleProfiles: Profile[] = [
    {
      id: 1,
      name: "Max Mustermann",
      city: "Berlin",
      address: "Hauptstr. 1",
      include_tax: true,
      default_tax_rate: 0.19,
    },
    {
      id: 2,
      name: "Erika Musterfrau",
      city: "München",
      include_tax: false,
      default_tax_rate: 0.19,
    },
    {
      id: 3,
      name: "Firma XYZ",
      city: "Hamburg",
      include_tax: true,
      default_tax_rate: 0.07,
    },
  ];

  it("zeigt Spaltenüberschriften korrekt", () => {
    render(<ProfilesTable profiles={sampleProfiles} />);

    screen.getByRole("columnheader", { name: "Name" });
    screen.getByRole("columnheader", { name: "Stadt" });
    screen.getByRole("columnheader", { name: "Steuerstatus" });
  });

  it("zeigt Profile-Daten korrekt", () => {
    render(<ProfilesTable profiles={sampleProfiles} />);

    screen.getByText("Max Mustermann");
    screen.getByText("Berlin");
    screen.getByText("Erika Musterfrau");
    screen.getByText("München");
  });

  it("berechnet Steuerstatus korrekt: USt 19%", () => {
    render(<ProfilesTable profiles={sampleProfiles} />);
    screen.getByText("USt 19%");
  });

  it("berechnet Steuerstatus korrekt: USt 7%", () => {
    render(<ProfilesTable profiles={sampleProfiles} />);
    screen.getByText("USt 7%");
  });

  it("berechnet Steuerstatus korrekt: §19 UStG (keine USt)", () => {
    render(<ProfilesTable profiles={sampleProfiles} />);
    screen.getByText("§19 UStG (keine USt)");
  });

  it("zeigt Caption mit Anzahl bei vorhandenen Daten", () => {
    render(<ProfilesTable profiles={sampleProfiles} />);
    screen.getByText("3 Profil(e)");
  });

  it("zeigt Empty-State ohne Daten", () => {
    render(<ProfilesTable profiles={[]} />);
    screen.getByText("Keine Profile gefunden");
  });

  it("zeigt Custom-EmptyMessage bei Fehler", () => {
    render(
      <ProfilesTable
        profiles={[]}
        emptyMessage={
          <>
            <span>Fehler beim Laden - Keine Profile gefunden</span>
          </>
        }
      />
    );
    screen.getByText("Fehler beim Laden - Keine Profile gefunden");
  });

  it("rendert Card-Title 'Profile'", () => {
    render(<ProfilesTable profiles={sampleProfiles} />);
    screen.getByText("Profile");
  });

  it("zeigt Platzhalter '—' bei leerem city String", () => {
    const profileWithoutCity: Profile[] = [
      {
        id: 99,
        name: "Test ohne Stadt",
        city: "",
        include_tax: true,
        default_tax_rate: 0.19,
      },
    ];
    render(<ProfilesTable profiles={profileWithoutCity} />);
    // City ist empty string, component zeigt "—" in der Stadt-Spalte
    const cells = screen.getAllByRole("cell");
    const cityCell = cells.find((cell) => cell.textContent === "—");
    expect(cityCell).toBeInTheDocument();
  });
});
