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
import { useEntityDialog } from "@/hooks/useEntityDialog";

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

  const isEditMode = !!customer;

  const { isSubmitting, handleSubmit } = useEntityDialog<Customer>({
    logScope: "👤 CustomerDialog",
    createFn: CustomersService.create,
    updateFn: CustomersService.update,
    onSuccess,
    onClose,
  });

  // Initialize form when customer changes
  /* eslint-disable react-hooks/set-state-in-effect */
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
  /* eslint-enable react-hooks/set-state-in-effect */

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      return;
    }

    const payload = {
      name: name.trim(),
      address: address.trim() || null,
      city: city.trim() || null,
    };

    await handleSubmit(customer, payload);
  };

  function handleClose() {
    setName("");
    setAddress("");
    setCity("");
    onClose();
  }

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

        <form onSubmit={onSubmit}>
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
