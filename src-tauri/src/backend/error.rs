// src-tauri/src/backend/error.rs
// Backend error types

use std::fmt;

#[derive(Debug, Clone)]
pub enum BackendError {
    /// Configuration error (missing/invalid env var, invalid port, etc)
    ConfigError(String),

    /// Binary not found at expected path
    BinaryNotFound(String),

    /// Port is already in use
    PortAlreadyBound { port: u16 },

    /// Failed to spawn backend process
    SpawnFailed(String),

    /// Backend not responding to health checks
    HealthCheckTimeout { duration_secs: u64 },

    /// Health check returned non-200 status
    UnhealthyResponse { status: u16, body: String },

    /// Network error (connection refused, timeout, etc)
    NetworkError(String),

    /// Database is corrupted or inaccessible
    DatabaseError(String),

    /// Graceful shutdown timeout exceeded
    ShutdownTimeout { duration_secs: u64 },

    /// Unexpected internal error
    Internal(String),
}

impl fmt::Display for BackendError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            BackendError::ConfigError(msg) => {
                write!(f, "Configuration error: {}", msg)
            }
            BackendError::BinaryNotFound(path) => {
                write!(f, "Backend binary not found: {}", path)
            }
            BackendError::PortAlreadyBound { port } => {
                write!(
                    f,
                    "Port {} is already in use. Check for running instances or change BACKEND_PORT.",
                    port
                )
            }
            BackendError::SpawnFailed(msg) => {
                write!(f, "Failed to spawn backend process: {}", msg)
            }
            BackendError::HealthCheckTimeout { duration_secs } => {
                write!(
                    f,
                    "Backend did not become healthy within {}s. Check logs for startup errors.",
                    duration_secs
                )
            }
            BackendError::UnhealthyResponse { status, body } => {
                write!(f, "Backend returned unhealthy status {}: {}", status, body)
            }
            BackendError::NetworkError(msg) => {
                write!(
                    f,
                    "Network error connecting to backend: {}. Backend may not be running.",
                    msg
                )
            }
            BackendError::DatabaseError(msg) => {
                write!(f, "Database error: {}", msg)
            }
            BackendError::ShutdownTimeout { duration_secs } => {
                write!(
                    f,
                    "Backend did not stop gracefully within {}s",
                    duration_secs
                )
            }
            BackendError::Internal(msg) => {
                write!(f, "Internal error: {}", msg)
            }
        }
    }
}

impl std::error::Error for BackendError {}

impl From<std::io::Error> for BackendError {
    fn from(err: std::io::Error) -> Self {
        BackendError::Internal(err.to_string())
    }
}

impl From<reqwest::Error> for BackendError {
    fn from(err: reqwest::Error) -> Self {
        BackendError::NetworkError(err.to_string())
    }
}
