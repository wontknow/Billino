/**
 * ApiClient kapselt die gemeinsame Basis-URL und HTTP-GET Logik.
 * SRP: Nur Transport / Fetch. Keine Domain-Logik.
 * Open/Closed: Erweiterbar um weitere Methoden (POST etc.) ohne bestehende zu ändern.
 */
export class ApiClient {
  static baseUrl(): string {
    return process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || "http://localhost:8000/api";
  }

  static async get<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${this.baseUrl()}${path}`, { cache: "no-store", ...init });
    if (!res.ok) {
      throw new Error(`Request fehlgeschlagen: ${res.status} ${res.statusText}`);
    }
    return res.json() as Promise<T>;
  }

  static async post<T>(path: string, body: unknown, init?: RequestInit): Promise<T> {
    const res = await fetch(`${this.baseUrl()}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
      body: JSON.stringify(body),
      ...init,
    });
    if (!res.ok) {
      throw new Error(`Request fehlgeschlagen: ${res.status} ${res.statusText}`);
    }
    return res.json() as Promise<T>;
  }
}
