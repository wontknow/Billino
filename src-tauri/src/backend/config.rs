// src-tauri/src/backend/config.rs
// Backend configuration loading and validation

use std::collections::HashMap;
use std::net::TcpListener;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use tauri::Manager;

use super::error::BackendError;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackendConfig {
    /// Path to backend binary
    pub binary_path: PathBuf,

    /// Database path (SQLite)
    pub db_path: Option<PathBuf>,

    /// Server host
    pub host: String,

    /// Server port
    pub port: u16,

    /// Startup timeout in seconds
    pub startup_timeout_secs: u64,

    /// Graceful shutdown timeout in seconds
    pub shutdown_timeout_secs: u64,

    /// Health check interval in seconds
    pub health_check_interval_secs: u64,

    /// Enable auto-restart on failure
    pub auto_restart: bool,

    /// Maximum restart attempts
    pub max_restart_attempts: u32,

    /// Environment variables for backend process
    pub env_vars: HashMap<String, String>,
}

impl BackendConfig {
    /// Get the backend server URL
    pub fn backend_url(&self) -> String {
        format!("http://{}:{}", self.host, self.port)
    }

    /// Get the health check URL
    pub fn health_url(&self) -> String {
        format!("{}/health", self.backend_url())
    }

    /// Check if the configured port is available
    pub fn is_port_available(&self) -> Result<bool, BackendError> {
        match TcpListener::bind((self.host.as_str(), self.port)) {
            Ok(_) => Ok(true),
            Err(e) if e.kind() == std::io::ErrorKind::AddrInUse => Ok(false),
            Err(e) => Err(BackendError::Internal(e.to_string())),
        }
    }

    /// Validate configuration
    pub fn validate(&self) -> Result<(), BackendError> {
        // Check host
        if self.host.is_empty() {
            return Err(BackendError::ConfigError("Host cannot be empty".to_string()));
        }

        // Check port
        if self.port < 1024 || self.port > 65535 {
            return Err(BackendError::ConfigError(format!(
                "Port must be between 1024 and 65535, got {}",
                self.port
            )));
        }

        // Check binary exists
        if !self.binary_path.exists() {
            return Err(BackendError::BinaryNotFound(
                self.binary_path.display().to_string(),
            ));
        }

        // Check timeouts are reasonable
        if self.startup_timeout_secs < 5 {
            return Err(BackendError::ConfigError(
                "Startup timeout must be at least 5 seconds".to_string(),
            ));
        }

        if self.shutdown_timeout_secs < 10 {
            return Err(BackendError::ConfigError(
                "Shutdown timeout must be at least 10 seconds to allow time for backups".to_string(),
            ));
        }

        Ok(())
    }
}

/// Load backend configuration from Tauri environment
pub fn load_config(app: &tauri::AppHandle) -> Result<BackendConfig, BackendError> {
    log::info!("📂 Loading backend configuration...");

    // Resolve binary path
    let binary_path = resolve_binary_path(app)?;
    log::info!("📦 Binary path: {:?}", binary_path);

    // Load environment variables from .env file (if present)
    let env_vars = load_env_file(app)?;

    // Extract configuration from environment
    let host = env_vars
        .get("BACKEND_HOST")
        .cloned()
        .unwrap_or_else(|| "127.0.0.1".to_string());

    let port: u16 = env_vars
        .get("BACKEND_PORT")
        .and_then(|p| p.parse().ok())
        .unwrap_or(8000);

    let startup_timeout_secs = env_vars
        .get("BACKEND_STARTUP_TIMEOUT")
        .and_then(|t| t.parse().ok())
        .unwrap_or(30);

    let shutdown_timeout_secs = env_vars
        .get("BACKEND_SHUTDOWN_TIMEOUT")
        .and_then(|t| t.parse().ok())
        .unwrap_or(30); // Default to 30s to allow time for DB+PDF backups

    let health_check_interval_secs = env_vars
        .get("BACKEND_HEALTH_INTERVAL")
        .and_then(|t| t.parse().ok())
        .unwrap_or(5);

    let auto_restart = env_vars
        .get("BACKEND_AUTO_RESTART")
        .map(|v| v.to_lowercase() == "true")
        .unwrap_or(true);

    let max_restart_attempts = env_vars
        .get("BACKEND_MAX_RESTART_ATTEMPTS")
        .and_then(|a| a.parse().ok())
        .unwrap_or(3);

    let config = BackendConfig {
        binary_path,
        db_path: None,
        host,
        port,
        startup_timeout_secs,
        shutdown_timeout_secs,
        health_check_interval_secs,
        auto_restart,
        max_restart_attempts,
        env_vars,
    };

    // Validate configuration
    config.validate()?;
    log::info!("✅ Configuration validated");

    Ok(config)
}

