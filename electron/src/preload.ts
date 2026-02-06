/**
 * Billino Desktop – Preload Script
 *
 * Exposes a minimal, safe API to the renderer process via contextBridge.
 * This keeps nodeIntegration disabled while providing necessary desktop features.
 */

import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("billino", {
  /**
   * Get the platform the app is running on.
   */
  platform: process.platform,

  /**
   * Check if the app is running as a packaged Electron build.
   */
  isDesktop: true,

  /**
   * Get app version from package.json.
   */
  getVersion: (): Promise<string> => ipcRenderer.invoke("get-version"),
});
