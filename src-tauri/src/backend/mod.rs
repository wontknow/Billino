// src-tauri/src/backend/mod.rs
// Backend process management module

pub mod config;
pub mod error;
pub mod health;
pub mod monitor;
pub mod shutdown;
pub mod spawn;
pub mod state;

pub use config::BackendConfig;
pub use error::BackendError;
pub use state::BackendState;
