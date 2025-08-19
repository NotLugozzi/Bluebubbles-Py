"""
New Chat Dialog
Dialog for creating new chats with existing contacts or new phone numbers/email addresses
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib
import asyncio
import threading
from ..api.client import BlueBubblesClient, BlueBubblesAPIError


class NewChatDialog(Adw.Dialog):
    """Dialog for creating new chats."""
    
    def __init__(self, parent_window, config_manager):
        super().__init__()
        
        self.parent_window = parent_window
        self.config_manager = config_manager
        self.contacts = []
        
        self.set_title("New Chat")
        self.set_content_width(400)
        self.set_content_height(300)
        
        self.setup_ui()
        self.load_contacts()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        # Main content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        
        # Title and description
        title_label = Gtk.Label()
        title_label.set_markup("<b>Start a New Chat</b>")
        title_label.set_halign(Gtk.Align.START)
        content_box.append(title_label)
        
        description_label = Gtk.Label()
        description_label.set_text("Select a contact and enter a message to start a new conversation")
        description_label.set_halign(Gtk.Align.START)
        description_label.add_css_class("dim-label")
        content_box.append(description_label)
        
        # Contact/Address entry with dropdown
        entry_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        
        entry_label = Gtk.Label()
        entry_label.set_text("Contact or Address:")
        entry_label.set_halign(Gtk.Align.START)
        entry_box.append(entry_label)
        
        # Create a dropdown that can also accept text input
        self.contact_entry = Gtk.Entry()
        self.contact_entry.set_placeholder_text("Enter phone number, email, or select contact...")
        self.contact_entry.set_hexpand(True)
        entry_box.append(self.contact_entry)
        
        # Dropdown for existing contacts
        self.contacts_dropdown = Gtk.DropDown()
        self.contacts_dropdown.set_hexpand(True)
        
        # Create string list for contacts
        self.contacts_model = Gtk.StringList()
        self.contacts_dropdown.set_model(self.contacts_model)
        
        # Connect dropdown selection to entry
        self.contacts_dropdown.connect("notify::selected-item", self.on_contact_selected)
        
        dropdown_label = Gtk.Label()
        dropdown_label.set_text("Or select from existing contacts:")
        dropdown_label.set_halign(Gtk.Align.START)
        dropdown_label.set_margin_top(12)
        entry_box.append(dropdown_label)
        entry_box.append(self.contacts_dropdown)
        
        content_box.append(entry_box)
        
        # Message entry
        message_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        message_box.set_margin_top(12)
        
        message_label = Gtk.Label()
        message_label.set_text("Initial Message:")
        message_label.set_halign(Gtk.Align.START)
        message_box.append(message_label)
        
        self.message_entry = Gtk.Entry()
        self.message_entry.set_placeholder_text("Enter a message to start the conversation...")
        self.message_entry.set_hexpand(True)
        message_box.append(self.message_entry)
        
        content_box.append(message_box)
        
        # Add some vertical space
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        content_box.append(spacer)
        
        # Button box
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.END)
        
        # Cancel button
        cancel_button = Gtk.Button()
        cancel_button.set_label("Cancel")
        cancel_button.connect("clicked", self.on_cancel_clicked)
        button_box.append(cancel_button)
        
        # Create button
        self.create_button = Gtk.Button()
        self.create_button.set_label("Create Chat")
        self.create_button.add_css_class("suggested-action")
        self.create_button.connect("clicked", self.on_create_clicked)
        self.create_button.set_sensitive(False)  # Initially disabled
        button_box.append(self.create_button)
        
        content_box.append(button_box)
        
        # Connect entry text changes to validate input
        self.contact_entry.connect("changed", self.on_entry_changed)
        self.message_entry.connect("changed", self.on_entry_changed)
        
        self.set_child(content_box)
    
    def on_contact_selected(self, dropdown, param):
        """Handle contact selection from dropdown."""
        selected_item = dropdown.get_selected_item()
        if selected_item:
            contact_text = selected_item.get_string()
            if contact_text != "Loading contacts...":
                # Extract the address from the contact text
                # Format is usually "Name - address" or just "address"
                if " - " in contact_text:
                    address = contact_text.split(" - ")[-1]
                else:
                    address = contact_text
                
                self.contact_entry.set_text(address)
    
    def on_entry_changed(self, entry):
        """Handle entry text changes to validate input."""
        contact_text = self.contact_entry.get_text().strip()
        message_text = self.message_entry.get_text().strip()
        # Enable create button if both fields have text
        self.create_button.set_sensitive(len(contact_text) > 0 and len(message_text) > 0)
    
    def on_cancel_clicked(self, button):
        """Handle cancel button click."""
        self.close()
    
    def on_create_clicked(self, button):
        """Handle create button click."""
        address = self.contact_entry.get_text().strip()
        message = self.message_entry.get_text().strip()
        
        if not address:
            self.show_error("Please enter a phone number or email address")
            return
        
        if not message:
            self.show_error("Please enter a message to start the conversation")
            return
        
        # Disable the button while creating
        self.create_button.set_sensitive(False)
        self.create_button.set_label("Creating...")
        
        # Create the chat
        self.create_chat(address, message)
    
    def show_error(self, message):
        """Show an error message."""
        if hasattr(self.parent_window, 'show_toast'):
            self.parent_window.show_toast(message)
    
    def load_contacts(self):
        """Load existing contacts from the server."""
        # Add placeholder while loading
        self.contacts_model.append("Loading contacts...")
        
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.load_contacts_async())
                loop.close()
            except Exception as e:
                def show_error():
                    self.contacts_model.remove(0)  # Remove "Loading..." item
                    self.contacts_model.append("Failed to load contacts")
                GLib.idle_add(show_error)
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    async def load_contacts_async(self):
        """Load contacts asynchronously."""
        config = self.config_manager.get_server_config()
        if not config['url'] or not config['password']:
            def update_ui():
                self.contacts_model.remove(0)  # Remove "Loading..." item
                self.contacts_model.append("No server configuration")
            GLib.idle_add(update_ui)
            return
        
        try:
            api_method = self.application.config_manager.get_api_method()
            async with BlueBubblesClient(config['url'], config['password'], api_method) as client:
                # Get chats to extract contacts
                chats = await client.get_chats(limit=200, with_data=['participants'])
                
                # Extract unique handles/addresses
                addresses = set()
                for chat in chats:
                    participants = chat.get('participants', [])
                    for participant in participants:
                        address = participant.get('address')
                        if address:
                            addresses.add(address)
                
                # Sort addresses
                sorted_addresses = sorted(list(addresses))
                
                def update_ui():
                    # Clear the model
                    while self.contacts_model.get_n_items() > 0:
                        self.contacts_model.remove(0)
                    
                    # Add contacts
                    if sorted_addresses:
                        for address in sorted_addresses:
                            self.contacts_model.append(address)
                    else:
                        self.contacts_model.append("No contacts found")
                
                GLib.idle_add(update_ui)
        
        except Exception as e:
            def update_ui():
                # Clear the model
                while self.contacts_model.get_n_items() > 0:
                    self.contacts_model.remove(0)
                self.contacts_model.append("Failed to load contacts")
            GLib.idle_add(update_ui)
    
    def create_chat(self, address, message):
        """Create a new chat with the specified address and message."""
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.create_chat_async(address, message))
                loop.close()
            except Exception as e:
                error_message = f"Failed to create chat: {str(e)}"
                def show_error():
                    self.create_button.set_sensitive(True)
                    self.create_button.set_label("Create Chat")
                    self.show_error(error_message)
                GLib.idle_add(show_error)
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    async def create_chat_async(self, address, message):
        """Create chat asynchronously."""
        config = self.config_manager.get_server_config()
        if not config['url'] or not config['password']:
            def show_error():
                self.create_button.set_sensitive(True)
                self.create_button.set_label("Create Chat")
                self.show_error("No server configuration found")
            GLib.idle_add(show_error)
            return
        
        try:
            api_method = self.application.config_manager.get_api_method()
            async with BlueBubblesClient(config['url'], config['password'], api_method) as client:
                # Create the chat
                result = await client.create_chat([address], message=message)
                
                def on_success():
                    if hasattr(self.parent_window, 'show_toast'):
                        self.parent_window.show_toast("Chat created successfully!")
                    
                    # Refresh the chat list if the method exists
                    if hasattr(self.parent_window, 'refresh_chat_list'):
                        self.parent_window.refresh_chat_list()
                    
                    self.close()
                
                GLib.idle_add(on_success)
        
        except BlueBubblesAPIError as e:
            error_message = f"Failed to create chat: {str(e)}"
            def show_error():
                self.create_button.set_sensitive(True)
                self.create_button.set_label("Create Chat")
                self.show_error(error_message)
            GLib.idle_add(show_error)
        
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"
            def show_error():
                self.create_button.set_sensitive(True)
                self.create_button.set_label("Create Chat")
                self.show_error(error_message)
            GLib.idle_add(show_error)
