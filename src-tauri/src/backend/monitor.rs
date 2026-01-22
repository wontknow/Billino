// src-tauri/src/backend/monitor.rs
// Continuous backend process monitoring

use std::process::Child;
use std::sync::{Arc, Mutex};
use std::time::Duration;

use super::config::BackendConfig;
use super::state::BackendState;

pub struct BackendMonitor {
    state: Arc<Mutex<BackendState>>,
    child: Arc<Mutex<Option<Child>>>,
    config: Arc<Mutex<Option<BackendConfig>>>,
}

impl BackendMonitor {
    pub fn new() -> Self {
        Self {
            state: Arc::new(Mutex::new(BackendState::NotStarted)),
            child: Arc::new(Mutex::new(None)),
            config: Arc::new(Mutex::new(None)),
        }
    }

    pub fn get_state(&self) -> BackendState {
        *self.state.lock().unwrap()
    }

    pub fn set_state(&self, state: BackendState) {
        *self.state.lock().unwrap() = state;
        log::info!("📊 Backend state changed: {}", state);
    }

    pub fn set_child(&self, child: Child) {
        *self.child.lock().unwrap() = Some(child);
        log::info!("💾 Backend process stored");
    }

    pub fn set_config(&self, cfg: BackendConfig) {
        *self.config.lock().unwrap() = Some(cfg);
    }

    pub fn kill_child(&self) -> Result<(), String> {
        let mut child_lock = self.child.lock().unwrap();
        if let Some(mut child) = child_lock.take() {
            log::info!("🛑 Terminating backend process...");
            child.kill().map_err(|e| format!("Failed to kill process: {}", e))?;
            log::info!("✅ Backend process terminated");
            Ok(())
        } else {
            log::warn!("⚠️ No child process to terminate");
            Ok(())
        }
    }
}

// Global monitor instance
lazy_static::lazy_static! {
    static ref MONITOR: BackendMonitor = BackendMonitor::new();
}

pub fn monitor_backend(config: &BackendConfig, app: &tauri::AppHandle, child: Child) {
    log::info!("👁️ Starting backend monitoring...");

    MONITOR.set_state(BackendState::Starting);
    MONITOR.set_child(child); // Store child process for later termination
    MONITOR.set_config(config.clone());

    // Periodic health checks
    let app_handle = app.clone();
    let config_clone = config.clone();

    std::thread::spawn(move || {
        let mut consecutive_failures = 0;

        loop {
            std::thread::sleep(Duration::from_secs(config_clone.health_check_interval_secs));

            if MONITOR.get_state().is_stopped() {
                log::info!("⏹️ Backend monitoring stopped (process not running)");
                break;
            }

            match super::health::wait_until_healthy_blocking(&config_clone) {
                Ok(_health) => {
                    if MONITOR.get_state() != BackendState::Healthy {
                        log::info!("✅ Backend recovered to healthy state");
                        MONITOR.set_state(BackendState::Healthy);
                        crate::events::emit_backend_ready(&app_handle);
                    }
                    consecutive_failures = 0;
                }
                Err(_e) => {
                    consecutive_failures += 1;

                    if consecutive_failures >= 3 {
                        if MONITOR.get_state() != BackendState::Unhealthy {
                            log::warn!(
                                "⚠️ Backend is unhealthy ({} consecutive failures)",
                                consecutive_failures
                            );
                            MONITOR.set_state(BackendState::Unhealthy);
                            crate::events::emit_backend_unhealthy(&app_handle);
                        }
                    }
                }
            }
        }
    });
}

pub fn get_backend_state() -> BackendState {
    MONITOR.get_state()
}

pub fn kill_backend() -> Result<(), String> {
    MONITOR.kill_child()
}

/// Trigger a backup via API and then terminate backend
/// 
/// This function uses fire-and-forget semantics to avoid blocking the shutdown process.
/// The backup request is sent in a separate thread with a short connect timeout,
/// and the backend is terminated immediately without waiting for the backup to complete.
pub fn trigger_backup_and_shutdown() -> Result<(), String> {
    // Try to trigger manual backup first (best-effort, fire-and-forget)
    if let Some(cfg) = MONITOR.config.lock().unwrap().clone() {
        let url = format!("{}/backups/trigger", cfg.backend_url());
        
        log::info!("🧩 Triggering manual backup before shutdown (fire-and-forget): {}", url);
        
        // Spawn thread for non-blocking backup request (fire-and-forget)
        std::thread::spawn(move || {
            let client = match reqwest::blocking::Client::builder()
                .connect_timeout(Duration::from_millis(500))  // Short connect timeout
                .timeout(Duration::from_secs(2))              // Max 2s total
                .build()
            {
                Ok(c) => c,
                Err(e) => {
                    log::error!("❌ Failed to build HTTP client for backup request: {}", e);
                    return;
                }
            };
            
            match client.post(&url).send() {
                Ok(r) => {
                    if r.status().is_success() {
                        log::info!("✅ Manual backup request sent successfully");
                    } else {
                        log::warn!("⚠️ Manual backup returned status {}", r.status());
                    }
                }
                Err(e) => {
                    log::warn!("⚠️ Manual backup request failed: {}", e);
                }
            }
        });
    } else {
        log::warn!("⚠️ No backend config available for manual backup trigger");
    }

    // Terminate backend process immediately (don't wait for backup)
    log::info!("🛑 Terminating backend process");
    kill_backend()
}
