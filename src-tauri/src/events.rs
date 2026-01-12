// src-tauri/src/events.rs
// Tauri event emissions to frontend

use serde_json::json;
use tauri::Emitter;

/// Emit when backend has started and is healthy
pub fn emit_backend_ready(app: &tauri::AppHandle) {
    log::info!("📡 Emitting backend:ready event");
    let _ = app.emit("backend:ready", json!({
        "status": "ready",
        "message": "Backend is operational"
    }));
}

/// Emit when backend health check fails (but still running)
pub fn emit_backend_unhealthy(app: &tauri::AppHandle) {
    log::warn!("📡 Emitting backend:unhealthy event");
    let _ = app.emit("backend:unhealthy", json!({
        "status": "unhealthy",
        "message": "Backend is running but health checks are failing"
    }));
}

/// Emit when backend stops
pub fn emit_backend_stopped(app: &tauri::AppHandle) {
    log::info!("📡 Emitting backend:stopped event");
    let _ = app.emit("backend:stopped", json!({
        "status": "stopped",
        "message": "Backend has stopped"
    }));
}

/// Emit when backend crashes unexpectedly
pub fn emit_backend_crashed(app: &tauri::AppHandle, reason: &str) {
    log::error!("📡 Emitting backend:crashed event: {}", reason);
    let _ = app.emit("backend:crashed", json!({
        "status": "crashed",
        "reason": reason,
        "message": format!("Backend crashed: {}", reason)
    }));
}

/// Emit when backend error occurs
pub fn emit_backend_error(app: &tauri::AppHandle, error: &str) {
    log::error!("📡 Emitting backend:error event: {}", error);
    let _ = app.emit("backend:error", json!({
        "status": "error",
        "error": error,
        "message": format!("Backend error: {}", error)
    }));
}
