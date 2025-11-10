import { z } from "zod";

/**
 * Zod Schema für einzelnes Invoice Item
 */
export const invoiceItemSchema = z.object({
  description: z.string().min(3, "Beschreibung muss mindestens 3 Zeichen haben"),
  quantity: z.number().int().positive("Menge muss größer als 0 sein"),
  price: z.number().positive("Preis muss größer als 0 sein"),
});

export type InvoiceItemFormData = z.infer<typeof invoiceItemSchema>;

/**
 * Zod Schema für Invoice-Formular
 * Validierung: Pflichtfelder, Datentypen, Formate
 *
 * Storage: IDs statt Names (für direkte API-Nutzung)
 * - customer_id: null = auto-create customer on submit
 * - profile_id: must be selected (required)
 */
export const invoiceFormSchema = z
  .object({
    customer_id: z.number().nullish().describe("Selected customer ID or null for auto-create"),
    profile_id: z
      .number({ required_error: "Profil ist erforderlich" })
      .min(1, "Profil ist erforderlich"),
    date: z.string().min(1, "Datum ist erforderlich"),
    is_gross_amount: z.boolean(),
    include_tax: z.boolean(),
    tax_rate: z.number().min(0).max(1).optional(),
    // Invoice items array (1-10 items)
    invoice_items: z
      .array(invoiceItemSchema)
      .min(1, "Mindestens ein Artikel erforderlich")
      .max(10, "Maximal 10 Artikel erlaubt"),
  })
  .refine(
    (data) => {
      // Wenn is_gross_amount true, dann muss include_tax auch true sein
      if (data.is_gross_amount && !data.include_tax) {
        return false;
      }
      return true;
    },
    {
      message: "Bruttobetrag kann nur bei versteuerter Rechnung angegeben werden",
      path: ["is_gross_amount"],
    }
  )
  .refine(
    (data) => {
      // Wenn include_tax true, dann muss tax_rate gesetzt sein
      if (data.include_tax && (data.tax_rate === undefined || data.tax_rate === null)) {
        return false;
      }
      return true;
    },
    {
      message: "Steuersatz muss angegeben werden, wenn versteuert",
      path: ["tax_rate"],
    }
  );

export type InvoiceFormData = z.infer<typeof invoiceFormSchema>;
