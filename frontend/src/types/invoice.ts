export interface Invoice {
  id: number | string;
  number: string;
  date: string; // ISO date string
  total_amount: number; // aligns with backend InvoiceRead.total_amount
}
