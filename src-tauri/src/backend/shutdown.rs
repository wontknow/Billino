// src-tauri/src/backend/shutdown.rs
// Graceful backend shutdown

use super::error::BackendError;
use super::monitor;

/// Stop backend gracefully
pub fn stop_backend_gracefully() -> Result<(), BackendError> {
    log::info!("🛑 Initiating graceful backend shutdown...");

    // Minimal but safer shutdown: trigger backup then kill
    if let Err(e) = super::monitor::trigger_backup_and_shutdown() {
        log::error!("❌ Failed during backup+shutdown: {}", e);
        return Err(BackendError::Internal(e));
    }

    log::info!("✅ Backend shutdown complete");
    Ok(())
}

/// Force kill backend process (fallback)
pub fn force_kill_backend() -> Result<(), BackendError> {
    log::warn!("💥 Force killing backend...");
    
    // This is a fallback - ideally we should use the stored child process
    if let Err(e) = super::monitor::kill_backend() {
        log::error!("❌ Failed to kill backend: {}", e);
        return Err(BackendError::Internal(e));
    }

    log::info!("✅ Backend force kill successful");
    Ok(())
}

