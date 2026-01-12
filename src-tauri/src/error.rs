// src-tauri/src/error.rs
// Error types for Tauri app

use std::fmt;

#[derive(Debug)]
pub enum AppError {
    Backend(crate::backend::error::BackendError),
    Internal(String),
}

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AppError::Backend(e) => write!(f, "{}", e),
            AppError::Internal(msg) => write!(f, "{}", msg),
        }
    }
}

impl From<crate::backend::error::BackendError> for AppError {
    fn from(err: crate::backend::error::BackendError) -> Self {
        AppError::Backend(err)
    }
}
