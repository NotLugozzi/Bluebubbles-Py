use adw::prelude::*;
use adw::Application;

pub fn show_main_window(app: &Application) {
    let window = adw::ApplicationWindow::builder()
        .application(app)
        .title("BlueBubbles")
        .default_width(960)
        .default_height(640)
        .build();

    let overlay = adw::ToastOverlay::new();

    let split = adw::Flap::builder()
        .reveal_flap(true)
        .locked(true)
        .modal(false)
        .build();

    use std::rc::Rc;
    let sidebar = Rc::new(crate::ui::sidebar::Sidebar::new());
    split.set_flap(Some(&sidebar.widget()));

    let chat = crate::ui::chat_view::ChatView::new();
    split.set_content(Some(&chat));

    overlay.set_child(Some(&split));

    let container = gtk4::Box::new(gtk4::Orientation::Vertical, 0);
    let header = adw::HeaderBar::new();
    let title = gtk4::Label::new(Some("BlueBubbles"));
    header.set_title_widget(Some(&title));

    let new_chat_btn = gtk4::Button::with_label("New Chat");
    new_chat_btn.add_css_class("suggested-action");
    header.pack_end(&new_chat_btn);
    container.append(&header);
    container.append(&overlay);
    window.set_content(Some(&container));
    window.present();

    let state = crate::app::AppState::load();
    if !state.base_url.is_empty() && !state.password.is_empty() {
    if let Ok(cached) = crate::storage::get_chats(Some(200)) {
            if !cached.is_empty() {
        sidebar.set_items(cached);
            }
        }

        let client = crate::api::client::ApiClient::new();
        let overlay_clone = overlay.clone();
    let sidebar_clone = sidebar.clone();
        let rx = crate::utils::run_async_to_main(async move {
            match client.conversations(&state.base_url, &state.password).await {
                Ok((items, raw)) => {
                    let _ = crate::storage::upsert_chats(&items, Some(&raw));
                    Ok(items)
                }
                Err(e) => Err(e),
            }
        });
        rx.attach(None, move |res| {
            match res {
                Ok(items) => sidebar_clone.set_items(items),
                Err(err) => overlay_clone.add_toast(adw::Toast::new(&format!("Failed to load chats: {}", err))),
            }
            glib::ControlFlow::Continue
        });
    }

    {
    let overlay = overlay.clone();
    let sidebar_for_dialog = sidebar.clone();
    new_chat_btn.connect_clicked(move |_| {
            let dialog = gtk4::Window::builder()
                .title("Start New Chat")
                .transient_for(&window)
                .modal(true)
                .resizable(false)
                .default_width(400)
                .build();

            let main_box = gtk4::Box::new(gtk4::Orientation::Vertical, 0);
            
            let content = gtk4::Box::new(gtk4::Orientation::Vertical, 12);
            content.set_margin_top(24);
            content.set_margin_bottom(12);
            content.set_margin_start(24);
            content.set_margin_end(24);

            let info = gtk4::Label::new(Some("Type a phone number or email, or choose a contact:"));
            info.set_halign(gtk4::Align::Start);
            content.append(&info);

            let entry = gtk4::Entry::new();
            entry.set_placeholder_text(Some("Number or email"));
            entry.set_hexpand(true);
            content.append(&entry);

            let dropdown = gtk4::DropDown::from_strings(&[]);
            dropdown.set_hexpand(true);
            dropdown.set_enable_search(true);
            content.append(&dropdown);

            // Button area
            let button_box = gtk4::Box::new(gtk4::Orientation::Horizontal, 6);
            button_box.set_halign(gtk4::Align::End);
            button_box.set_margin_top(12);
            button_box.set_margin_bottom(12);
            button_box.set_margin_start(24);
            button_box.set_margin_end(24);

            let cancel_btn = gtk4::Button::with_label("Cancel");
            let start_btn = gtk4::Button::with_label("Start");
            start_btn.add_css_class("suggested-action");

            button_box.append(&cancel_btn);
            button_box.append(&start_btn);

            main_box.append(&content);
            main_box.append(&button_box);
            dialog.set_child(Some(&main_box));

            // Cancel button action
            let dialog_cancel = dialog.clone();
            cancel_btn.connect_clicked(move |_| {
                dialog_cancel.close();
            });

            let state = crate::app::AppState::load();
            if !state.base_url.is_empty() && !state.password.is_empty() {
                let rx = crate::utils::run_async_to_main(async move {
                    let client = crate::api::client::ApiClient::new();
                    client.contacts(&state.base_url, &state.password).await
                });
                let dropdown_clone = dropdown.clone();
                rx.attach(None, move |res| {
                    if let Ok(contacts) = res {
                        let strings: Vec<String> = contacts.iter().map(|c| c.label.clone()).collect();
                        dropdown_clone.set_model(Some(&gtk4::StringList::new(strings.iter().map(|s| s.as_str()).collect::<Vec<_>>().as_slice())));
                    }
                    glib::ControlFlow::Continue
                });
            }

            let overlay2 = overlay.clone();
            let sidebar_for_response = sidebar_for_dialog.clone();
            let dialog_start = dialog.clone();
            start_btn.connect_clicked(move |_| {
                let mut addr = entry.text().to_string();
                if addr.trim().is_empty() {
                    if let Some(model) = dropdown.model() {
                        let pos = dropdown.selected();
                        if let Some(item) = model.item(pos) {
                                if let Ok(str_item) = item.downcast::<gtk4::StringObject>() {
                                    addr = str_item.string().to_string();
                                    if let Some(start) = addr.rfind('(') { if let Some(end) = addr.rfind(')') { if end > start { addr = addr[start+1..end].to_string(); }}}
                                }
                            }
                    }
                }
                let addr = addr.trim().to_string();
                if addr.is_empty() {
                    overlay2.add_toast(adw::Toast::new("Please enter a number/email or select a contact."));
                    return;
                }

                let state = crate::app::AppState::load();
                if state.base_url.is_empty() || state.password.is_empty() { return; }
                let overlay3 = overlay2.clone();
                let sidebar_for_update = sidebar_for_response.clone();
                let rx = crate::utils::run_async_to_main(async move {
                    let client = crate::api::client::ApiClient::new();
                    match client.create_chat(&state.base_url, &state.password, vec![addr], None).await {
                        Ok(conv) => {
                            let _ = crate::storage::upsert_chats(&[conv.clone()], None);
                            Ok(conv)
                        }
                        Err(e) => Err(e),
                    }
                });

                rx.attach(None, move |res| {
                    match res {
                        Ok(conv) => {
                            if let Ok(list) = crate::storage::get_chats(Some(200)) {
                                sidebar_for_update.set_items(list);
                            } else {
                                sidebar_for_update.set_items(vec![conv]);
                            }
                        }
                        Err(err) => {
                            overlay3.add_toast(adw::Toast::new(&format!("Failed to create chat: {}", err)));
                        }
                    }
                    glib::ControlFlow::Continue
                });
                
                dialog_start.close();
            });

            dialog.present();
        });
    }
}
