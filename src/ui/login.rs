use adw::prelude::*;
use adw::Application;
use gtk4 as gtk;

pub fn show_login_window(app: &Application) {
    let window = adw::ApplicationWindow::builder()
        .application(app)
        .title("BlueBubbles Login")
        .default_width(420)
        .default_height(260)
        .resizable(false)
        .build();

    let toast_overlay = adw::ToastOverlay::new();

    // Root container
    let root = gtk::Box::new(gtk::Orientation::Vertical, 12);
    root.set_margin_top(24);
    root.set_margin_bottom(24);
    root.set_margin_start(24);
    root.set_margin_end(24);

    // Title
    let title = gtk::Label::new(Some("Connect to BlueBubbles"));
    title.add_css_class("title-2");
    title.set_halign(gtk::Align::Start);
    root.append(&title);

    // Server URL
    let server_entry = gtk::Entry::new();
    server_entry.set_placeholder_text(Some("Server URL (e.g. https://myserver:1234)"));
    server_entry.set_hexpand(true);

    // Password
    let pass_entry = gtk::PasswordEntry::new();
    pass_entry.set_placeholder_text(Some("API Password"));
    pass_entry.set_hexpand(true);

    // Arrange fields
    let form = gtk::Box::new(gtk::Orientation::Vertical, 8);
    form.append(&server_entry);
    form.append(&pass_entry);
    root.append(&form);

    // Status label (small, muted)
    let status = gtk::Label::new(None);
    status.add_css_class("dim-label");
    status.set_halign(gtk::Align::Start);
    root.append(&status);

    // Login button
    let login_btn = gtk::Button::with_label("Connect");
    login_btn.add_css_class("suggested-action");
    login_btn.set_halign(gtk::Align::End);
    root.append(&login_btn);

    toast_overlay.set_child(Some(&root));
    // Add a header bar inside content to show window decorations
    let container = gtk::Box::new(gtk::Orientation::Vertical, 0);
    let header = adw::HeaderBar::new();
    let title = gtk::Label::new(Some("BlueBubbles"));
    header.set_title_widget(Some(&title));
    container.append(&header);
    container.append(&toast_overlay);
    window.set_content(Some(&container));

    // Trigger connect action
    let on_connect = {
        let app = app.clone();
        let window = window.clone();
        let overlay = toast_overlay.clone();
        let server_entry = server_entry.clone();
        let pass_entry = pass_entry.clone();
        move || {
            let overlay = overlay.clone();
            let url = crate::utils::normalize_url(&server_entry.text());
            let password = pass_entry.text().to_string();
            if url.is_empty() || password.is_empty() {
                overlay.add_toast(adw::Toast::new("Please enter server URL and password."));
                return;
            }

            status.set_label("Connecting…");
            status.add_css_class("dim-label");

            // Optional server info check
            let password_for_async = password.clone();
            let url_for_async = url.clone();
            // Explicitly type the Result payload to avoid any inference to `str`
            let rx: glib::Receiver<Result<(String, String), String>> = crate::utils::run_async_to_main(async move {
                let client = crate::api::client::ApiClient { http: reqwest::Client::builder()
                        .timeout(std::time::Duration::from_secs(5))
                        .build()
                        .map_err(|e| e.to_string())?, ws_url: None };
                
                // Try to get server info to validate connection
                let server_info_url = format!("{}/api/v1/server/info?password={}", url_for_async.trim_end_matches('/'), &password_for_async);
                match client.http.get(&server_info_url).send().await {
                    Ok(resp) => {
                        if resp.status().is_success() {
                            Ok((url_for_async, "Connected".to_string()))
                        } else {
                            // Still save credentials even if server info fails
                            Ok((url_for_async, "Saved (server info unavailable)".to_string()))
                        }
                    }
                    Err(_) => {
                        // Still save credentials even if request fails
                        Ok((url_for_async, "Saved (server unreachable)".to_string()))
                    }
                }
            });

            let status_label = status.clone();
            let app2 = app.clone();
            let window2 = window.clone();
            let overlay2 = overlay.clone();
            let password_for_save = password.clone();
            rx.attach(None, move |res| {
                match res {
                    Ok((base_url, message)) => {
                        eprintln!("Server check: {base_url} - {message}");
                        status_label.set_label(&message);
                        // Always persist credentials
                        let mut st = crate::app::AppState::load();
                        st.base_url = base_url;
                        st.password = password_for_save.clone();
                        st.token = None; // Clear any old token
                        if let Err(e) = st.save() {
                            overlay2.add_toast(adw::Toast::new(&format!("Failed to save settings: {}", e)));
                        }
                        crate::ui::main_window::show_main_window(&app2);
                        window2.close();
                    }
                    Err(err) => {
                        eprintln!("Server check failed: {err}");
                        status_label.set_label("Connection failed");
                        overlay2.add_toast(adw::Toast::new("Could not validate server. Check URL and password."));
                    }
                }
                glib::ControlFlow::Continue
            });
        }
    };

    use std::rc::Rc;
    let on_connect: Rc<dyn Fn()> = Rc::new(on_connect);
    // Button click
    {
        let on_connect = on_connect.clone();
        login_btn.connect_clicked(move |_| (on_connect)());
    }
    // Enter key in either field triggers connect
    {
        let on_connect = on_connect.clone();
        server_entry.connect_activate(move |_| (on_connect)());
    }
    {
        let on_connect = on_connect.clone();
        pass_entry.connect_activate(move |_| (on_connect)());
    }

    window.present();
}
