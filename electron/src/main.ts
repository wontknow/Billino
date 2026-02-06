/**
 * Billino Desktop – Electron Main Process
 *
 * Responsibilities:
 * 1. Spawn the bundled FastAPI backend (billino-backend.exe)
 * 2. Wait until /health returns ok
 * 3. Load the static Next.js frontend
 * 4. On quit: trigger /backups/trigger, then kill backend
 *
 * Data is stored in AppData/Roaming/Billino (Windows):
 *   %APPDATA%/Billino/billino.db
 *   %APPDATA%/Billino/backups/
 *   %APPDATA%/Billino/pdfs/
 *   %APPDATA%/Billino/logs/
 */

import { app, BrowserWindow, dialog, protocol } from "electron";
import { ChildProcess, spawn } from "child_process";
import path from "path";
import fs from "fs";
import log from "electron-log/main";

// ─── Constants ───────────────────────────────────────────────────────────────

const BACKEND_PORT = 8000;
const BACKEND_HOST = "127.0.0.1";
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
const HEALTH_URL = `${BACKEND_URL}/health`;
const BACKUP_URL = `${BACKEND_URL}/backups/trigger`;
const HEALTH_RETRIES = 60; // max attempts
const HEALTH_INTERVAL_MS = 500; // ms between attempts

// ─── Globals ─────────────────────────────────────────────────────────────────

let backendProcess: ChildProcess | null = null;
let mainWindow: BrowserWindow | null = null;
let isQuitting = false;

// ─── Logging ─────────────────────────────────────────────────────────────────

log.initialize();
log.transports.file.resolvePathFn = () =>
  path.join(app.getPath("userData"), "logs", "billino-desktop.log");

// ─── User Data Directories ──────────────────────────────────────────────────

/**
 * Ensure all required data directories exist in AppData/Roaming/Billino.
 */
function ensureUserDataDirs(): void {
  const userData = app.getPath("userData"); // %APPDATA%/Billino
  const dirs = ["backups", "pdfs", "logs"];

  for (const dir of dirs) {
    const dirPath = path.join(userData, dir);
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
      log.info(`📁 Created directory: ${dirPath}`);
    }
  }

  log.info(`📂 User data root: ${userData}`);
}

// ─── Backend Lifecycle ───────────────────────────────────────────────────────

/**
 * Resolve the path to the backend executable.
 *
 * In development: uses the Python backend directly.
 * In production: uses the PyInstaller-bundled executable from resources.
 */
function getBackendPath(): string {
  if (app.isPackaged) {
    // Production: bundled executable in resources
    const exeName =
      process.platform === "win32" ? "billino-backend.exe" : "billino-backend";
    return path.join(process.resourcesPath, "backend", exeName);
  }

  // Development: run Python directly
  return path.join(__dirname, "..", "..", "backend", "main.py");
}

/**
 * Spawn the FastAPI backend process with proper environment variables.
 *
 * Sets:
 * - APP_ENV=desktop
 * - ENV=production (packaged) or development
 * - BACKEND_HOST / BACKEND_PORT
 * - DATA_DIR → AppData/Roaming/Billino
 * - BACKUP_ENABLED=true
 */
function startBackend(): void {
  const backendPath = getBackendPath();
  const userData = app.getPath("userData");

  const env: NodeJS.ProcessEnv = {
    ...process.env,
    APP_ENV: "desktop",
    ENV: app.isPackaged ? "production" : "development",
    BACKEND_HOST,
    BACKEND_PORT: String(BACKEND_PORT),
    DATA_DIR: userData,
    BACKUP_ENABLED: "true",
  };

  log.info(`🚀 Starting backend: ${backendPath}`);
  log.info(`📂 Data directory: ${userData}`);

  if (app.isPackaged) {
    // Production: run the bundled executable
    backendProcess = spawn(backendPath, [], {
      env,
      stdio: ["ignore", "pipe", "pipe"],
      windowsHide: true,
    });
  } else {
    // Development: run via Python
    backendProcess = spawn("python", [backendPath], {
      env,
      stdio: ["ignore", "pipe", "pipe"],
      cwd: path.join(__dirname, "..", "..", "backend"),
    });
  }

  // Pipe backend output to electron-log
  backendProcess.stdout?.on("data", (data: Buffer) => {
    log.info(`[backend] ${data.toString().trim()}`);
  });

  backendProcess.stderr?.on("data", (data: Buffer) => {
    log.warn(`[backend:err] ${data.toString().trim()}`);
  });

  backendProcess.on("exit", (code, signal) => {
    log.info(`🛑 Backend exited: code=${code}, signal=${signal}`);
    backendProcess = null;

    if (!isQuitting) {
      log.error("❌ Backend crashed unexpectedly!");
      dialog.showErrorBox(
        "Billino – Fehler",
        "Das Backend ist unerwartet beendet worden.\nBitte starte die App neu."
      );
      app.quit();
    }
  });

  backendProcess.on("error", (err) => {
    log.error(`❌ Failed to start backend: ${err.message}`);
    dialog.showErrorBox(
      "Billino – Startfehler",
      `Das Backend konnte nicht gestartet werden:\n${err.message}`
    );
    app.quit();
  });
}

