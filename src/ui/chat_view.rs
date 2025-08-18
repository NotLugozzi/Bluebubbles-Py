use gtk4::prelude::*;
use gtk4 as gtk;

pub struct ChatView;

impl ChatView {
    pub fn new() -> gtk::Widget {
        let root = gtk::Box::new(gtk::Orientation::Vertical, 6);
    root.set_margin_top(8);
    root.set_margin_bottom(8);
    root.set_margin_start(8);
    root.set_margin_end(8);

        let scroller = gtk::ScrolledWindow::builder()
            .vexpand(true)
            .hexpand(true)
            .build();
        let messages_box = gtk::Box::new(gtk::Orientation::Vertical, 6);
        for line in [
            "Welcome to BlueBubbles",
            "This is a placeholder chat view.",
            "Messages will appear here.",
        ] {
            let lbl = gtk::Label::new(Some(line));
            lbl.set_halign(gtk::Align::Start);
            messages_box.append(&lbl);
        }
        scroller.set_child(Some(&messages_box));
        root.append(&scroller);

        // Input row
        let input_row = gtk::Box::new(gtk::Orientation::Horizontal, 6);
        let entry = gtk::Entry::new();
        entry.set_hexpand(true);
        entry.set_placeholder_text(Some("Type a message…"));
        let send_btn = gtk::Button::with_label("Send");
        input_row.append(&entry);
        input_row.append(&send_btn);
        root.append(&input_row);

        // Send actions
        {
            use std::rc::Rc;
            let entry_for_send = entry.clone();
            let messages_box_for_send = messages_box.clone();
            let scroller_for_send = scroller.clone();
            let send: Rc<dyn Fn()> = Rc::new(move || {
                if entry_for_send.text().is_empty() {
                    return;
                }
                let text = entry_for_send.text().to_string();
                eprintln!("Send clicked: {text}");
                let lbl = gtk::Label::new(Some(&text));
                lbl.set_halign(gtk::Align::End);
                messages_box_for_send.append(&lbl);
                entry_for_send.set_text("");
                let adj = scroller_for_send.vadjustment();
                adj.set_value(adj.upper());
            });
            {
                let send = send.clone();
                send_btn.connect_clicked(move |_| (send)());
            }
            {
                let send = send.clone();
                let entry_for_activate = entry.clone();
                entry_for_activate.connect_activate(move |_| (send)());
            }
        }

        root.upcast()
    }
}
