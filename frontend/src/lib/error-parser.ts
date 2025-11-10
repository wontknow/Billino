/**
 * Error-Parser für Backend API-Fehler
 * Strukturiert Validierungsfehler vom Backend für bessere UI-Anzeige
 */

export interface ValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ApiErrorResponse {
  detail?: string | ValidationError[];
}

export interface ParsedError {
  title: string;
  message: string;
  fieldErrors: Record<string, string>;
  isValidationError: boolean;
}

/**
 * Parse API error responses into structured format
 */
export function parseApiError(error: unknown): ParsedError {
  // Default error
  const defaultError: ParsedError = {
    title: "Fehler",
    message: "Ein unbekannter Fehler ist aufgetreten",
    fieldErrors: {},
    isValidationError: false,
  };

  // Handle Error objects
  if (error instanceof Error) {
    try {
      // Try to parse as JSON (if error.message contains JSON)
      const jsonMatch = error.message.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0]) as ApiErrorResponse;
        return parseApiErrorResponse(parsed);
      }
    } catch {
      // Not JSON, return as-is
    }
    return {
      title: "Fehler",
      message: error.message,
      fieldErrors: {},
      isValidationError: false,
    };
  }

  // Handle responses with detail field
  if (typeof error === "object" && error !== null) {
    const response = error as ApiErrorResponse;
    if (response.detail) {
      return parseApiErrorResponse(response);
    }
  }

  // Handle string errors
  if (typeof error === "string") {
    return {
      title: "Fehler",
      message: error,
      fieldErrors: {},
      isValidationError: false,
    };
  }

  return defaultError;
}

/**
 * Parse API error response with detail field
 */
function parseApiErrorResponse(response: ApiErrorResponse): ParsedError {
  // If detail is a string
  if (typeof response.detail === "string") {
    return {
      title: "Fehler",
      message: response.detail,
      fieldErrors: {},
      isValidationError: false,
    };
  }

  // If detail is an array of validation errors
  if (Array.isArray(response.detail)) {
    const fieldErrors: Record<string, string> = {};
    let mainMessage = "";

    response.detail.forEach((error: ValidationError) => {
      // Extract field name from loc (e.g., ["body", "total_amount"] -> "total_amount")
      const fieldPath = error.loc.slice(1).join(".");
      if (fieldPath) {
        fieldErrors[fieldPath] = error.msg;
      }
      if (!mainMessage) {
        mainMessage = error.msg;
      }
    });

    return {
      title: "Validierungsfehler",
      message: mainMessage || "Bitte überprüfen Sie Ihre Eingaben und versuchen Sie es erneut",
      fieldErrors,
      isValidationError: true,
    };
  }

  return {
    title: "Fehler",
    message: "Ein unbekannter Fehler ist aufgetreten",
    fieldErrors: {},
    isValidationError: false,
  };
}
