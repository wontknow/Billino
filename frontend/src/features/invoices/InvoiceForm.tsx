"use client";

import React, { useEffect, useState } from "react";
import { useForm, useWatch, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { invoiceFormSchema, type InvoiceFormData } from "@/types/invoice-form";
import { InvoicesService } from "@/services/invoices";
import { ProfilesService } from "@/services/profiles";
import { CustomersService } from "@/services/customers";
import type { Profile } from "@/types/profile";
import type { Customer } from "@/types/customer";
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
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, Trash2, Loader2 } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function InvoiceForm() {
  const [previewNumber, setPreviewNumber] = useState<string>("");
  const [isLoadingPreview, setIsLoadingPreview] = useState(true);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [isLoadingProfiles, setIsLoadingProfiles] = useState(true);
  const [customerSearchResults, setCustomerSearchResults] = useState<Customer[]>([]);
  const [isSearchingCustomers, setIsSearchingCustomers] = useState(false);
  const [customerSearchInput, setCustomerSearchInput] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fetch invoice number preview on mount
  useEffect(() => {
    const fetchPreview = async () => {
      try {
        const { preview_number } = await InvoicesService.getNumberPreview();
        setPreviewNumber(preview_number);
      } catch (error) {
        console.error("Fehler beim Laden der Rechnungsnummer-Vorschau:", error);
        setPreviewNumber("Fehler beim Laden");
      } finally {
        setIsLoadingPreview(false);
      }
    };
    fetchPreview();
  }, []);

  // Fetch profiles for dropdown
  useEffect(() => {
    const fetchProfiles = async () => {
      try {
        const profilesList = await ProfilesService.list();
        setProfiles(profilesList);
      } catch (error) {
        console.error("Fehler beim Laden der Profile:", error);
      } finally {
        setIsLoadingProfiles(false);
      }
    };
    fetchProfiles();
  }, []);

  // Debounced customer search
  useEffect(() => {
    // Clear results if input is too short
    if (customerSearchInput.length < 2) {
      setCustomerSearchResults([]);
      return;
    }

    // Set up debounced search
    const timer = setTimeout(async () => {
      try {
        setIsSearchingCustomers(true);
        console.log("🔍 Searching customers:", customerSearchInput);
        const results = await CustomersService.search(customerSearchInput);
        setCustomerSearchResults(results);
        console.log("✅ Search results:", results.length, "items");
      } catch (error) {
        console.error("❌ Search error:", error);
      } finally {
        setIsSearchingCustomers(false);
      }
    }, 300); // 300ms debounce

    // Cleanup function - called when component unmounts or before next effect runs
    return () => clearTimeout(timer);
  }, [customerSearchInput]);

  const form = useForm<InvoiceFormData>({
    resolver: zodResolver(invoiceFormSchema),
    defaultValues: {
      customer_id: null,
      profile_id: undefined,
      date: new Date().toISOString().split("T")[0],
      is_gross_amount: false,
      include_tax: false,
      tax_rate: undefined,
      invoice_items: [
        {
          description: "",
          quantity: 0,
          price: 0,
        },
      ],
    },
  });

  // useFieldArray for dynamic invoice items
  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "invoice_items",
  });

  // Watch include_tax für conditional Steuersatz-Feld
  const includeTax = useWatch({
    control: form.control,
    name: "include_tax",
  });

  // Watch all invoice items to calculate total
  const invoiceItems = useWatch({
    control: form.control,
    name: "invoice_items",
  });

  // Calculate total amount from all items
  const calculatedTotal = (invoiceItems || []).reduce((sum, item) => {
    const quantity = item?.quantity || 0;
    const price = item?.price || 0;
    return sum + quantity * price;
  }, 0);

  const onSubmit = async (data: InvoiceFormData) => {
    setIsSubmitting(true);

    try {
      console.log("📄 Starting invoice creation flow...");
      console.log("Form data:", {
        profile_id: data.profile_id,
        customer_id: data.customer_id,
        items: data.invoice_items.length,
      });

      // Step 1: Resolve customer_id
      let customer_id: number;

      if (data.customer_id !== null && data.customer_id !== undefined) {
        // Customer already selected via Combobox
        customer_id = data.customer_id;
        console.log("✅ Customer already selected:", customer_id);
      } else {
        // Customer not selected → auto-create with name from search input
        const customerName = customerSearchInput.trim();
        if (!customerName) {
          alert("Fehler: Bitte geben Sie einen Kundennamen ein oder wählen Sie einen Kunden aus");
          setIsSubmitting(false);
          return;
        }
        console.log("⚠️ Customer not selected, creating new with name:", customerName);
        const newCustomer = await CustomersService.create({
          name: customerName,
          address: null,
          city: null,
        });
        customer_id = newCustomer.id as number;
        console.log("✅ Customer created:", newCustomer);
      }

      // Step 2: Build invoice payload (profile_id is already required by schema)
      const payload = {
        date: data.date,
        customer_id,
        profile_id: data.profile_id,
        total_amount: calculatedTotal,
        invoice_items: data.invoice_items.map((item) => ({
          description: item.description,
          quantity: item.quantity,
          price: item.price,
        })),
        include_tax: data.include_tax,
        tax_rate: data.tax_rate,
        is_gross_amount: data.is_gross_amount,
      };

      console.log("📤 Sending invoice payload:", payload);

      // Step 3: Create invoice
      const createdInvoice = await InvoicesService.create(payload);
      console.log("✅ Invoice created successfully:", createdInvoice);

      // Step 4: Fetch and verify created invoice
      const fetchedInvoice = await InvoicesService.getById(createdInvoice.id as number);
      console.log("📥 Fetched created invoice:", fetchedInvoice);

      // Success!
      alert(`✅ Rechnung erfolgreich erstellt!\nRechnungsnummer: ${fetchedInvoice.number}`);

      // Reset form
      form.reset({
        customer_id: null,
        profile_id: undefined,
        date: new Date().toISOString().split("T")[0],
        is_gross_amount: false,
        include_tax: false,
        tax_rate: undefined,
        invoice_items: [{ description: "", quantity: 0, price: 0 }],
      });

      // Reset customer search input
      setCustomerSearchInput("");
      setCustomerSearchResults([]);

      // Refresh preview number
      const { preview_number } = await InvoicesService.getNumberPreview();
      setPreviewNumber(preview_number);
    } catch (error) {
      console.error("❌ Error creating invoice:", error);
      const errorMessage = error instanceof Error ? error.message : "Unbekannter Fehler";
      alert(`Fehler beim Erstellen der Rechnung:\n${errorMessage}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="w-full max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle>Neue Rechnung erstellen</CardTitle>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Invoice Number Preview (Read-only) */}
            <FormItem>
              <FormLabel>Rechnungsnummer (Vorschau)</FormLabel>
              <FormControl>
                <Input
                  value={isLoadingPreview ? "Lädt..." : previewNumber}
                  disabled
                  readOnly
                  className="bg-muted"
                />
              </FormControl>
              <FormDescription>
                Diese Nummer wird automatisch beim Erstellen vergeben
              </FormDescription>
            </FormItem>

            {/* Kundenname - Combobox mit Search */}
            <FormField
              control={form.control}
              name="customer_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Kunde <span className="text-destructive">*</span>
                  </FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Kundennamen eingeben..."
                      value={customerSearchInput}
                      role="combobox"
                      aria-expanded={customerSearchResults.length > 0}
                      aria-controls="customer-search-listbox"
                      aria-activedescendant={
                        highlightedIndex >= 0
                          ? `customer-option-${customerSearchResults[highlightedIndex]?.id}`
                          : undefined
                      }
                      aria-autocomplete="list"
                      onChange={(e) => {
                        const value = e.target.value;
                        setCustomerSearchInput(value);
                        setHighlightedIndex(-1); // Reset highlight on new input

                        if (value.length < 2) {
                          setCustomerSearchResults([]);
                          field.onChange(null); // Reset selection
                        }
                      }}
                      onKeyDown={(e) => {
                        if (customerSearchResults.length === 0) return;

                        switch (e.key) {
                          case "ArrowDown":
                            e.preventDefault();
                            setHighlightedIndex((prev) =>
                              prev < customerSearchResults.length - 1 ? prev + 1 : 0
                            );
                            break;
                          case "ArrowUp":
                            e.preventDefault();
                            setHighlightedIndex((prev) =>
                              prev > 0 ? prev - 1 : customerSearchResults.length - 1
                            );
                            break;
                          case "Enter":
                            e.preventDefault();
                            if (
                              highlightedIndex >= 0 &&
                              highlightedIndex < customerSearchResults.length
                            ) {
                              const selectedCustomer = customerSearchResults[highlightedIndex];
                              field.onChange(selectedCustomer.id);
                              setCustomerSearchInput(selectedCustomer.name);
                              setCustomerSearchResults([]);
                              setHighlightedIndex(-1);
                            } else if (
                              highlightedIndex === -1 &&
                              customerSearchResults.length > 0
                            ) {
                              // Auto-select the first result if nothing is highlighted
                              const selectedCustomer = customerSearchResults[0];
                              field.onChange(selectedCustomer.id);
                              setCustomerSearchInput(selectedCustomer.name);
                              setCustomerSearchResults([]);
                              setHighlightedIndex(-1);
                            }
                            break;
                          case "Escape":
                            e.preventDefault();
                            setCustomerSearchResults([]);
                            setHighlightedIndex(-1);
                            break;
                        }
                      }}
                    />
                  </FormControl>

                  {/* Search Results Dropdown */}
                  {customerSearchResults.length > 0 && (
                    <div
                      id="customer-search-listbox"
                      role="listbox"
                      aria-label="Kunden Suchergebnisse"
                      className="border rounded-md p-2 mt-2 space-y-1 bg-background"
                    >
                      {customerSearchResults.map((customer, index) => (
                        <button
                          key={customer.id}
                          id={`customer-option-${customer.id}`}
                          type="button"
                          role="option"
                          aria-selected={highlightedIndex === index}
                          className={`w-full text-left px-2 py-1 rounded ${
                            highlightedIndex === index ? "bg-accent" : "hover:bg-accent"
                          }`}
                          onClick={() => {
                            field.onChange(customer.id);
                            setCustomerSearchInput(customer.name);
                            setCustomerSearchResults([]);
                            setHighlightedIndex(-1);
                          }}
                          onMouseEnter={() => setHighlightedIndex(index)}
                        >
                          {customer.name}
                        </button>
                      ))}
                    </div>
                  )}

                  {customerSearchInput && field.value === null && (
                    <FormDescription className="text-blue-600">
                      Neuer Kunde wird automatisch erstellt
                    </FormDescription>
                  )}
                  {isSearchingCustomers && (
                    <FormDescription className="text-amber-600">Suche lädt...</FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Profil - Select */}
            <FormField
              control={form.control}
              name="profile_id"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    Profil <span className="text-destructive">*</span>
                  </FormLabel>
                  <Select
                    onValueChange={(value) => field.onChange(parseInt(value, 10))}
                    value={field.value ? String(field.value) : ""}
                    disabled={isLoadingProfiles}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue
                          placeholder={isLoadingProfiles ? "Lädt Profile..." : "Profil auswählen"}
                        />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {profiles.map((profile) => (
                        <SelectItem key={profile.id} value={String(profile.id)}>
                          {profile.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
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

            {/* Invoice Items Section */}
            <div className="border rounded-lg p-4 space-y-4">
              <div className="flex justify-between items-center mb-2">
                <h3 className="font-semibold text-lg">Rechnungspositionen</h3>
                <span className="text-sm text-muted-foreground">
                  {fields.length} von max. 10 Positionen
                </span>
              </div>

              {fields.map((field, index) => (
                <div key={field.id} className="border rounded-md p-3 space-y-3 bg-muted/30">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium">Position {index + 1}</span>
                    {fields.length > 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => remove(index)}
                        className="h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>

                  {/* Item Description */}
                  <FormField
                    control={form.control}
                    name={`invoice_items.${index}.description`}
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>
                          Beschreibung <span className="text-destructive">*</span>
                        </FormLabel>
                        <FormControl>
                          <Input placeholder="z.B. Beratungsleistung" {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="grid grid-cols-2 gap-3">
                    {/* Item Quantity */}
                    <FormField
                      control={form.control}
                      name={`invoice_items.${index}.quantity`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>
                            Menge <span className="text-destructive">*</span>
                          </FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              step="1"
                              min="1"
                              placeholder="1"
                              {...field}
                              onChange={(e) => {
                                const value = e.target.value === "" ? 0 : parseInt(e.target.value);
                                field.onChange(isNaN(value) ? 0 : value);
                              }}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    {/* Item Price */}
                    <FormField
                      control={form.control}
                      name={`invoice_items.${index}.price`}
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>
                            Preis (€) <span className="text-destructive">*</span>
                          </FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              step="0.01"
                              placeholder="0.00"
                              {...field}
                              onChange={(e) => {
                                const value =
                                  e.target.value === "" ? 0 : parseFloat(e.target.value);
                                field.onChange(isNaN(value) ? 0 : value);
                              }}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  {/* Item Subtotal */}
                  <div className="pt-2 border-t text-sm">
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Zwischensumme:</span>
                      <span className="font-semibold">
                        {(
                          (invoiceItems?.[index]?.quantity || 0) *
                          (invoiceItems?.[index]?.price || 0)
                        ).toFixed(2)}{" "}
                        €
                      </span>
                    </div>
                  </div>
                </div>
              ))}

              {/* Add Item Button */}
              {fields.length < 10 && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => append({ description: "", quantity: 0, price: 0 })}
                  className="w-full"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Position hinzufügen
                </Button>
              )}

              {/* Total Amount Display */}
              <div className="pt-3 border-t-2">
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-lg">Gesamtsumme:</span>
                  <span className="text-xl font-bold">{calculatedTotal.toFixed(2)} €</span>
                </div>
              </div>
            </div>

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
                        onChange={(e) => {
                          const val = parseFloat(e.target.value);
                          field.onChange(isNaN(val) ? undefined : val);
                        }}
                        value={field.value ?? ""}
                      />
                    </FormControl>
                    <FormDescription>Als Dezimalzahl (z.B. 0.19 für 19%)</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}

            {/* Submit Button */}
            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Rechnung wird erstellt...
                </>
              ) : (
                "Rechnung erstellen"
              )}
            </Button>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}