/**
 * Poll the /health endpoint until the backend reports ready.
 *
 * @throws Error if backend doesn't become healthy within the timeout
 */
async function waitForBackend(): Promise<void> {
  log.info("⏳ Waiting for backend to become ready...");

  for (let attempt = 1; attempt <= HEALTH_RETRIES; attempt++) {
    try {
      const response = await fetch(HEALTH_URL);
      if (response.ok) {
        const data = (await response.json()) as { ready?: boolean; status?: string };
        if (data.ready === true || data.status === "ok") {
          log.info(`✅ Backend ready after ${attempt} attempt(s)`);
          return;
        }
      }
    } catch {
      // Backend not yet reachable – expected during startup
    }

    await new Promise((resolve) => setTimeout(resolve, HEALTH_INTERVAL_MS));
  }

  throw new Error(
    `Backend did not become ready after ${HEALTH_RETRIES * HEALTH_INTERVAL_MS}ms`
  );
}

/**
 * Trigger a backup via the backend API before shutdown.
 */
async function triggerShutdownBackup(): Promise<void> {
  log.info("💾 Triggering shutdown backup...");

  try {
    const response = await fetch(BACKUP_URL, {
      method: "POST",
      signal: AbortSignal.timeout(10_000), // 10s timeout
    });

    if (response.ok) {
      log.info("✅ Shutdown backup completed successfully");
    } else {
      log.warn(`⚠️ Shutdown backup returned status ${response.status}`);
    }
  } catch (err) {
    log.warn(`⚠️ Shutdown backup failed: ${err}`);
  }
}

/**
 * Gracefully terminate the backend process.
 */
function stopBackend(): void {
  if (!backendProcess) return;

  log.info("🛑 Stopping backend process...");

  if (process.platform === "win32") {
    // On Windows, SIGTERM doesn't work reliably – use taskkill
    spawn("taskkill", ["/pid", String(backendProcess.pid), "/f", "/t"], {
      windowsHide: true,
    });
  } else {
    backendProcess.kill("SIGTERM");
  }

  backendProcess = null;
}

// ─── Custom Protocol (app://) ────────────────────────────────────────────────

/** MIME type map for common static-export file extensions. */
const MIME_TYPES: Record<string, string> = {
  ".html": "text/html",
  ".js": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".eot": "application/vnd.ms-fontobject",
  ".map": "application/json",
  ".webp": "image/webp",
  ".txt": "text/plain",
};

/**
 * Resolve the root directory of the static Next.js frontend export.
 */
function getFrontendRoot(): string {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "frontend");
  }
  return path.join(__dirname, "..", "..", "frontend", "out");
}

/**
 * Register the `app://` custom protocol to serve static Next.js files.
 *
 * This replaces `file://` which cannot handle SPA-style absolute paths
 * (e.g. `/dashboard`, `/_next/static/...`) because they resolve to the
 * filesystem root instead of the frontend export directory.
 *
 * The handler:
 * 1. Maps the URL path to a file inside the frontend export directory
 * 2. If the path has no extension → tries `<path>/index.html` (Next.js trailingSlash)
 * 3. Falls back to the root `index.html` for client-side route resolution
 * 4. Returns a proper Response with the correct MIME type
 */
function registerAppProtocol(): void {
  protocol.handle("app", (request) => {
    const frontendRoot = getFrontendRoot();

    // Parse the URL path (app://./dashboard → /dashboard)
    let urlPath: string;
    try {
      const url = new URL(request.url);
      urlPath = decodeURIComponent(url.pathname);
    } catch {
      urlPath = "/";
    }

    // Normalize: remove leading slash for path.join safety
    const relativePath = urlPath.replace(/^\/+/, "");

    // 1. Try exact file match (assets like .js, .css, .ico, images)
    const exactPath = path.join(frontendRoot, relativePath);
    if (fs.existsSync(exactPath) && fs.statSync(exactPath).isFile()) {
      return serveFile(exactPath);
    }

    // 2. Try as directory with index.html (Next.js trailingSlash: true)
    const indexPath = path.join(frontendRoot, relativePath, "index.html");
    if (fs.existsSync(indexPath)) {
      return serveFile(indexPath);
    }

    // 3. Fallback: serve root index.html (client-side routing handles it)
    const rootIndex = path.join(frontendRoot, "index.html");
    if (fs.existsSync(rootIndex)) {
      return serveFile(rootIndex);
    }

    // 4. Nothing found
    log.warn(`⚠️ [protocol] 404 for: ${request.url}`);
    return new Response("Not Found", { status: 404 });
  });

  log.info("✅ Custom app:// protocol registered");
}

