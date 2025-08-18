use adw::Application;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;
use directories::BaseDirs;

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AppState {
    pub base_url: String,
    pub password: String,
    pub token: Option<String>,
}

impl AppState {
    pub fn new() -> Self {
        Self::default()
    }
    // TOML authentication is preferred, but a JSON fallback is available. the program will attempt to convert legacy json to toml where possible
    fn toml_path() -> Option<PathBuf> {
        let base = BaseDirs::new()?;
        let cfg_dir = base.config_dir();
        Some(cfg_dir.join("bb.toml"))
    }

    fn legacy_json_path() -> Option<PathBuf> {
        let proj = directories::ProjectDirs::from("com", "example", "BlueBubblesGTK")?;
        Some(proj.config_dir().join("state.json"))
    }

    pub fn load() -> Self {
        if let Some(path) = Self::toml_path() {
            if let Ok(bytes) = fs::read(&path) {
                if let Ok(text) = String::from_utf8(bytes) {
                    if let Ok(state) = toml::from_str::<AppState>(&text) {
                        return state;
                    }
                }
            }
        }

        if let Some(legacy) = Self::legacy_json_path() {
            if let Ok(bytes) = fs::read(&legacy) {
                if let Ok(state) = serde_json::from_slice::<AppState>(&bytes) {
                    let _ = state.save();
                    return state;
                }
            }
        }

        Self::new()
    }

    pub fn save(&self) -> std::io::Result<()> {
        if let Some(path) = Self::toml_path() {
            if let Some(parent) = path.parent() { let _ = fs::create_dir_all(parent); }
            let toml = toml::to_string_pretty(self)
                .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e.to_string()))?;
            fs::write(path, toml)
        } else {
            Err(std::io::Error::new(std::io::ErrorKind::NotFound, "No config dir"))
        }
    }
}

pub fn build_ui(app: &Application) {
    let state = AppState::load();
    if !state.base_url.is_empty() && !state.password.is_empty() {
        crate::ui::main_window::show_main_window(app);
    } else {
        crate::ui::login::show_login_window(app);
    }
}
