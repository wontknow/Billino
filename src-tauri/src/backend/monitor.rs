// src-tauri/src/backend/monitor.rs
// Continuous backend process monitoring

use std::sync::{Arc, Mutex};
use std::time::Duration;

use tauri_plugin_shell::process::CommandChild;

use super::config::BackendConfig;
use super::state::BackendState;

pub struct BackendMonitor {
    state: Arc<Mutex<BackendState>>,
}

impl BackendMonitor {
    pub fn new() -> Self {
        Self {
            state: Arc::new(Mutex::new(BackendState::NotStarted)),
        }
    }

    pub fn get_state(&self) -> BackendState {
        *self.state.lock().unwrap()
    }

    pub fn set_state(&self, state: BackendState) {
        *self.state.lock().unwrap() = state;
        log::info!("📊 Backend state changed: {}", state);
    }
}

// Global monitor instance
lazy_static::lazy_static! {
    static ref MONITOR: BackendMonitor = BackendMonitor::new();
}

pub fn monitor_backend(config: &BackendConfig, app: &tauri::AppHandle, mut child: CommandChild) {
    log::info!("👁️ Starting backend monitoring...");

    MONITOR.set_state(BackendState::Starting);

    // Monitor process exit
    let app_handle = app.clone();
    let config_clone = config.clone();

    std::thread::spawn(move || {
        // Wait for process to exit
        match child.wait() {
            Ok(output) => {
                log::error!(
                    "❌ Backend process exited with status: {:?}",
                    output.code()
                );

                if output.code() == Some(0) {
                    MONITOR.set_state(BackendState::StoppedClean);
                    crate::events::emit_backend_stopped(&app_handle);
                } else {
                    MONITOR.set_state(BackendState::Crashed);
                    crate::events::emit_backend_crashed(&app_handle, "Unexpected exit");

                    // Try auto-restart
                    if config_clone.auto_restart {
                        log::info!("🔄 Attempting automatic restart...");
                        // Note: In production, you'd want to track restart attempts
                        // and abort after max_restart_attempts
                    }
                }
            }
            Err(e) => {
                log::error!("❌ Error waiting for backend process: {}", e);
                MONITOR.set_state(BackendState::Crashed);
                crate::events::emit_backend_error(&app_handle, &e.to_string());
            }
        }
    });

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
                                "⚠️ Backend is unhealthy ({}  consecutive failures)",
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
