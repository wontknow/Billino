// src-tauri/src/commands/backend.rs
// Backend management commands

use serde::{Deserialize, Serialize};

use crate::backend::monitor;

#[derive(Debug, Serialize, Deserialize)]
pub struct BackendStatus {
    pub state: String,
    pub is_running: bool,
    pub is_healthy: bool,
    pub can_restart: bool,
}

/// Get current backend status
#[tauri::command]
pub fn get_backend_status() -> BackendStatus {
    let state = monitor::get_backend_state();
    BackendStatus {
        state: state.to_string(),
        is_running: state.is_running(),
        is_healthy: state.is_healthy(),
        can_restart: state.is_stopped(),
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct BackendHealth {
    pub status: String,
    pub ready: bool,
    pub db_status: String,
}

/// Get backend health information (from /health endpoint)
#[tauri::command]
pub async fn get_backend_health() -> Result<BackendHealth, String> {
    // This would call the actual health endpoint
    // For now, return status from monitor
    let state = monitor::get_backend_state();
    Ok(BackendHealth {
        status: state.to_string(),
        ready: state.is_healthy(),
        db_status: "ok".to_string(),
    })
}

/// Restart backend process
#[tauri::command]
pub fn restart_backend() -> Result<String, String> {
    log::info!("🔄 User requested backend restart");
    
    let state = monitor::get_backend_state();
    if state.is_running() {
        return Err("Backend is already running. Stop it first.".to_string());
    }

    // TODO: Implement restart logic
    // 1. Wait for current process to stop
    // 2. Spawn new process
    // 3. Wait for health checks

    Ok("Backend restart initiated".to_string())
}
