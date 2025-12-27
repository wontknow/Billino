"use client";

import React from "react";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle, CardAction } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { Profile } from "@/types/profile";

interface ProfilesTableProps {
  profiles: Profile[];
  emptyMessage?: React.ReactNode;
  onProfileSelect?: (profile: Profile) => void;
  onCreateProfile?: () => void;
}

export const ProfilesTable: React.FC<ProfilesTableProps> = ({
  profiles,
  emptyMessage,
  onProfileSelect,
  onCreateProfile,
}) => {
  const hasData = profiles.length > 0;
  const isInteractive = !!onProfileSelect;

  return (
    <Card className="w-full mx-auto flex flex-col overflow-hidden max-w-screen-lg md:max-w-screen-xl 2xl:max-w-screen-2xl h-[70vh] md:h-[75vh] lg:h-[80vh]">
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Profile</CardTitle>
        {onCreateProfile && (
          <CardAction className="flex gap-2">
            <Button onClick={onCreateProfile}>Neues Profil</Button>
          </CardAction>
        )}
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden">
        <div className="h-full overflow-auto">
          <Table>
            <TableCaption>
              {hasData
                ? `${profiles.length} Profil(e)`
                : (emptyMessage ?? "Keine Profile gefunden")}
            </TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky top-0 z-10 bg-background">Name</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background">Stadt</TableHead>
                <TableHead className="sticky top-0 z-10 bg-background">Steuerstatus</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {profiles.map((p) => (
                <TableRow
                  key={p.id}
                  className={isInteractive ? "cursor-pointer hover:bg-muted/50" : ""}
                  onClick={() => isInteractive && onProfileSelect?.(p)}
                  tabIndex={isInteractive ? 0 : -1}
                  onKeyDown={(event) => {
                    if (!isInteractive) {
                      return;
                    }
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onProfileSelect?.(p);
                    }
                  }}
                >
                  <TableCell className="font-medium">{p.name}</TableCell>
                  <TableCell>{p.city || "—"}</TableCell>
                  <TableCell>{renderTaxStatus(p)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
};

function renderTaxStatus(p: Profile) {
  if (p.include_tax) {
    return `USt ${Math.round(p.default_tax_rate * 100)}%`;
  }
  return "§19 UStG (keine USt)";
}
