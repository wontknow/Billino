import { ApiClient } from "./base";

// Mock fetch globally
global.fetch = jest.fn();

describe("ApiClient", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("baseUrl", () => {
    it("gibt Default-URL zurück wenn keine Env-Variable gesetzt", () => {
      const url = ApiClient.baseUrl();
      expect(url).toBe("http://localhost:8000");
    });

    it("nutzt NEXT_PUBLIC_API_URL wenn gesetzt", () => {
      process.env.NEXT_PUBLIC_API_URL = "https://api.example.com";
      const url = ApiClient.baseUrl();
      expect(url).toBe("https://api.example.com");
      delete process.env.NEXT_PUBLIC_API_URL;
    });
  });

  describe("get", () => {
    it("führt erfolgreichen GET-Request durch und gibt JSON zurück", async () => {
      const mockData = { id: 1, name: "Test" };
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await ApiClient.get<typeof mockData>("/test");

      expect(global.fetch).toHaveBeenCalledWith("http://localhost:8000/test", {
        cache: "no-store",
      });
      expect(result).toEqual(mockData);
    });

    it("wirft Fehler bei nicht-ok Response", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: async () => ({ detail: "404 Not Found" }),
      });

      await expect(ApiClient.get("/missing")).rejects.toThrow('{"detail":"404 Not Found"}');
    });

    it("übergibt zusätzliche RequestInit-Optionen", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      });

      await ApiClient.get("/test", { headers: { Authorization: "Bearer token" } });

      expect(global.fetch).toHaveBeenCalledWith(
        "http://localhost:8000/test",
        expect.objectContaining({
          cache: "no-store",
          headers: { Authorization: "Bearer token" },
        })
      );
    });
  });
});
