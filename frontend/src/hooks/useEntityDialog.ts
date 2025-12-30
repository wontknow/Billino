import { useState } from "react";
import { logger } from "@/lib/logger";

type IdOf<T> = T extends { id?: infer I } ? NonNullable<I> : never;

type EntityDialogConfig<T, TPayload = Partial<T>> = {
  logScope: string;
  createFn: (payload: TPayload) => Promise<T>;
  updateFn: (id: IdOf<T>, payload: TPayload) => Promise<T>;
  onSuccess: (entity: T) => void | Promise<void>;
  onClose: () => void;
};

/**
 * Custom hook for managing entity dialog state and submission logic.
 * Reduces code duplication between CustomerDialog and ProfileDialog.
 *
 * @template T - Entity type that extends { id?: number | string }
 * @param config - Configuration object for the entity dialog
 * @param config.logScope - Logging prefix for scoped logger (e.g., "👤 CustomerDialog")
 * @param config.createFn - Function to create a new entity
 * @param config.updateFn - Function to update an existing entity
 * @param config.onSuccess - Callback invoked with the created/updated entity on success
 * @param config.onClose - Callback invoked after successful submission
 * @returns Object containing isSubmitting state and handleSubmit function
 * @returns.isSubmitting - Boolean indicating if a submission is in progress
 * @returns.handleSubmit - Async function to handle form submission
 */
export function useEntityDialog<T extends { id?: number | string }, TPayload = Partial<T>>(
  config: EntityDialogConfig<T, TPayload>
) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const log = logger.createScoped(config.logScope);

  const formatErrorMessage = (error: unknown): string => {
    return error instanceof Error ? error.message : "Unbekannter Fehler";
  };

  const handleSubmit = async (
    entity: T | null | undefined,
    payload: TPayload
  ): Promise<boolean> => {
    setIsSubmitting(true);

    try {
      let result: T;

      if (entity?.id) {
        // Update existing entity
        result = await config.updateFn(entity.id as IdOf<T>, payload);
      } else {
        // Create new entity
        result = await config.createFn(payload);
      }

      await config.onSuccess(result);
      config.onClose();
      return true;
    } catch (error) {
      log.error("Failed to save entity", { error });
      alert(`Fehler beim Speichern: ${formatErrorMessage(error)}`);
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
