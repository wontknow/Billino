export interface Profile {
  id: number | string; // Backend liefert int
  name: string;
  address?: string;
  city?: string;
  bank_data?: string | null;
  tax_number?: string | null; // optional
  include_tax: boolean; // ob Steuer ausgewiesen wird
  default_tax_rate: number; // z.B. 0.19
}

// Entfernt: Invoice in eigene Datei ausgelagert
