// src-tauri/src/backend/health.rs
// Backend health checking with exponential backoff

use std::time::{Duration, Instant};

use super::config::BackendConfig;
use super::error::BackendError;

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct HealthStatus {
    pub status: String,
    pub ready: bool,
    pub uptime_ms: u64,
    pub db_status: String,
    pub db_response_time_ms: u64,
}

/// Wait for backend to become healthy (blocking)
pub fn wait_until_healthy_blocking(config: &BackendConfig) -> Result<HealthStatus, BackendError> {
    let deadline = Instant::now() + Duration::from_secs(config.startup_timeout_secs);
    let mut attempt = 0;
    let mut last_error = None;

    loop {
        attempt += 1;

        if let Ok(health) = perform_health_check(config) {
            if health.ready {
                log::info!("✅ Backend healthy after {} attempts", attempt);
                return Ok(health);
            }
        } else if let Err(e) = perform_health_check(config) {
            last_error = Some(e.to_string());
        }

        if Instant::now() >= deadline {
            let _error_msg = last_error.unwrap_or_else(|| "Unknown error".to_string());
            return Err(BackendError::HealthCheckTimeout {
                duration_secs: config.startup_timeout_secs,
            });
        }

        let backoff = std::cmp::max(
            (2_u64).pow(std::cmp::min(attempt / 3, 3)),
            2,
        );
        log::debug!("Health check attempt {}, backing off {}s", attempt, backoff);
        std::thread::sleep(Duration::from_secs(backoff));
    }
}

/// Perform a single health check (blocking)
fn perform_health_check(config: &BackendConfig) -> Result<HealthStatus, BackendError> {
    let url = config.health_url();
    
    // Use blocking client for simplicity in sync context
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .map_err(|e| BackendError::NetworkError(e.to_string()))?;

    let response = client
        .get(&url)
        .send()
        .map_err(|e| {
            if e.is_timeout() {
                BackendError::HealthCheckTimeout {
                    duration_secs: 2,
                }
            } else {
                BackendError::NetworkError(e.to_string())
            }
        })?;

    if !response.status().is_success() {
        return Err(BackendError::UnhealthyResponse {
            status: response.status().as_u16(),
            body: response.text().unwrap_or_else(|_| String::new()),
        });
    }

    let health: HealthStatus = response.json().map_err(|e| {
        BackendError::Internal(format!("Failed to parse health response: {}", e))
    })?;

    Ok(health)
}

/// Async version for use in event handlers
pub async fn wait_until_healthy_async(
    config: &BackendConfig,
) -> Result<HealthStatus, BackendError> {
    let deadline = Instant::now() + Duration::from_secs(config.startup_timeout_secs);
    let mut attempt = 0;

    loop {
        attempt += 1;

        if let Ok(health) = perform_health_check_async(config).await {
            if health.ready {
                log::info!("✅ Backend healthy after {} attempts", attempt);
                return Ok(health);
            }
        }

        if Instant::now() >= deadline {
            return Err(BackendError::HealthCheckTimeout {
                duration_secs: config.startup_timeout_secs,
            });
        }

        // Exponential backoff
        let backoff = std::cmp::min(
            (2_u64).pow(std::cmp::min(attempt / 3, 3)),
            2,
        );
        tokio::time::sleep(Duration::from_secs(backoff)).await;
    }
}

/// Async health check
async fn perform_health_check_async(config: &BackendConfig) -> Result<HealthStatus, BackendError> {
    let url = config.health_url();
    
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .map_err(|e| BackendError::NetworkError(e.to_string()))?;

    let response = client
        .get(&url)
        .send()
        .await
        .map_err(|e| {
            if e.is_timeout() {
                BackendError::HealthCheckTimeout {
                    duration_secs: 2,
                }
            } else {
                BackendError::NetworkError(e.to_string())
            }
        })?;

    if !response.status().is_success() {
        return Err(BackendError::UnhealthyResponse {
            status: response.status().as_u16(),
            body: response.text().await.unwrap_or_else(|_| String::new()),
        });
    }

    let health: HealthStatus = response.json().await.map_err(|e| {
        BackendError::Internal(format!("Failed to parse health response: {}", e))
    })?;

    Ok(health)
}
