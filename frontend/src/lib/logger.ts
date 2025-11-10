/**
 * Logger-Modul für strukturiertes Frontend-Logging
 * - DEV: Detaillierte Debug-Logs
 * - PROD: Nur Warnings und Errors
 *
 * Nutzung:
 *   import { logger } from "@/lib/logger";
 *   logger.debug("🔍 Debug info", { data });
 *   logger.info("✅ Success");
 *   logger.warn("⚠️ Warning");
 *   logger.error("❌ Error");
 */

type LogLevel = "DEBUG" | "INFO" | "WARN" | "ERROR";

class Logger {
  private isDev: boolean;
  private prefix: string;

  constructor() {
    // Check if we're in development
    this.isDev = process.env.NODE_ENV === "development";
    this.prefix = "🔧";
  }

  /**
   * Set a custom prefix for logs (e.g., "HTTP", "FORM", "INVOICE")
   */
  setPrefix(prefix: string): void {
    this.prefix = prefix;
  }

  /**
   * Format log output
   */
  private format(level: LogLevel, message: string, data?: unknown): string {
    const timestamp = new Date().toISOString().split("T")[1].slice(0, 8); // HH:MM:SS
    const levelColor = this.getLevelColor(level);
    const formatted = `[${timestamp}] ${levelColor} [${this.prefix}] ${message}`;
    return data ? `${formatted} ${JSON.stringify(data)}` : formatted;
  }

  /**
   * Get emoji representation for log level
   */
  private getLevelColor(level: LogLevel): string {
    const colors: Record<LogLevel, string> = {
      DEBUG: "🔍",
      INFO: "ℹ️",
      WARN: "⚠️",
      ERROR: "❌",
    };
    return colors[level];
  }

  /**
   * Debug log - only in development
   */
  debug(message: string, data?: unknown): void {
    if (!this.isDev) return;
    console.log(this.format("DEBUG", message, data));
  }

  /**
   * Info log - shown in dev and prod
   */
  info(message: string, data?: unknown): void {
    console.log(this.format("INFO", message, data));
  }

  /**
   * Warning log
   */
  warn(message: string, data?: unknown): void {
    console.warn(this.format("WARN", message, data));
  }

  /**
   * Error log
   */
  error(message: string, data?: unknown): void {
    console.error(this.format("ERROR", message, data));
  }

  /**
   * Create a scoped logger with a specific prefix
   */
  createScoped(prefix: string): ScopedLogger {
    return new ScopedLogger(prefix, this.isDev);
  }
}

/**
 * Scoped logger for specific modules/features
 */
class ScopedLogger {
  constructor(
    private prefix: string,
    private isDev: boolean
  ) {}

  private format(level: LogLevel, message: string, data?: unknown): string {
    const timestamp = new Date().toISOString().split("T")[1].slice(0, 8);
    const levelColor = this.getLevelColor(level);
    const formatted = `[${timestamp}] ${levelColor} [${this.prefix}] ${message}`;
    return data ? `${formatted} ${JSON.stringify(data)}` : formatted;
  }

  private getLevelColor(level: LogLevel): string {
    const colors: Record<LogLevel, string> = {
      DEBUG: "🔍",
      INFO: "ℹ️",
      WARN: "⚠️",
      ERROR: "❌",
    };
    return colors[level];
  }

  debug(message: string, data?: unknown): void {
    if (!this.isDev) return;
    console.log(this.format("DEBUG", message, data));
  }

  info(message: string, data?: unknown): void {
    console.log(this.format("INFO", message, data));
  }

  warn(message: string, data?: unknown): void {
    console.warn(this.format("WARN", message, data));
  }

  error(message: string, data?: unknown): void {
    console.error(this.format("ERROR", message, data));
  }
}

// Export global logger instance
export const logger = new Logger();

// Export for scoped usage
export { ScopedLogger };
