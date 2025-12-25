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

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public detail: ApiErrorDetail,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export class ApiClient {
  static baseUrl(): string {
    return process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || "http://localhost:8000";
  }

  static async get<T>(path: string, init?: RequestInit): Promise<T> {
    const url = `${this.baseUrl()}${path}`;
    log.debug(`📤 REQUEST: GET ${path}`);

    try {
      const res = await fetch(url, { cache: "no-store", ...init });

      if (!res.ok) {
        const errorDetail = await this.parseErrorResponse(res);
        log.error(`📥 RESPONSE: GET ${path} [${res.status}]`, {
          status: res.status,
          statusText: res.statusText,
          detail: errorDetail,
        });
        throw new ApiError(res.status, res.statusText, errorDetail, JSON.stringify(errorDetail));
      }

      log.debug(`📥 RESPONSE: GET ${path} [${res.status}] ✅`);
      const data = (await res.json()) as Promise<T>;
      return data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      log.error(`📥 RESPONSE: GET ${path} [NETWORK ERROR]`, { error });
      throw error;
    }
  }

  static async post<T>(path: string, body: unknown, init?: RequestInit): Promise<T> {
    const url = `${this.baseUrl()}${path}`;
    const bodySize = JSON.stringify(body).length;
    log.debug(`📤 REQUEST: POST ${path}`, { bodySize: `${bodySize} bytes` });

    try {
      const res = await fetch(url, {
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
        log.error(`📥 RESPONSE: POST ${path} [${res.status}]`, {
          status: res.status,
          statusText: res.statusText,
          detail: errorDetail,
        });
        throw new ApiError(res.status, res.statusText, errorDetail, JSON.stringify(errorDetail));
      }

      log.debug(`📥 RESPONSE: POST ${path} [${res.status}] ✅`);
      const data = (await res.json()) as Promise<T>;
      return data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      log.error(`📥 RESPONSE: POST ${path} [NETWORK ERROR]`, { error });
      throw error;
    }
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
