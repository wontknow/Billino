/**
 * ApiClient kapselt die gemeinsame Basis-URL und HTTP-GET Logik.
 * SRP: Nur Transport / Fetch. Keine Domain-Logik.
 * Open/Closed: Erweiterbar um weitere Methoden (POST etc.) ohne bestehende zu ändern.
 */

import { logger } from "@/lib/logger";

const log = logger.createScoped("🌐 HTTP");

interface ApiErrorDetail {
  detail?:
    | string
    | Array<{
        loc: (string | number)[];
        msg: string;
        type: string;
      }>;
}

export class ApiClient {
  static baseUrl(): string {
    return process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || "http://localhost:8000";
  }

  static async get<T>(path: string, init?: RequestInit): Promise<T> {
    log.debug(`GET ${path}`);
    const res = await fetch(`${this.baseUrl()}${path}`, { cache: "no-store", ...init });
    if (!res.ok) {
      const errorDetail = await this.parseErrorResponse(res);
      log.error(`GET ${path} [${res.status}]`, errorDetail);
      const error = new Error(JSON.stringify(errorDetail));
      throw error;
    }
    log.debug(`GET ${path} [${res.status}] ✅`);
    return res.json() as Promise<T>;
  }

  static async post<T>(path: string, body: unknown, init?: RequestInit): Promise<T> {
    log.debug(`POST ${path}`, { bodySize: JSON.stringify(body).length });
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
      const errorDetail = await this.parseErrorResponse(res);
      log.error(`POST ${path} [${res.status}]`, errorDetail);
      const error = new Error(JSON.stringify(errorDetail));
      throw error;
    }
    log.debug(`POST ${path} [${res.status}] ✅`);
    return res.json() as Promise<T>;
  }

  /**
   * Parse error response and extract validation details
   */
  private static async parseErrorResponse(res: Response): Promise<ApiErrorDetail> {
    try {
      const data = (await res.json()) as ApiErrorDetail;
      return data;
    } catch {
      return {
        detail: `${res.status} ${res.statusText}`,
      };
    }
  }
}
