// src-tauri/src/backend/shutdown.rs
// Graceful backend shutdown

use std::process::Command;
use std::time::Duration;
use std::thread;

use super::error::BackendError;

/// Stop backend gracefully
pub fn stop_backend_gracefully() -> Result<(), BackendError> {
    log::info!("🛑 Initiating graceful backend shutdown...");

    // Try to send SIGTERM to the backend process
    #[cfg(unix)]
    {
        use nix::signal::{kill, Signal};
        use nix::unistd::Pid;

        // In a real implementation, you'd store the backend PID
        // For now, we just try to find and kill the process by port
        if let Err(e) = kill_backend_by_port() {
            log::warn!("⚠️ Graceful shutdown failed: {}. Trying force kill.", e);
            return Err(e);
        }
    }

    #[cfg(windows)]
    {
        // On Windows, we can use taskkill to gracefully terminate
        // This is less graceful than SIGTERM but better than SIGKILL
        if let Err(e) = kill_backend_by_port() {
            log::warn!("⚠️ Graceful shutdown failed: {}. Trying force kill.", e);
            return Err(e);
        }
    }

    log::info!("✅ Backend shutdown initiated");
    Ok(())
}

#[cfg(unix)]
fn kill_backend_by_port() -> Result<(), BackendError> {
    // Use lsof to find process on port
    let output = Command::new("lsof")
        .args(&["-i", ":8000", "-t"])
        .output()
        .map_err(|e| BackendError::Internal(e.to_string()))?;

    if output.status.success() {
        let pid_str = String::from_utf8_lossy(&output.stdout).trim().to_string();
        if !pid_str.is_empty() {
            Command::new("kill")
                .arg(&pid_str)
                .output()
                .map_err(|e| BackendError::Internal(e.to_string()))?;
        }
    }

    Ok(())
}

#[cfg(windows)]
fn kill_backend_by_port() -> Result<(), BackendError> {
    // Use netstat to find PID on port
    let output = Command::new("netstat")
        .args(&["-ano"])
        .output()
        .map_err(|e| BackendError::Internal(e.to_string()))?;

    let netstat_output = String::from_utf8_lossy(&output.stdout);

    // Parse netstat output to find PID on port 8000
    for line in netstat_output.lines() {
        if line.contains(":8000") && line.contains("LISTENING") {
            if let Some(pid_str) = line.split_whitespace().last() {
                Command::new("taskkill")
                    .args(&["/PID", pid_str, "/T"])
                    .output()
                    .map_err(|e| BackendError::Internal(e.to_string()))?;
                break;
            }
        }
    }

    Ok(())
}

/// Force kill backend process (last resort)
pub fn force_kill_backend() -> Result<(), BackendError> {
    log::warn!("💥 Force killing backend...");

    #[cfg(unix)]
    {
        let output = Command::new("pkill")
            .args(&["-9", "billino-backend"])
            .output()
            .map_err(|e| BackendError::Internal(e.to_string()))?;

        if !output.status.success() {
            return Err(BackendError::Internal(
                "Failed to force kill backend".to_string(),
            ));
        }
    }

    #[cfg(windows)]
    {
        Command::new("taskkill")
            .args(&["/IM", "billino-backend.exe", "/F"])
            .output()
            .map_err(|e| BackendError::Internal(e.to_string()))?;
    }

    log::info!("✅ Backend force killed");
    Ok(())
}
