import { renderHook, waitFor } from "@testing-library/react";
import { useEntityDialog } from "./useEntityDialog";
import { logger } from "@/lib/logger";

// Mock logger
jest.mock("@/lib/logger", () => ({
  logger: {
    createScoped: jest.fn(() => ({
      error: jest.fn(),
    })),
  },
}));

describe("useEntityDialog", () => {
  const mockCreateFn = jest.fn();
  const mockUpdateFn = jest.fn();
  const mockOnSuccess = jest.fn();
  const mockOnClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
    // Mock window.alert
    global.alert = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  const defaultConfig = {
    logScope: "🧪 TestDialog",
    createFn: mockCreateFn,
    updateFn: mockUpdateFn,
    onSuccess: mockOnSuccess,
    onClose: mockOnClose,
  };

  describe("handleSubmit", () => {
    it("creates a new entity when no existing entity is provided", async () => {
      const newEntity = { id: 1, name: "New Entity" };
      mockCreateFn.mockResolvedValueOnce(newEntity);

      const { result } = renderHook(() => useEntityDialog(defaultConfig));

      const payload = { name: "New Entity" };
      const success = await result.current.handleSubmit(null, payload);

      expect(mockCreateFn).toHaveBeenCalledWith(payload);
      expect(mockUpdateFn).not.toHaveBeenCalled();
      expect(mockOnSuccess).toHaveBeenCalledWith(newEntity);
      expect(mockOnClose).toHaveBeenCalled();
      expect(success).toBe(true);
    });

    it("updates an existing entity when entity with id is provided", async () => {
      const existingEntity = { id: 1, name: "Existing Entity" };
      const updatedEntity = { id: 1, name: "Updated Entity" };
      mockUpdateFn.mockResolvedValueOnce(updatedEntity);

      const { result } = renderHook(() => useEntityDialog(defaultConfig));

      const payload = { name: "Updated Entity" };
      const success = await result.current.handleSubmit(existingEntity, payload);

      expect(mockUpdateFn).toHaveBeenCalledWith(1, payload);
      expect(mockCreateFn).not.toHaveBeenCalled();
      expect(mockOnSuccess).toHaveBeenCalledWith(updatedEntity);
      expect(mockOnClose).toHaveBeenCalled();
      expect(success).toBe(true);
    });

    it("handles entity with string id correctly", async () => {
      const existingEntity = { id: "abc-123", name: "Entity" };
      const updatedEntity = { id: "abc-123", name: "Updated" };
      mockUpdateFn.mockResolvedValueOnce(updatedEntity);

      const { result } = renderHook(() => useEntityDialog(defaultConfig));

      await result.current.handleSubmit(existingEntity, { name: "Updated" });

      expect(mockUpdateFn).toHaveBeenCalledWith("abc-123", { name: "Updated" });
    });

    it("sets isSubmitting to true during submission", async () => {
      mockCreateFn.mockImplementation(
        () => new Promise((resolve) => setTimeout(() => resolve({ id: 1 }), 100))
      );

      const { result } = renderHook(() => useEntityDialog(defaultConfig));

      expect(result.current.isSubmitting).toBe(false);

      const submitPromise = result.current.handleSubmit(null, { name: "Test" });

      // Check immediately after calling handleSubmit
      await waitFor(() => {
        expect(result.current.isSubmitting).toBe(true);
      });

      await submitPromise;

      expect(result.current.isSubmitting).toBe(false);
    });

    it("handles Error instance correctly", async () => {
      const error = new Error("Network error");
      mockCreateFn.mockRejectedValueOnce(error);

      const { result } = renderHook(() => useEntityDialog(defaultConfig));

      const success = await result.current.handleSubmit(null, { name: "Test" });

      expect(global.alert).toHaveBeenCalledWith("Fehler beim Speichern: Network error");
      expect(mockOnSuccess).not.toHaveBeenCalled();
      expect(mockOnClose).not.toHaveBeenCalled();
      expect(success).toBe(false);
    });

    it("handles unknown error type with generic message", async () => {
      mockCreateFn.mockRejectedValueOnce("String error");

      const { result } = renderHook(() => useEntityDialog(defaultConfig));

      const success = await result.current.handleSubmit(null, { name: "Test" });

      expect(global.alert).toHaveBeenCalledWith("Fehler beim Speichern: Unbekannter Fehler");
      expect(success).toBe(false);
    });

    it("logs error with scoped logger", async () => {
      const error = new Error("Test error");
      mockCreateFn.mockRejectedValueOnce(error);

      const mockLog = {
        error: jest.fn(),
      };
      (logger.createScoped as jest.Mock).mockReturnValueOnce(mockLog);

      const { result } = renderHook(() => useEntityDialog(defaultConfig));

      await result.current.handleSubmit(null, { name: "Test" });

      expect(logger.createScoped).toHaveBeenCalledWith("🧪 TestDialog");
      expect(mockLog.error).toHaveBeenCalledWith("Failed to save entity", { error });
    });

    it("resets isSubmitting state even when error occurs", async () => {
      mockCreateFn.mockRejectedValueOnce(new Error("Test error"));

      const { result } = renderHook(() => useEntityDialog(defaultConfig));

      await result.current.handleSubmit(null, { name: "Test" });

      expect(result.current.isSubmitting).toBe(false);
    });

    it("does not call onSuccess or onClose when submission fails", async () => {
      mockCreateFn.mockRejectedValueOnce(new Error("Submission failed"));

      const { result } = renderHook(() => useEntityDialog(defaultConfig));

      await result.current.handleSubmit(null, { name: "Test" });

      expect(mockOnSuccess).not.toHaveBeenCalled();
      expect(mockOnClose).not.toHaveBeenCalled();
    });

    it("handles partial payloads correctly", async () => {
      const newEntity = { id: 1, name: "Entity", extra: "data" };
      mockCreateFn.mockResolvedValueOnce(newEntity);

      const { result } = renderHook(() => useEntityDialog(defaultConfig));

      const partialPayload = { name: "Entity" };
      await result.current.handleSubmit(null, partialPayload);

      expect(mockCreateFn).toHaveBeenCalledWith(partialPayload);
    });
  });

  describe("initialization", () => {
    it("initializes with isSubmitting set to false", () => {
      const { result } = renderHook(() => useEntityDialog(defaultConfig));

      expect(result.current.isSubmitting).toBe(false);
    });

    it("creates scoped logger with provided logScope", () => {
      renderHook(() => useEntityDialog(defaultConfig));

      expect(logger.createScoped).toHaveBeenCalledWith("🧪 TestDialog");
    });
  });
});
