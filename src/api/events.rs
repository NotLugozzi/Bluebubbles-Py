use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct IncomingEvent {
    pub event_type: String,
    pub data: serde_json::Value,
}

// TODO: Add event handling logic