/// Resolve backend binary path
fn resolve_binary_path(app: &tauri::AppHandle) -> Result<PathBuf, BackendError> {
    // Get the resource directory from Tauri
    let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|e| BackendError::Internal(e.to_string()))?;

    // In development, use Python directly instead of exe
    // Look for backend/main.py for development mode
    let dev_backend_path = resource_dir.join("../../../backend/main.py");
    if dev_backend_path.exists() {
        log::info!("✅ Using development Python backend: {:?}", dev_backend_path);
        return Ok(dev_backend_path);
    }

    // Fallback to bundled exe for production
    #[cfg(target_os = "windows")]
    let binary_name = "billino-backend.exe";
    #[cfg(not(target_os = "windows"))]
    let binary_name = "billino-backend";

    let binary_path = resource_dir.join(binary_name);

    if binary_path.exists() {
        log::info!("✅ Backend binary found: {:?}", binary_path);
        Ok(binary_path)
    } else {
        // Try looking in common paths
        let fallback_paths = vec![
            // Dev mode: bin directory
            resource_dir.join(format!("../../bin/{}", binary_name)),
            // Dev mode: backend dist
            resource_dir.join("../../../backend/dist/billino-backend"),
            // System-wide installations
            PathBuf::from(format!("/usr/local/bin/{}", binary_name)),
            PathBuf::from(format!("C:\\Program Files\\Billino\\{}", binary_name)),
        ];

        for path in fallback_paths {
            if path.exists() {
                log::info!("✅ Backend binary found at fallback: {:?}", path);
                return Ok(path);
            }
        }

        Err(BackendError::BinaryNotFound(
            binary_path.display().to_string(),
        ))
    }
}

/// Load environment variables from .env file
fn load_env_file(app: &tauri::AppHandle) -> Result<HashMap<String, String>, BackendError> {
    let mut env_vars = HashMap::new();

    // Try to load from .env in app data directory (production)
    if let Ok(app_dir) = app.path().app_data_dir() {
        let env_path = app_dir.join(".env");
        if env_path.exists() {
            if let Ok(content) = std::fs::read_to_string(&env_path) {
                for line in content.lines() {
                    if let Some((key, value)) = line.split_once('=') {
                        let key = key.trim().to_string();
                        let value = value.trim().trim_matches('"').to_string();
                        if !key.is_empty() && !key.starts_with('#') {
                            env_vars.insert(key, value);
                        }
                    }
                }
                log::info!("✅ Loaded {} environment variables from .env", env_vars.len());
                return Ok(env_vars);
            }
        }
    }

    // Try to load from backend/.env.tauri (Tauri development, preferred)
    #[cfg(debug_assertions)]
    {
        // Calculate project root: resource_dir -> ../../.. -> project root
        if let Ok(resource_dir) = app.path().resource_dir() {
            if let Some(project_root) = resource_dir.parent()
                .and_then(|p| p.parent())
                .and_then(|p| p.parent())
            {
                let tauri_env_path = project_root.join("backend/.env.tauri");
                if tauri_env_path.exists() {
                    if let Ok(content) = std::fs::read_to_string(&tauri_env_path) {
                        for line in content.lines() {
                            if let Some((key, value)) = line.split_once('=') {
                                let key = key.trim().to_string();
                                let value = value.trim().trim_matches('"').to_string();
                                if !key.is_empty() && !key.starts_with('#') {
                                    env_vars.insert(key, value);
                                }
                            }
                        }
                        log::info!("✅ Loaded {} environment variables from backend/.env.tauri (Tauri-specific)", env_vars.len());
                        return Ok(env_vars);
                    }
                }
            }
        }
    }

    // Try to load from backend/.env (fallback for development)
    #[cfg(debug_assertions)]
    {
        // Calculate project root: resource_dir -> ../../.. -> project root
        if let Ok(resource_dir) = app.path().resource_dir() {
            if let Some(project_root) = resource_dir.parent()
                .and_then(|p| p.parent())
                .and_then(|p| p.parent())
            {
                let dev_env_path = project_root.join("backend/.env");
                if dev_env_path.exists() {
                    if let Ok(content) = std::fs::read_to_string(&dev_env_path) {
                        for line in content.lines() {
                            if let Some((key, value)) = line.split_once('=') {
                                let key = key.trim().to_string();
                                let value = value.trim().trim_matches('"').to_string();
                                if !key.is_empty() && !key.starts_with('#') {
                                    env_vars.insert(key, value);
                                }
                            }
                        }
                        log::info!("✅ Loaded {} environment variables from backend/.env", env_vars.len());
                        return Ok(env_vars);
                    }
                }
            }
        }
    }

    log::info!("ℹ️ No .env file found, using defaults");
    Ok(env_vars)
}
