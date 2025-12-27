import { useState } from "react";
import { logger } from "@/lib/logger";

type EntityDialogConfig<T> = {
  logScope: string;
  createFn: (payload: Partial<T>) => Promise<T>;
  updateFn: (id: number | string, payload: Partial<T>) => Promise<T>;
  onSuccess: (entity: T) => void;
  onClose: () => void;
};

/**
 * Custom hook for managing entity dialog state and submission logic.
 * Reduces code duplication between CustomerDialog and ProfileDialog.
 */
export function useEntityDialog<T extends { id?: number | string }>(
  config: EntityDialogConfig<T>
) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const log = logger.createScoped(config.logScope);

  const handleSubmit = async (
    entity: T | null | undefined,
    payload: Partial<T>
  ): Promise<boolean> => {
    setIsSubmitting(true);

    try {
      let result: T;

      if (entity?.id) {
        // Update existing entity
        result = await config.updateFn(entity.id, payload);
      } else {
        // Create new entity
        result = await config.createFn(payload);
      }

      config.onSuccess(result);
      config.onClose();
      return true;
    } catch (error) {
      log.error("Failed to save entity", { error });
      alert(
        `Fehler beim Speichern: ${error instanceof Error ? error.message : "Unbekannter Fehler"}`
      );
      return false;
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    isSubmitting,
    handleSubmit,
  };
}
