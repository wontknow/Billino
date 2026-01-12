// src-tauri/src/backend/spawn.rs
// Backend process spawning

use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use tauri::Manager;

use super::config::BackendConfig;
use super::error::BackendError;

/// Spawn the backend process
pub fn spawn_backend(config: &BackendConfig, app_handle: &tauri::AppHandle) -> Result<Child, BackendError> {
    log::info!(
        "🔄 Spawning backend process: {:?}",
        config.binary_path
    );

    // Get AppData directory for Tauri
    let app_data_dir = app_handle.path()
        .app_data_dir()
        .map_err(|e| BackendError::Internal(format!("Cannot get AppData directory: {}", e)))?
        .join("Billino");
    
    log::info!("📂 Using data directory: {:?}", app_data_dir);
    
    // Ensure data directory exists
    std::fs::create_dir_all(&app_data_dir)
        .map_err(|e| BackendError::Internal(format!("Cannot create data directory: {}", e)))?;

    // Check if this is a Python file (.py) - use Python interpreter
    let mut cmd = if config.binary_path.extension().and_then(|s| s.to_str()) == Some("py") {
        log::info!("📝 Detected Python script, using uvicorn directly");
        
        // Find Python in virtual environment
        let backend_dir = config.binary_path.parent()
            .ok_or_else(|| BackendError::Internal("Cannot determine backend directory".to_string()))?;
        
        #[cfg(target_os = "windows")]
        let python_path = backend_dir.join(".venv/Scripts/python.exe");
        #[cfg(not(target_os = "windows"))]
        let python_path = backend_dir.join(".venv/bin/python");
        
        let python_exe = if python_path.exists() {
            log::info!("✅ Using venv Python: {:?}", python_path);
            python_path
        } else {
            log::warn!("⚠️ venv not found, using system Python");
            PathBuf::from("python")
        };
        
        let mut python_cmd = Command::new(&python_exe);
        python_cmd.args(&["-m", "uvicorn", "main:app", "--host", &config.host, "--port", &config.port.to_string()]);
        
        // Set working directory to backend folder
        python_cmd.current_dir(backend_dir);
        
        python_cmd
    } else {
        // Binary executable
        let mut bin_cmd = Command::new(&config.binary_path);
        
        // Set working directory to backend folder
        if let Some(parent) = config.binary_path.parent() {
            bin_cmd.current_dir(parent);
        }
        
        bin_cmd
    };

    // Set environment variables
    cmd.env("BACKEND_HOST", &config.host);
    cmd.env("BACKEND_PORT", config.port.to_string());
    cmd.env("TAURI_ENABLED", "true");
    cmd.env("DATA_DIR", app_data_dir.to_string_lossy().to_string());

    // Pass through additional env vars
    for (key, value) in &config.env_vars {
        cmd.env(key, value);
    }

    // Configure stdio - inherit for console output
    cmd.stdout(Stdio::inherit());
    cmd.stderr(Stdio::inherit());

    // Spawn process
    let child = cmd
        .spawn()
        .map_err(|e| BackendError::SpawnFailed(e.to_string()))?;

    log::info!("✅ Backend process spawned (PID: {:?})", child.id());
    Ok(child)
}
