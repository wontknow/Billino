export interface Invoice {
  id: number | string;
  number: string;
  date: string; // ISO date string
  customer_id: number;
  profile_id: number;
  total_amount: number; // aligns with backend InvoiceRead.total_amount
  include_tax?: boolean;
  tax_rate?: number;
  is_gross_amount: boolean;
  total_net?: number;
  total_tax?: number;
  total_gross?: number;
  customer_name?: string;
}
