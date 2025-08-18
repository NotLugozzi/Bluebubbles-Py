mod app;
mod utils;
mod api;
mod ui;
mod storage;

use adw::prelude::*;
use adw::Application;

fn main() {
    let app = Application::builder()
        .application_id("com.example.BluebubblesGtk")
        .build();
    app.connect_activate(|app| {
    let _ = crate::storage::init();
        crate::app::build_ui(app);
    });
    app.run();
}
