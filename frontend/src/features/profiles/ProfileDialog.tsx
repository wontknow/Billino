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
import { Checkbox } from "@/components/ui/checkbox";
import type { Profile } from "@/types/profile";
import { ProfilesService } from "@/services/profiles";
import { logger } from "@/lib/logger";

const log = logger.createScoped("📋 ProfileDialog");

type Props = {
  isOpen: boolean;
  profile?: Profile | null;
  onClose: () => void;
  onSuccess: (profile: Profile) => void;
};

export function ProfileDialog({ isOpen, profile, onClose, onSuccess }: Props) {
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [city, setCity] = useState("");
  const [bankData, setBankData] = useState("");
  const [taxNumber, setTaxNumber] = useState("");
  const [includeTax, setIncludeTax] = useState(true);
  const [defaultTaxRate, setDefaultTaxRate] = useState("19");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isEditMode = !!profile;

  // Initialize form when profile changes
  useEffect(() => {
    if (profile) {
      setName(profile.name);
      setAddress(profile.address ?? "");
      setCity(profile.city ?? "");
      setBankData(profile.bank_data ?? "");
      setTaxNumber(profile.tax_number ?? "");
      setIncludeTax(profile.include_tax);
      setDefaultTaxRate(String(Math.round(profile.default_tax_rate * 100)));
    } else {
      setName("");
      setAddress("");
      setCity("");
      setBankData("");
      setTaxNumber("");
      setIncludeTax(true);
      setDefaultTaxRate("19");
    }
  }, [profile]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = {
        name: name.trim(),
        address: address.trim() || undefined,
        city: city.trim() || undefined,
        bank_data: bankData.trim() || null,
        tax_number: taxNumber.trim() || null,
        include_tax: includeTax,
        default_tax_rate: Number(defaultTaxRate) / 100,
      };

      let result: Profile;

      if (isEditMode && profile) {
        // Update existing profile using service
        result = await ProfilesService.update(Number(profile.id), payload);
      } else {
        // Create new profile using service
        result = await ProfilesService.create(payload);
      }

      onSuccess(result);
      handleClose();
    } catch (error) {
      log.error("Failed to save profile", { error });
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
    setBankData("");
    setTaxNumber("");
    setIncludeTax(true);
    setDefaultTaxRate("19");
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && handleClose()}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{isEditMode ? "Profil bearbeiten" : "Neues Profil"}</DialogTitle>
          <DialogDescription>
            {isEditMode
              ? "Bearbeiten Sie die Profildaten."
              : "Erstellen Sie ein neues Firmenprofil mit allen erforderlichen Daten."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="name">
                Firmenname <span className="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="z.B. Tech Solutions GmbH"
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
                placeholder="z.B. Hauptstraße 123"
                disabled={isSubmitting}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="city">Stadt</Label>
              <Input
                id="city"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="z.B. 10115 Berlin"
                disabled={isSubmitting}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="bankData">Bankdaten</Label>
              <Input
                id="bankData"
                value={bankData}
                onChange={(e) => setBankData(e.target.value)}
                placeholder="z.B. DE89370400440532013000"
                disabled={isSubmitting}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="taxNumber">Steuernummer</Label>
              <Input
                id="taxNumber"
                value={taxNumber}
                onChange={(e) => setTaxNumber(e.target.value)}
                placeholder="z.B. DE123456789"
                disabled={isSubmitting}
              />
            </div>

            <div className="flex items-center space-x-3">
              <Checkbox
                id="includeTax"
                checked={includeTax}
                onCheckedChange={(checked) => setIncludeTax(checked as boolean)}
                disabled={isSubmitting}
              />
              <Label htmlFor="includeTax" className="cursor-pointer font-normal">
                Umsatzsteuer ausweisen
              </Label>
            </div>

            {includeTax && (
              <div className="grid gap-2">
                <Label htmlFor="defaultTaxRate">Standard-Steuersatz (%)</Label>
                <Input
                  id="defaultTaxRate"
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  value={defaultTaxRate}
                  onChange={(e) => setDefaultTaxRate(e.target.value)}
                  placeholder="19"
                  disabled={isSubmitting}
                />
              </div>
            )}
          </div>

          <DialogFooter className="gap-2">
            <Button type="button" variant="ghost" onClick={handleClose} disabled={isSubmitting}>
              Abbrechen
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || !name.trim()}
            >
              {isEditMode ? "Speichern" : "Erstellen"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
