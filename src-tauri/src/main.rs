// src-tauri/src/main.rs
// Billino Desktop Application - Main Entry Point

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend;
mod commands;
mod error;
mod events;

use tauri::WindowEvent;

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
                    events::emit_backend_error(app.handle(), &e.to_string());
                    return Err(Box::new(std::io::Error::new(
                        std::io::ErrorKind::InvalidInput,
                        e.to_string(),
                    )));
                }
            };

            // Validate configuration
            if let Err(e) = config.validate() {
                log::error!("❌ Configuration validation failed: {}", e);
                events::emit_backend_error(app.handle(), &format!("Validation: {}", e));
                return Err(Box::new(std::io::Error::new(
                    std::io::ErrorKind::InvalidInput,
                    e.to_string(),
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
                return Err(Box::new(std::io::Error::new(
                    std::io::ErrorKind::AddrInUse,
                    err,
                )));
            }

            // Spawn backend process
            log::info!("🔄 Spawning backend process...");
            let child = match backend::spawn::spawn_backend(&config, app.handle()) {
                Ok(c) => {
                    log::info!("✅ Backend process spawned");
                    c
                }
                Err(e) => {
                    log::error!("❌ Failed to spawn backend: {}", e);
                    events::emit_backend_error(app.handle(), &e.to_string());
                    return Err(Box::new(std::io::Error::new(
                        std::io::ErrorKind::Other,
                        e.to_string(),
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

                std::thread::sleep(std::time::Duration::from_secs(1));
                match backend::health::wait_until_healthy_blocking(&config_clone) {
                    Ok(_health) => {
                        log::info!("✅ Backend is healthy!");
                        events::emit_backend_ready(&app_handle);
                    }
                    Err(e) => {
                        log::error!("❌ Backend health check failed: {}", e);
                        events::emit_backend_error(&app_handle, &e.to_string());
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
                // Use scoped thread with join to ensure cleanup completes before process exit
                // while still being non-blocking to the event loop
                std::thread::scope(|s| {
                    s.spawn(|| {
                        if let Err(err) = backend::shutdown::stop_backend_gracefully() {
                            log::error!("❌ Failed to stop backend gracefully: {err}");
                        }
                    });
                });
            }
            _ => {}
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
