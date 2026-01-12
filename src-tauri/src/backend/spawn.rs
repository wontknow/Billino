// src-tauri/src/backend/spawn.rs
// Backend process spawning

use std::process::{Command, Stdio};

use tauri_plugin_shell::process::CommandChild;

use super::config::BackendConfig;
use super::error::BackendError;

/// Spawn the backend process
pub fn spawn_backend(config: &BackendConfig) -> Result<CommandChild, BackendError> {
    log::info!(
        "🔄 Spawning backend process: {:?}",
        config.binary_path
    );

    // Build command
    let mut cmd = Command::new(&config.binary_path);

    // Set working directory to backend folder
    if let Some(parent) = config.binary_path.parent() {
        cmd.current_dir(parent);
    }

    // Set environment variables
    cmd.env("BACKEND_HOST", &config.host);
    cmd.env("BACKEND_PORT", config.port.to_string());
    cmd.env("TAURI_ENABLED", "true");

    // Pass through additional env vars
    for (key, value) in &config.env_vars {
        cmd.env(key, value);
    }

    // Configure stdio
    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());

    // Spawn process using tauri_plugin_shell
    use tauri_plugin_shell::ShellExt;

    let (rx, mut child) = tauri::async_runtime::block_on(async {
        match cmd.spawn() {
            Ok((rx, child)) => (rx, child),
            Err(e) => {
                return Err(BackendError::SpawnFailed(e.to_string()));
            }
        }
    })?;

    // Log stdout/stderr
    tauri::async_runtime::spawn(async move {
        use futures::io::AsyncReadExt;
        let mut output = String::new();
        let mut rx = rx;
        while let Ok(Some(line)) = rx.read_line().await {
            output.push_str(&line);
        }
        if !output.is_empty() {
            log::debug!("Backend output: {}", output);
        }
    });

    log::info!("✅ Backend process spawned (PID: {:?})", child.pid());
    Ok(child)
}
