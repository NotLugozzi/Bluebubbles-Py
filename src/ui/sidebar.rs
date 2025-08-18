use gtk4::prelude::*;
use gtk4 as gtk;

pub struct Sidebar {
    root: gtk::Box,
    list: gtk::ListBox,
}

impl Sidebar {
    pub fn new() -> Self {
        let root = gtk::Box::new(gtk::Orientation::Vertical, 6);
        root.set_margin_top(8);
        root.set_margin_bottom(8);
        root.set_margin_start(8);
        root.set_margin_end(8);

        let title = gtk::Label::new(Some("Conversations"));
        title.add_css_class("heading");
        title.set_halign(gtk::Align::Start);
        root.append(&title);

        let list = gtk::ListBox::new();
        root.append(&list);

        Self { root, list }
    }

    pub fn widget(&self) -> gtk::Widget {
        self.root.clone().upcast()
    }

    pub fn set_items(&self, items: Vec<crate::api::models::Conversation>) {
        while let Some(child) = self.list.first_child() {
            self.list.remove(&child);
        }
        for conv in items {
            let row = gtk::ListBoxRow::new();
            let label = gtk::Label::new(Some(&conv.name));
            label.set_margin_top(8);
            label.set_margin_bottom(8);
            label.set_margin_start(8);
            label.set_margin_end(8);
            label.set_halign(gtk::Align::Start);
            row.set_child(Some(&label));
            self.list.append(&row);
        }
    }
}
