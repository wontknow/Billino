// src-tauri/src/main.rs
// Billino Desktop Application - Main Entry Point

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend;
mod commands;
mod error;
mod events;

use tauri::{Manager, WindowEvent};
use std::sync::Arc;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_log::Builder::default().build())
        .setup(|app| {
            log::info!("🚀 Billino Desktop starting...");

            // Load backend configuration
            log::info!("⚙️ Loading backend configuration...");
            let config = match backend::config::load_config(app.handle()) {
                Ok(cfg) => {
                    log::info!("✅ Config loaded: {}", cfg.backend_url());
                    cfg
                }
                Err(e) => {
                    log::error!("❌ Failed to load configuration: {}", e);
                    events::emit_backend_error(app.handle(), &e);
                    return Err(tauri::Error::Io(std::io::Error::new(
                        std::io::ErrorKind::InvalidInput,
                        e,
                    )));
                }
            };

            // Validate configuration
            if let Err(e) = config.validate() {
                log::error!("❌ Configuration validation failed: {}", e);
                events::emit_backend_error(app.handle(), &format!("Validation: {}", e));
                return Err(tauri::Error::Io(std::io::Error::new(
                    std::io::ErrorKind::InvalidInput,
                    e,
                )));
            }

            // Check port availability
            if !config.is_port_available().unwrap_or(false) {
                let err = format!(
                    "Port {} is already in use. Change BACKEND_PORT or stop existing instances.",
                    config.port
                );
                log::error!("❌ {}", err);
                events::emit_backend_error(app.handle(), &err);
                return Err(tauri::Error::Io(std::io::Error::new(
                    std::io::ErrorKind::AddrInUse,
                    err,
                )));
            }

            // Spawn backend process
            log::info!("🔄 Spawning backend process...");
            let child = match backend::spawn::spawn_backend(&config) {
                Ok(c) => {
                    log::info!("✅ Backend process spawned");
                    c
                }
                Err(e) => {
                    log::error!("❌ Failed to spawn backend: {}", e);
                    events::emit_backend_error(app.handle(), &e);
                    return Err(tauri::Error::Io(std::io::Error::new(
                        std::io::ErrorKind::Other,
                        e,
                    )));
                }
            };

            // Wait for backend to become healthy
            let config_clone = config.clone();
            let app_handle = app.handle().clone();
            std::thread::spawn(move || {
                log::info!(
                    "⏳ Waiting for backend to become healthy (timeout: {}s)...",
                    config_clone.startup_timeout_secs
                );

                match std::thread::sleep(std::time::Duration::from_secs(1));
                backend::health::wait_until_healthy_blocking(&config_clone) {
                    Ok(health) => {
                        log::info!("✅ Backend is healthy!");
                        events::emit_backend_ready(&app_handle);
                    }
                    Err(e) => {
                        log::error!("❌ Backend health check failed: {}", e);
                        events::emit_backend_error(&app_handle, &e);
                    }
                }
            });

            // Start background monitoring
            let config_clone = config.clone();
            let app_handle = app.handle().clone();
            std::thread::spawn(move || {
                backend::monitor::monitor_backend(&config_clone, &app_handle, child);
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            match event {
                WindowEvent::CloseRequested { api, .. } => {
                    log::info!("🪟 Window close requested");
                    // Don't prevent close, let shutdown sequence handle it
                }
                _ => {}
            }
        })
        .invoke_handler(tauri::generate_handler![
            commands::backend::get_backend_status,
            commands::backend::get_backend_health,
            commands::backend::restart_backend,
        ])
        .on_window_event(|_window, event| match event {
            WindowEvent::Destroyed => {
                log::info!("🛑 Main window destroyed, initiating graceful shutdown...");
                backend::shutdown::stop_backend_gracefully();
            }
            _ => {}
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
