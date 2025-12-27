"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { Customer } from "@/types/customer";
import { CustomersService } from "@/services/customers";

type Props = {
  isOpen: boolean;
  customer?: Customer | null;
  onClose: () => void;
  onSuccess: (customer: Customer) => void;
};

export function CustomerDialog({ isOpen, customer, onClose, onSuccess }: Props) {
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isEditMode = !!customer;

  // Initialize form when customer changes
  useEffect(() => {
    if (customer) {
      setName(customer.name);
      setAddress(customer.address ?? "");
      setCity(customer.city ?? "");
    } else {
      setName("");
      setAddress("");
      setCity("");
    }
  }, [customer]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        name: name.trim(),
        address: address.trim() || null,
        city: city.trim() || null,
      };

      let result: Customer;

      if (isEditMode && customer) {
        // Update existing customer using service
        result = await CustomersService.update(customer.id, payload);
      } else {
        // Create new customer using service
        result = await CustomersService.create(payload);
      }

      onSuccess(result);
      handleClose();
    } catch (error) {
      console.error("Error saving customer:", error);
      alert(
        `Fehler beim Speichern: ${error instanceof Error ? error.message : "Unbekannter Fehler"}`
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setName("");
    setAddress("");
    setCity("");
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{isEditMode ? "Kunde bearbeiten" : "Neuer Kunde"}</DialogTitle>
          <DialogDescription>
            {isEditMode
              ? "Bearbeiten Sie die Kundendaten."
              : "Erstellen Sie einen neuen Kunden mit Name, Adresse und Stadt."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">
                Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="z.B. Max Mustermann"
                required
                disabled={isSubmitting}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="address">Adresse</Label>
              <Input
                id="address"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="z.B. Musterstraße 123"
                disabled={isSubmitting}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="city">Stadt</Label>
              <Input
                id="city"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="z.B. 12345 Berlin"
                disabled={isSubmitting}
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button type="button" variant="ghost" onClick={handleClose} disabled={isSubmitting}>
              Abbrechen
            </Button>
            <Button type="submit" disabled={isSubmitting || !name.trim()}>
              {isSubmitting ? "Speichern..." : isEditMode ? "Speichern" : "Erstellen"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
