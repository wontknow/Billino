// src-tauri/src/backend/state.rs
// Backend lifecycle state machine

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BackendState {
    /// Initial state, backend not yet started
    NotStarted,

    /// Backend process is spawning
    Starting,

    /// Backend is running and healthy
    Healthy,

    /// Backend is running but health checks are failing
    Unhealthy,

    /// Graceful shutdown in progress
    Stopping,

    /// Backend has stopped cleanly
    StoppedClean,

    /// Backend was force-killed
    StoppedForce,

    /// Backend crashed unexpectedly
    Crashed,
}

impl BackendState {
    pub fn is_running(&self) -> bool {
        matches!(self, BackendState::Starting | BackendState::Healthy)
    }

    pub fn is_healthy(&self) -> bool {
        matches!(self, BackendState::Healthy)
    }

    pub fn is_stopped(&self) -> bool {
        matches!(
            self,
            BackendState::StoppedClean | BackendState::StoppedForce | BackendState::Crashed
        )
    }

    pub fn description(&self) -> &'static str {
        match self {
            BackendState::NotStarted => "Not Started",
            BackendState::Starting => "Starting",
            BackendState::Healthy => "Healthy",
            BackendState::Unhealthy => "Unhealthy",
            BackendState::Stopping => "Stopping",
            BackendState::StoppedClean => "Stopped (Clean)",
            BackendState::StoppedForce => "Stopped (Forced)",
            BackendState::Crashed => "Crashed",
        }
    }
}

impl std::fmt::Display for BackendState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.description())
    }
}
