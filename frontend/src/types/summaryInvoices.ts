export type SummaryInvoiceResponse = {
  id: number;
  range_text: string;
  date: string;
  profile_id: number;
  total_net: number;
  total_tax: number;
  total_gross: number;
  invoice_ids: number[];
  recipient_customer_id?: number;
  recipient_display_name?: string;
  profile_name?: string;
};

export type SummaryInvoiceCompact = {
  id: number;
  range_text: string;
  date: string;
  total_net: number;
  total_gross: number;
  profile_id: number;
  recipient_display_name?: string;
  profile_name?: string;
};

export type SummaryInvoiceCreatePayload = {
  profile_id: number;
  invoice_ids: number[];
  date?: string;
  recipient_name?: string;
  recipient_customer_id?: number;
};
