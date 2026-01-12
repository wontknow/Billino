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
}

impl BackendMonitor {
    pub fn new() -> Self {
        Self {
            state: Arc::new(Mutex::new(BackendState::NotStarted)),
            child: Arc::new(Mutex::new(None)),
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