/**
 * Serve a local file as a Response with the correct MIME type.
 */
function serveFile(filePath: string): Response {
  const ext = path.extname(filePath).toLowerCase();
  const mimeType = MIME_TYPES[ext] || "application/octet-stream";
  const body = fs.readFileSync(filePath);
  return new Response(body, {
    status: 200,
    headers: { "Content-Type": mimeType },
  });
}

// ─── Window ──────────────────────────────────────────────────────────────────

/**
 * Create the main application window.
 *
 * In production: loads the app:// protocol pointing at the static export.
 * In development: connects to Next.js dev server on localhost:3000.
 */
function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    title: "Billino",
    icon: path.join(__dirname, "..", "icons", "icon.ico"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      // Disable same-origin policy in packaged mode so the app:// origin
      // can make fetch() calls to the local backend on http://127.0.0.1.
      // Safe because: backend is localhost-only, no external content loaded,
      // contextIsolation remains true, nodeIntegration remains false.
      webSecurity: !app.isPackaged,
    },
  });

  // Pipe renderer console.log/warn/error to electron-log for debugging
  mainWindow.webContents.on("console-message", (_event, level, message, line, sourceId) => {
    const tag = "[renderer]";
    const source = sourceId ? ` (${sourceId}:${line})` : "";
    switch (level) {
      case 0: log.debug(`${tag} ${message}${source}`); break;  // verbose
      case 1: log.info(`${tag} ${message}${source}`); break;   // info
      case 2: log.warn(`${tag} ${message}${source}`); break;   // warning
      case 3: log.error(`${tag} ${message}${source}`); break;  // error
      default: log.info(`${tag} ${message}${source}`);
    }
  });

  if (app.isPackaged) {
    // Production: load via custom protocol (handles SPA routing)
    mainWindow.loadURL("app://./dashboard");

    // Force full-page navigation for internal links.
    // Next.js client-side router intercepts <Link> clicks and does SPA-style
    // soft navigation (RSC payload fetching), which doesn't work with the
    // custom app:// protocol. Since every route has its own pre-rendered
    // index.html, full-page navigation is instant from local files.
    mainWindow.webContents.on("dom-ready", () => {
      mainWindow?.webContents.executeJavaScript(`
        document.addEventListener('click', function(e) {
          var anchor = e.target.closest ? e.target.closest('a') : null;
          if (!anchor) return;
          var href = anchor.getAttribute('href');
          if (!href) return;
          // Only intercept internal routes (starting with /)
          if (href.startsWith('/') && !href.startsWith('//')) {
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            window.location.href = 'app://.' + href;
          }
        }, true);
      `);
    });
  } else {
    // Development: connect to Next.js dev server
    mainWindow.loadURL("http://localhost:3000");
    mainWindow.webContents.openDevTools({ mode: "detach" });
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// ─── App Lifecycle ───────────────────────────────────────────────────────────

// Register custom scheme privileges before app is ready.
// This must happen synchronously before the 'ready' event.
protocol.registerSchemesAsPrivileged([
  {
    scheme: "app",
    privileges: {
      standard: true, // allows relative URL resolution (e.g. ./file.js)
      secure: true, // treat as secure origin (needed for fetch, etc.)
      supportFetchAPI: true,
      corsEnabled: true,
    },
  },
]);

app.whenReady().then(async () => {
  log.info("=" .repeat(60));
  log.info("🚀 Billino Desktop starting...");
  log.info(`📦 Packaged: ${app.isPackaged}`);
  log.info(`📂 userData: ${app.getPath("userData")}`);
  log.info("=" .repeat(60));

  try {
    // Register app:// protocol handler for static frontend files
    registerAppProtocol();

    ensureUserDataDirs();
    startBackend();
    await waitForBackend();
    createWindow();
  } catch (err) {
    log.error(`❌ Startup failed: ${err}`);
    dialog.showErrorBox(
      "Billino – Startfehler",
      `Die Anwendung konnte nicht gestartet werden:\n${err}`
    );
    stopBackend();
    app.quit();
  }
});

app.on("window-all-closed", () => {
  // On macOS, apps stay active until Cmd+Q
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("activate", () => {
  // macOS: recreate window when dock icon is clicked
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on("before-quit", async (event) => {
  if (isQuitting) return;

  event.preventDefault();
  isQuitting = true;

  log.info("🛑 Billino shutting down...");

  // Step 1: Trigger backup before killing the backend
  await triggerShutdownBackup();

  // Step 2: Stop backend process
  stopBackend();

  // Step 3: Exit
  log.info("✅ Shutdown complete");
  app.exit(0);
});
