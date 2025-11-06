import { z } from "zod";

/**
 * Zod Schema für Invoice-Formular
 * Validierung: Pflichtfelder, Datentypen, Formate
 */
export const invoiceFormSchema = z
  .object({
    customer_name: z.string().min(1, "Kundenname ist erforderlich"),
    profile_name: z.string().min(1, "Profilname ist erforderlich"),
    date: z.string().min(1, "Datum ist erforderlich"),
    total_amount: z.number().positive("Betrag muss größer als 0 sein"),
    is_gross_amount: z.boolean(),
    include_tax: z.boolean(),
    tax_rate: z.number().min(0).max(1).optional(),
    description: z.string().min(3, "Beschreibung muss mindestens 3 Zeichen haben"),
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
