"use client";

import React from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { invoiceFormSchema, type InvoiceFormData } from "@/types/invoice-form";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function InvoiceForm() {
  // TODO: Später für Autocomplete wieder aktivieren wenn Backend Search-Endpoints bereit sind
  // const [customers, setCustomers] = useState<Customer[]>([]);
  // const [profiles, setProfiles] = useState<Profile[]>([]);
  // const [loading, setLoading] = useState(true);

  // useEffect(() => {
  //   const loadData = async () => {
  //     try {
  //       const [customersData, profilesData] = await Promise.all([
  //         CustomersService.list(),
  //         ProfilesService.list(),
  //       ]);
  //       setCustomers(customersData);
  //       setProfiles(profilesData);
  //     } catch (error) {
  //       console.error("Fehler beim Laden von Kunden/Profilen:", error);
  //     } finally {
  //       setLoading(false);
  //     }
  //   };
  //   loadData();
  // }, []);

  const form = useForm<InvoiceFormData>({
    resolver: zodResolver(invoiceFormSchema),
    defaultValues: {
      customer_name: "",
      profile_name: "",
      date: new Date().toISOString().split("T")[0],
      total_amount: 0,
      is_gross_amount: false,
      include_tax: false,
      tax_rate: undefined,
      description: "",
    },
  });

  // Watch include_tax für conditional Steuersatz-Feld
  const includeTax = useWatch({
    control: form.control,
    name: "include_tax",
  });

  const onSubmit = (data: InvoiceFormData) => {
    // TODO: Später mit Backend Search-Endpoints IDs finden
    // Aktuell: User muss exakte Namen eingeben, die im Backend existieren
    console.log("📄 Invoice Form Submitted:", data);
    console.table(data);
    console.warn(
      "⚠️  Hinweis: customer_name und profile_name müssen mit Backend übereinstimmen. Später: Autocomplete mit ID-Lookup"
    );
    // TODO: API-Call POST /invoices mit customer_id und profile_id
    // Benötigt: Backend Search-Endpoints oder Frontend-seitige ID-Resolution
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>Neue Rechnung erstellen</CardTitle>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Kundenname */}
            <FormField
              control={form.control}
              name="customer_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Kundenname <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input placeholder="z.B. Max Mustermann GmbH" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Profilname */}
            <FormField
              control={form.control}
              name="profile_name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Profilname <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input placeholder="z.B. Hauptprofil" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Datum */}
            <FormField
              control={form.control}
              name="date"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Datum <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input type="date" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Betrag */}
            <FormField
              control={form.control}
              name="total_amount"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Betrag (€) <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      {...field}
                      onChange={(e) => field.onChange(parseFloat(e.target.value) || 0)}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Brutto/Netto */}
            <FormField
              control={form.control}
              name="is_gross_amount"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center space-x-3 space-y-0">
                  <FormControl>
                    <input
                      type="checkbox"
                      checked={field.value}
                      onChange={field.onChange}
                      className="h-4 w-4"
                    />
                  </FormControl>
                  <FormLabel className="font-normal">Bruttobetrag (sonst Netto)</FormLabel>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Versteuert */}
            <FormField
              control={form.control}
              name="include_tax"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center space-x-3 space-y-0">
                  <FormControl>
                    <input
                      type="checkbox"
                      checked={field.value}
                      onChange={field.onChange}
                      className="h-4 w-4"
                    />
                  </FormControl>
                  <FormLabel className="font-normal">Rechnung versteuern</FormLabel>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Steuersatz (nur wenn versteuert) */}
            {includeTax && (
              <FormField
                control={form.control}
                name="tax_rate"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Steuersatz <span className="text-destructive">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        step="0.01"
                        min="0"
                        max="1"
                        placeholder="0.19"
                        {...field}
                        onChange={(e) => field.onChange(parseFloat(e.target.value) || undefined)}
                        value={field.value ?? ""}
                      />
                    </FormControl>
                    <FormDescription>Als Dezimalzahl (z.B. 0.19 für 19%)</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            {/* Beschreibung */}
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Beschreibung <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Rechnungsdetails eingeben..."
                      className="min-h-[100px] resize-none"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Submit Button */}
            <Button type="submit" className="w-full">
              Rechnung erstellen (Demo)
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
