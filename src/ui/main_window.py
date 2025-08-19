"""
Main Window
The primary application window that displays chats and messages
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio, GObject, Gdk
import asyncio
import threading
import os
from datetime import datetime
from pathlib import Path
from ..api.client import BlueBubblesClient, BlueBubblesAPIError
from ..db.models import ChatRecord
from .new_chat_dialog import NewChatDialog

class MainWindow(Adw.ApplicationWindow):
    """Main application window."""
    
    def __init__(self, application):
        super().__init__(application=application)
        
        self.set_title("BlueBubbles")
        self.set_default_size(1200, 800)
        
        # Store reference to config manager and chat service
        self.config_manager = application.config_manager
        self.chat_service = application.get_chat_service()
        
        # Store chat data
        self.chats = []
        self.current_chat = None
        
        # Typing indicator state
        self.typing_timeout_id = None
        self.is_typing = False
        
        # Connect to window destroy signal for cleanup
        self.connect("destroy", self.on_window_destroy)
        
        # Build UI
        self.setup_ui()
        self.load_styles()
        
        # Load data
        self.load_server_info()
        self.load_chats()
        
        # Start background message checking
        self.start_message_monitoring()
    
    def load_styles(self):
        """Load custom CSS styles for this window."""
        try:
            css_provider = Gtk.CssProvider()
            css_path = Path(__file__).parent / 'styles.css'
            css_provider.load_from_path(str(css_path))
            
            # Apply to this window's display
            display = self.get_display()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
        except Exception as e:
            pass  # Silently handle CSS loading errors
    
    def load_image_from_data(self, image_data: bytes, size: int = 40) -> Gtk.Image:
        """Load image data into a Gtk.Image widget."""
        try:
            # Create a GBytes object from the image data
            gbytes = GLib.Bytes.new(image_data)
            
            # Create a texture from the bytes
            texture = Gdk.Texture.new_from_bytes(gbytes)
            
            # Create the image widget
            image = Gtk.Image.new_from_paintable(texture)
            image.set_pixel_size(size)
            image.add_css_class("circular")
            
            return image
        except Exception as e:
            # Fallback to default icon on error
            image = Gtk.Image()
            image.set_from_icon_name("person-symbolic")
            image.set_pixel_size(size)
            image.add_css_class("circular")
            return image
    
    def setup_ui(self):
        """Set up the user interface."""
        # Create main content area with toast overlay
        content = Adw.ToastOverlay()
        
        # Create a toolbar view to properly handle the header bar
        toolbar_view = Adw.ToolbarView()
        
        # Create header bar
        header_bar = Adw.HeaderBar()
        
        # Add menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_child(Gtk.Image.new_from_icon_name("open-menu-symbolic"))
        menu_button.set_menu_model(self.create_menu())
        header_bar.pack_end(menu_button)
        
        toolbar_view.add_top_bar(header_bar)
        content.set_child(toolbar_view)
        self.set_content(content)
        
        # Create split view for chat list and messages
        self.split_view = Adw.NavigationSplitView()
        self.split_view.set_sidebar_width_fraction(0.3)
        
        # Sidebar (chat list)
        sidebar_page = Adw.NavigationPage()
        sidebar_page.set_title("Chats")
        
        # Create main sidebar container
        sidebar_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        # Chat list in scrolled window
        sidebar_content = Gtk.ScrolledWindow()
        sidebar_content.set_vexpand(True)
        self.chat_list = Gtk.ListBox()
        self.chat_list.add_css_class("navigation-sidebar")
        self.chat_list.connect("row-selected", self.on_chat_selected)
        sidebar_content.set_child(self.chat_list)
        sidebar_container.append(sidebar_content)
        
        # New chat button at the bottom
        new_chat_button = Gtk.Button()
        new_chat_button.set_label("New Chat")
        new_chat_button.set_margin_start(12)
        new_chat_button.set_margin_end(12)
        new_chat_button.set_margin_top(6)
        new_chat_button.set_margin_bottom(12)
        new_chat_button.add_css_class("suggested-action")
        new_chat_button.set_icon_name("list-add-symbolic")
        new_chat_button.connect("clicked", self.on_new_chat_clicked)
        sidebar_container.append(new_chat_button)
        
        sidebar_page.set_child(sidebar_container)
        self.split_view.set_sidebar(sidebar_page)
        
        # Content area (messages)
        content_page = Adw.NavigationPage()
        content_page.set_title("Messages")
        
        # Placeholder content
        self.content_stack = Gtk.Stack()
        
        # Placeholder when no chat is selected
        placeholder = Adw.StatusPage()
        placeholder.set_icon_name("mail-send-symbolic")
        placeholder.set_title("Welcome to BlueBubbles")
        placeholder.set_description("Select a chat to start messaging")
        self.content_stack.add_named(placeholder, "placeholder")
        
        # Chat view (will be created when a chat is selected)
        self.content_stack.set_visible_child_name("placeholder")
        
        content_page.set_child(self.content_stack)
        self.split_view.set_content(content_page)
        
        # Set the split view as the content of the toolbar view
        toolbar_view.set_content(self.split_view)
        self.toast_overlay = content
    
    def create_menu(self):
        """Create the application menu."""
        menu = Gio.Menu()
        
        # Preferences item
        menu.append("Preferences", "app.preferences")
        
        # Separator
        menu.append_section(None, Gio.Menu())
        
        # About item
        about_item = Gio.Menu()
        about_item.append("About BlueBubbles", "app.about")
        menu.append_section(None, about_item)
        
        # Quit item
        quit_item = Gio.Menu()
        quit_item.append("Quit", "app.quit")
        menu.append_section(None, quit_item)
        
        return menu
    
    def show_toast(self, message: str, timeout: int = 3):
        """Show a toast notification."""
        toast = Adw.Toast()
        toast.set_title(message)
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)
    
    def on_new_chat_clicked(self, button):
        """Handle new chat button click."""
        dialog = NewChatDialog(self, self.config_manager)
        dialog.present(self)
    
    def refresh_chat_list(self):
        """Refresh the chat list."""
        self.load_chats(force_refresh=True)
    
    def load_chats(self, force_refresh: bool = False):
        """Load chats from cache or server."""
        config = self.get_application().config_manager.get_server_config()
        if not config['url'] or not config['password']:
            return
        
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                if force_refresh:
                    # Fetch from server
                    loop.run_until_complete(
                        self.load_chats_from_server_async(config['url'], config['password'])
                    )
                else:
                    # Try cache first, fallback to server
                    loop.run_until_complete(
                        self.load_chats_async(config['url'], config['password'])
                    )
                
                loop.close()
            except Exception as e:
                def show_error():
                    self.show_toast(f"Failed to load chats: {str(e)}")
                GLib.idle_add(show_error)
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    async def load_chats_async(self, server_url: str, password: str):
        """Load chats, preferring cache but falling back to server."""
        try:
            # First try to load from cache
            cached_chats = self.chat_service.get_cached_chats(limit=100)
            
            if cached_chats:
                # Update UI with cached chats
                def update_ui():
                    self.chats = cached_chats
                    self.populate_chat_list()
                
                GLib.idle_add(update_ui)
                
                # Optionally sync in background
                try:
                    updated_chats = await self.chat_service.sync_chats_from_server(
                        server_url, password, limit=100
                    )
                    
                    # Update UI if we got different data
                    if len(updated_chats) != len(cached_chats):
                        def update_ui_again():
                            self.chats = updated_chats
                            self.populate_chat_list()
                        
                        GLib.idle_add(update_ui_again)
                        
                except Exception as sync_error:
                    pass  # Silently handle background sync errors
            else:
                # No cache, fetch from server
                await self.load_chats_from_server_async(server_url, password)
                
        except Exception as e:
            def show_error():
                self.show_toast(f"Failed to load chats: {str(e)}")
            
            GLib.idle_add(show_error)
    
    async def load_chats_from_server_async(self, server_url: str, password: str):
        """Load chats from server and update UI."""
        try:
            chats = await self.chat_service.sync_chats_from_server(
                server_url, password, limit=100
            )
            
            def update_ui():
                self.chats = chats
                self.populate_chat_list()
                if chats:
                    self.show_toast(f"Loaded {len(chats)} chats")
                else:
                    self.show_toast("No chats found")
            
            GLib.idle_add(update_ui)
            
        except Exception as e:
            def show_error():
                self.show_toast(f"Failed to load chats from server: {str(e)}")
            
            GLib.idle_add(show_error)
    
    def populate_chat_list(self):
        """Populate the chat list with chat data."""
        # Clear existing items
        while True:
            row = self.chat_list.get_first_child()
            if row is None:
                break
            self.chat_list.remove(row)
        
        # Add chat items
        for chat in self.chats:
            chat_row = self.create_chat_row(chat)
            self.chat_list.append(chat_row)
    
    def create_chat_row(self, chat: ChatRecord) -> Gtk.ListBoxRow:
        """Create a chat list row."""
        row = Gtk.ListBoxRow()
        # Store chat data as an attribute instead of using set_data
        row.chat = chat
        
        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(8)
        main_box.set_margin_bottom(8)
        
        # Avatar (will be loaded asynchronously)
        avatar = Gtk.Image()
        if chat.is_group_chat:
            avatar.set_from_icon_name("group-symbolic")
        else:
            avatar.set_from_icon_name("person-symbolic")
        avatar.add_css_class("circular")
        avatar.set_pixel_size(40)
        main_box.append(avatar)
        
        # Load avatar asynchronously
        self.load_chat_avatar_async(avatar, chat)
        
        # Content area
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        content_box.set_hexpand(True)
        
        # Title and timestamp row
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Chat title
        title_label = Gtk.Label()
        title_label.set_text(chat.display_title)
        title_label.set_halign(Gtk.Align.START)
        title_label.set_hexpand(True)
        title_label.set_ellipsize(3)  # ELLIPSIZE_END
        title_label.add_css_class("heading")
        title_row.append(title_label)
        
        # Timestamp
        if chat.last_message_date:
            time_label = Gtk.Label()
            time_str = self.format_message_time(chat.last_message_datetime)
            time_label.set_text(time_str)
            time_label.add_css_class("dim-label")
            time_label.add_css_class("caption")
            title_row.append(time_label)
        
        content_box.append(title_row)
        
        # Last message preview
        if chat.last_message_text:
            preview_label = Gtk.Label()
            preview_text = chat.last_message_text
            if len(preview_text) > 60:
                preview_text = preview_text[:60] + "..."
            
            # Add sender info for group chats
            if chat.is_group_chat and chat.last_message_address and not chat.last_message_from_me:
                sender = chat.last_message_address.split('@')[0]  # Simple name extraction
                preview_text = f"{sender}: {preview_text}"
            elif chat.last_message_from_me:
                preview_text = f"You: {preview_text}"
            
            preview_label.set_text(preview_text)
            preview_label.set_halign(Gtk.Align.START)
            preview_label.set_ellipsize(3)  # ELLIPSIZE_END
            preview_label.add_css_class("dim-label")
            content_box.append(preview_label)
        
        main_box.append(content_box)
        row.set_child(main_box)
        
        return row
    
    def format_message_time(self, dt: datetime) -> str:
        """Format message timestamp for display."""
        if not dt:
            return ""
        
        now = datetime.now()
        diff = now - dt
        
        if diff.days == 0:
            # Today - show time
            return dt.strftime("%H:%M")
        elif diff.days == 1:
            # Yesterday
            return "Yesterday"
        elif diff.days < 7:
            # This week - show day name
            return dt.strftime("%A")
        else:
            # Older - show date
            return dt.strftime("%m/%d/%y")
    
    def get_message_receipt_status(self, message):
        """Get the read receipt status for a message. Returns (status_text, css_class)."""
        if not message.is_from_me:
            return "", ""  # Only show receipts for sent messages
        
        if message.date_read:
            # Message has been read - use double checkmark
            return "✓✓ Read", "read"
        elif message.date_delivered:
            # Message has been delivered but not read - use single checkmark
            return "✓ Delivered", "delivered"
        else:
            # Message is still sending or failed - use clock icon
            return "🕒 Sending...", "sending"
    
    def on_chat_selected(self, list_box, row):
        """Handle chat selection."""
        if row is None:
            return
        
        chat = getattr(row, 'chat', None)
        if chat:
            self.current_chat = chat
            self.load_chat_view(chat)
            # Mark chat as read when opened
            self.mark_chat_read_async(chat.guid)
    
    def load_chat_view(self, chat: ChatRecord):
        """Load the chat view for the selected chat."""
        chat_view_name = f"chat_{chat.guid}"
        
        # Check if chat view already exists
        existing_view = self.content_stack.get_child_by_name(chat_view_name)
        if existing_view:
            # print(f"🎯 Chat view already exists, switching to: {chat_view_name}")
            self.content_stack.set_visible_child_name(chat_view_name)
            return
        
        # print(f"🎯 Creating new chat view: {chat_view_name}")
        
        # Create a simple chat view for now
        chat_view = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        # Chat title area (not a header bar)
        title_area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_area.set_margin_start(12)
        title_area.set_margin_end(12)
        title_area.set_margin_top(8)
        title_area.set_margin_bottom(8)
        title_area.add_css_class("chat-title-area")
        
        title_label = Gtk.Label()
        title_label.set_text(chat.display_title)
        title_label.set_hexpand(True)
        title_label.set_halign(Gtk.Align.START)
        title_label.add_css_class("title-2")
        title_area.append(title_label)
        
        chat_view.append(title_area)
        
        # Messages area (placeholder for now)
        messages_area = Gtk.ScrolledWindow()
        messages_area.set_vexpand(True)
        
        # Simple message display
        messages_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        messages_box.set_margin_start(12)
        messages_box.set_margin_end(12)
        messages_box.set_margin_top(12)
        messages_box.set_margin_bottom(12)
        
        # Store references for auto-scrolling
        chat_view.messages_area = messages_area
        chat_view.messages_box = messages_box
        
        # Load recent messages
        self.load_chat_messages(chat, messages_box, messages_area)
        
        messages_area.set_child(messages_box)
        chat_view.append(messages_area)
        
        # Message input area with attachment support
        input_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        input_container.set_margin_start(12)
        input_container.set_margin_end(12)
        input_container.set_margin_top(8)
        input_container.set_margin_bottom(12)
        
        # Main input row
        input_area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Attachment button
        attachment_button = Gtk.Button()
        attachment_button.set_icon_name("document-edit-symbolic")
        attachment_button.set_tooltip_text("Attach image")
        attachment_button.add_css_class("flat")
        attachment_button.connect("clicked", self.on_attachment_clicked)
        input_area.append(attachment_button)
        
        # Message entry
        message_entry = Gtk.Entry()
        message_entry.set_placeholder_text("Type a message...")
        message_entry.set_hexpand(True)
        message_entry.connect("changed", self.on_message_entry_changed)
        message_entry.connect("activate", self.on_send_message)
        input_area.append(message_entry)
        
        # Send button
        send_button = Gtk.Button()
        send_button.set_icon_name("send-symbolic")
        send_button.add_css_class("suggested-action")
        send_button.connect("clicked", self.on_send_message)
        input_area.append(send_button)
        
        # Store references for later use
        input_area.message_entry = message_entry
        input_area.send_button = send_button
        input_area.attachment_button = attachment_button
        chat_view.input_area = input_area
        
        input_container.append(input_area)
        chat_view.append(input_container)
        
        # Add to stack
        self.content_stack.add_named(chat_view, f"chat_{chat.guid}")
        self.content_stack.set_visible_child_name(f"chat_{chat.guid}")
    
    def load_chat_messages(self, chat: ChatRecord, messages_box: Gtk.Box, messages_area: Gtk.ScrolledWindow = None):
        """Load messages for a chat."""
        # Get cached messages first
        messages = self.chat_service.get_cached_chat_messages(chat.guid, limit=50)
        
        if not messages:
            # No cached messages, show loading and fetch from server
            loading_label = Gtk.Label()
            loading_label.set_text("Loading messages...")
            loading_label.add_css_class("dim-label")
            messages_box.append(loading_label)
            
            # Load from server in background
            config = self.get_application().config_manager.get_server_config()
            if config['url'] and config['password']:
                def run_async():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(
                            self.load_messages_from_server_async(
                                config['url'], config['password'], chat.guid, messages_box, messages_area
                            )
                        )
                        loop.close()
                    except Exception as e:
                        def show_error():
                            # Remove loading label
                            messages_box.remove(loading_label)
                            error_label = Gtk.Label()
                            error_label.set_text(f"Failed to load messages: {str(e)}")
                            error_label.add_css_class("error")
                            messages_box.append(error_label)
                        GLib.idle_add(show_error)
                
                thread = threading.Thread(target=run_async, daemon=True)
                thread.start()
        else:
            # Display cached messages
            self.display_messages(messages, messages_box)
            # Auto-scroll to bottom after displaying messages
            if messages_area:
                GLib.idle_add(self.scroll_to_bottom, messages_area)
    
    async def load_messages_from_server_async(self, server_url: str, password: str, 
                                            chat_guid: str, messages_box: Gtk.Box, messages_area: Gtk.ScrolledWindow = None):
        """Load messages from server."""
        try:
            messages = await self.chat_service.sync_chat_messages(
                server_url, password, chat_guid, limit=50
            )
            
            def update_ui():
                # Clear loading message
                child = messages_box.get_first_child()
                if child:
                    messages_box.remove(child)
                
                # Display messages
                self.display_messages(messages, messages_box)
                # Auto-scroll to bottom after loading from server
                if messages_area:
                    GLib.idle_add(self.scroll_to_bottom, messages_area)
            
            GLib.idle_add(update_ui)
            
        except Exception as e:
            def show_error():
                # Remove any existing children
                while True:
                    child = messages_box.get_first_child()
                    if child is None:
                        break
                    messages_box.remove(child)
                
                error_label = Gtk.Label()
                error_label.set_text(f"Failed to load messages: {str(e)}")
                error_label.add_css_class("error")
                messages_box.append(error_label)
            
            GLib.idle_add(show_error)
    
    def scroll_to_bottom(self, scrolled_window: Gtk.ScrolledWindow):
        """Scroll to the bottom of a scrolled window."""
        try:
            vadjustment = scrolled_window.get_vadjustment()
            if vadjustment:
                vadjustment.set_value(vadjustment.get_upper() - vadjustment.get_page_size())
        except Exception as e:
            pass  # Silently handle scroll errors
    
    def display_messages(self, messages, messages_box: Gtk.Box):
        """Display messages in the messages box."""
        # Clear existing messages
        while True:
            child = messages_box.get_first_child()
            if child is None:
                break
            messages_box.remove(child)

        # Filter out reaction events; these are represented as badges on the parent message.
        filtered_messages = [m for m in messages if not self.is_reaction_event(m)]

        if not filtered_messages:
            no_messages_label = Gtk.Label()
            no_messages_label.set_text("No messages in this chat")
            no_messages_label.add_css_class("dim-label")
            messages_box.append(no_messages_label)
            return

        # Sort messages by date (newest last for natural reading order)
        sorted_messages = sorted(filtered_messages, key=lambda m: m.date_created)

        for message in sorted_messages:
            message_widget = self.create_message_widget(message)
            # Store the message GUID for future reference
            message_widget.message_guid = message.guid
            messages_box.append(message_widget)
    
    def create_message_widget(self, message) -> Gtk.Widget:
        """Create a widget for a message with reaction and context menu support."""
        # Main container
        message_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        message_box.set_margin_top(4)
        message_box.set_margin_bottom(4)
        
        # Content row
        content_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        if message.is_from_me:
            # Right-align for sent messages
            content_row.set_halign(Gtk.Align.END)
        else:
            # Left-align for received messages
            content_row.set_halign(Gtk.Align.START)
        
        # Message bubble with gesture support
        bubble_event_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        bubble_event_box.set_margin_start(8)
        bubble_event_box.set_margin_end(8)
        bubble_event_box.set_margin_top(4)
        bubble_event_box.set_margin_bottom(4)
        
        # Style the bubble
        if message.is_from_me:
            bubble_event_box.add_css_class("message-bubble-sent")
        else:
            bubble_event_box.add_css_class("message-bubble-received")
        
        # Add gesture controllers for reactions and context menu
        # Long press gesture for reactions (mobile-style)
        long_press = Gtk.GestureLongPress()
        long_press.set_delay_factor(1.0)  # Standard delay
        long_press.connect("pressed", self.on_message_long_press, message)
        bubble_event_box.add_controller(long_press)
        
        # Right-click gesture for context menu
        right_click = Gtk.GestureClick()
        right_click.set_button(3)  # Right mouse button
        right_click.connect("pressed", self.on_message_right_click, message)
        bubble_event_box.add_controller(right_click)
        
        # Message text
        if message.text:
            text_label = Gtk.Label()
            text_label.set_text(message.text)
            text_label.set_wrap(True)
            text_label.set_wrap_mode(2)  # WORD_CHAR
            text_label.set_max_width_chars(50)
            text_label.set_halign(Gtk.Align.START)
            text_label.set_selectable(True)
            bubble_event_box.append(text_label)
        
        # Attachments
        if hasattr(message, 'attachments') and message.attachments:
            print(f"DEBUG: Message has {len(message.attachments)} attachments")
            attachment_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            attachment_box.set_margin_top(4)
            
            for attachment in message.attachments:
                print(f"DEBUG: Processing attachment: {attachment}")
                attachment_widget = self.create_attachment_widget(attachment)
                attachment_box.append(attachment_widget)
            
            bubble_event_box.append(attachment_box)
        else:
            # Check the actual value of attachments
            if hasattr(message, 'attachments'):
                print(f"DEBUG: Message attachments value: {message.attachments} (type: {type(message.attachments)})")
        
        # Timestamp and sender info
        info_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        
        # Sender (for received messages in group chats)
        if not message.is_from_me and message.handle_address:
            sender_label = Gtk.Label()
            sender_name = message.handle_address.split('@')[0]  # Simple name extraction
            sender_label.set_text(sender_name)
            sender_label.add_css_class("caption")
            sender_label.add_css_class("dim-label")
            info_box.append(sender_label)
        
        # Timestamp
        time_label = Gtk.Label()
        time_str = self.format_message_time(message.datetime_created)
        time_label.set_text(time_str)
        time_label.add_css_class("caption")
        time_label.add_css_class("dim-label")
        info_box.append(time_label)
        
        # Read receipt indicators (only for sent messages)
        if message.is_from_me:
            receipt_label = Gtk.Label()
            receipt_status, receipt_class = self.get_message_receipt_status(message)
            if receipt_status:
                receipt_label.set_text(receipt_status)
                receipt_label.add_css_class("caption")
                receipt_label.add_css_class("read-receipt")
                if receipt_class:
                    receipt_label.add_css_class(receipt_class)
                receipt_label.set_margin_start(4)
                info_box.append(receipt_label)
        
        # Edit indicator
        if hasattr(message, 'is_edited') and message.is_edited:
            edit_label = Gtk.Label()
            edit_label.set_text("(edited)")
            edit_label.add_css_class("caption")
            edit_label.add_css_class("dim-label")
            info_box.append(edit_label)
        
        bubble_event_box.append(info_box)
        content_row.append(bubble_event_box)
        message_box.append(content_row)
        
        # Get and display reactions
        reactions = self.chat_service.get_message_reactions(message.guid)
        if reactions:
            reactions_widget = self.create_reactions_widget(reactions, message.is_from_me)
        else:
            # Keep a placeholder to simplify later updates
            reactions_widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            if message.is_from_me:
                reactions_widget.set_halign(Gtk.Align.END)
            else:
                reactions_widget.set_halign(Gtk.Align.START)
        # Store a reference so we can update badges later without rebuilding the whole message
        message_box.reactions_widget = reactions_widget
        message_box.append(reactions_widget)
        
        # Store message reference for gesture callbacks
        bubble_event_box.message = message
        
        return message_box
    
    def create_attachment_widget(self, attachment) -> Gtk.Widget:
        """Create a widget for displaying a message attachment."""
        attachment_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        attachment_container.set_margin_top(4)
        attachment_container.set_margin_bottom(4)
        
        # Get file info from metadata or original name
        file_name = attachment.get('original_roi') or attachment.get('transfer_name', 'Unknown File')
        file_size = attachment.get('total_bytes', 0)
        mime_type = attachment.get('mime_type', '')
        
        # Icon based on file type
        icon_widget = Gtk.Image()
        icon_widget.set_pixel_size(32)
        
        if mime_type.startswith('image/'):
            icon_widget.set_from_icon_name("image-x-generic")
            attachment_container.add_css_class("attachment-image")
        elif mime_type.startswith('video/'):
            icon_widget.set_from_icon_name("video-x-generic")
            attachment_container.add_css_class("attachment-video")
        elif mime_type.startswith('audio/'):
            icon_widget.set_from_icon_name("audio-x-generic")
            attachment_container.add_css_class("attachment-audio")
        elif 'pdf' in mime_type:
            icon_widget.set_from_icon_name("application-pdf")
            attachment_container.add_css_class("attachment-document")
        else:
            icon_widget.set_from_icon_name("text-x-generic")
            attachment_container.add_css_class("attachment-document")
        
        attachment_container.append(icon_widget)
        
        # File info
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        
        # File name
        name_label = Gtk.Label()
        name_label.set_text(file_name)
        name_label.set_halign(Gtk.Align.START)
        name_label.set_ellipsize(3)  # END
        name_label.set_max_width_chars(30)
        name_label.add_css_class("attachment-name")
        info_box.append(name_label)
        
        # File size
        if file_size > 0:
            size_label = Gtk.Label()
            size_str = self.format_file_size(file_size)
            size_label.set_text(size_str)
            size_label.set_halign(Gtk.Align.START)
            size_label.add_css_class("caption")
            size_label.add_css_class("dim-label")
            info_box.append(size_label)
        
        attachment_container.append(info_box)
        
        # Download button
        download_button = Gtk.Button()
        download_button.set_icon_name("document-save")
        download_button.set_tooltip_text("Download attachment")
        download_button.add_css_class("flat")
        download_button.connect("clicked", self.on_download_attachment, attachment)
        
        attachment_container.append(download_button)
        
        # Style the attachment container
        attachment_container.add_css_class("attachment-widget")
        
        return attachment_container
    
    def format_file_size(self, bytes_size: int) -> str:
        """Format file size in human readable format."""
        if bytes_size < 1024:
            return f"{bytes_size} B"
        elif bytes_size < 1024 * 1024:
            return f"{bytes_size / 1024:.1f} KB"
        elif bytes_size < 1024 * 1024 * 1024:
            return f"{bytes_size / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_size / (1024 * 1024 * 1024):.1f} GB"
    
    def on_download_attachment(self, button, attachment):
        """Handle attachment download button click."""
        # Run download in background to avoid blocking UI
        def download_async():
            try:
                file_path = self.chat_service.get_attachment(attachment['guid'])
                if file_path and os.path.exists(file_path):
                    # Open file manager to show the downloaded file
                    GLib.idle_add(self.show_download_complete, file_path)
                else:
                    GLib.idle_add(self.show_error_toast, "Failed to download attachment")
            except Exception as e:
                GLib.idle_add(self.show_error_toast, f"Download error: {str(e)}")
        
        threading.Thread(target=download_async, daemon=True).start()
    
    def show_download_complete(self, file_path: str):
        """Show a toast notification when download completes."""
        toast = Adw.Toast()
        toast.set_title(f"Downloaded to {os.path.dirname(file_path)}")
        toast.set_timeout(3)
        
        if hasattr(self, 'toast_overlay'):
            self.toast_overlay.add_toast(toast)
    
    def show_error_toast(self, message: str):
        """Show an error toast notification."""
        toast = Adw.Toast()
        toast.set_title(message)
        toast.set_timeout(5)
        
        if hasattr(self, 'toast_overlay'):
            self.toast_overlay.add_toast(toast)
    
    def create_reactions_widget(self, reactions, message_is_from_me) -> Gtk.Widget:
        """Create a widget to display reaction emojis."""
        reactions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        reactions_box.set_margin_start(16)
        reactions_box.set_margin_end(16)
        reactions_box.set_margin_top(2)
        reactions_box.set_margin_bottom(2)
        
        # Align reactions to match message alignment
        if message_is_from_me:
            reactions_box.set_halign(Gtk.Align.END)
        else:
            reactions_box.set_halign(Gtk.Align.START)
        
        # Group reactions by type and count them
        reaction_counts = {}
        for reaction in reactions:
            emoji = self.get_reaction_emoji(reaction.associated_message_type)
            if emoji:
                if emoji in reaction_counts:
                    reaction_counts[emoji] += 1
                else:
                    reaction_counts[emoji] = 1
        
        # Create emoji labels for each reaction type
        for emoji, count in reaction_counts.items():
            reaction_label = Gtk.Label()
            if count > 1:
                reaction_label.set_text(f"{emoji} {count}")
            else:
                reaction_label.set_text(emoji)
            
            reaction_label.add_css_class("reaction-emoji")
            reaction_label.set_margin_start(2)
            reaction_label.set_margin_end(2)
            reactions_box.append(reaction_label)
        
        return reactions_box
    
    def get_reaction_emoji(self, reaction_type: str) -> str:
        """Convert a reaction type to its corresponding emoji."""
        # Map BlueBubbles reaction types to emojis
        reaction_map = {
            "2000": "❤️",  # love
            "2001": "👍",  # like  
            "2002": "👎",  # dislike
            "2003": "😂",  # laugh
            "2004": "‼️",  # emphasis
            "2005": "❓",  # question
            # Alternative mappings based on common reaction names
            "love": "❤️",
            "like": "👍", 
            "dislike": "👎",
            "laugh": "😂",
            "emphasis": "‼️",
            "question": "❓"
        }
        
        if reaction_type:
            return reaction_map.get(reaction_type, "👍")  # Default to thumbs up
        return ""

    def is_reaction_event(self, message) -> bool:
        """Return True if this message is a reaction event (tapback), not a normal chat message."""
        try:
            return bool(message.associated_message_guid and message.associated_message_type)
        except Exception:
            return False
    
    def load_server_info(self):
        """Load server information and display in title."""
        config = self.get_application().config_manager.get_server_config()
        if config['url'] and config['password']:
            # Run the async function in a thread to avoid event loop issues
            def run_async():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.load_server_info_async(config['url'], config['password']))
                    loop.close()
                except Exception as e:
                    def show_error():
                        self.show_toast(f"Failed to load server info: {str(e)}")
                    GLib.idle_add(show_error)
            
            thread = threading.Thread(target=run_async, daemon=True)
            thread.start()
    
    def show_about_dialog(self):
        """Show the About BlueBubbles dialog with server and iMessage info."""
        # Run the async function in a thread to get the data
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.show_about_dialog_async())
                loop.close()
            except Exception as e:
                error_msg = str(e)
                def show_error():
                    self.show_toast(f"Failed to load server information: {error_msg}")
                GLib.idle_add(show_error)
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    async def show_about_dialog_async(self):
        """Load server information and show the about dialog."""
        config = self.get_application().config_manager.get_server_config()
        if not config['url'] or not config['password']:
            def show_error():
                self.show_toast("No server configuration found")
            GLib.idle_add(show_error)
            return
        
        try:
            api_method = self.get_application().config_manager.get_api_method()
            async with BlueBubblesClient(config['url'], config['password'], api_method) as client:
                # Fetch all the information
                server_info = await client.get_server_info()
                try:
                    icloud_info = await client.get_icloud_account_info()
                except BlueBubblesAPIError:
                    icloud_info = None  # iCloud info might not be available
                
                try:
                    statistics = await client.get_server_statistics()
                except BlueBubblesAPIError:
                    statistics = None  # Statistics might not be available
                
                def show_dialog():
                    self.create_about_dialog(server_info, icloud_info, statistics)
                
                GLib.idle_add(show_dialog)
        
        except Exception as e:
            error_msg = str(e)
            def show_error():
                self.show_toast(f"Failed to load server information: {error_msg}")
            GLib.idle_add(show_error)
    
    # New callback methods for the enhanced features
    
    def on_attachment_clicked(self, button):
        """Handle attachment button click to show file picker."""
        file_dialog = Gtk.FileDialog()
        file_dialog.set_title("Select Image")
        
        # Set up image filters
        filter_images = Gtk.FileFilter()
        filter_images.set_name("Images")
        filter_images.add_mime_type("image/jpeg")
        filter_images.add_mime_type("image/png")
        filter_images.add_mime_type("image/gif")
        filter_images.add_mime_type("image/webp")
        filter_images.add_mime_type("image/heic")
        
        filter_list = Gio.ListStore.new(Gtk.FileFilter)
        filter_list.append(filter_images)
        file_dialog.set_filters(filter_list)
        file_dialog.set_default_filter(filter_images)
        
        def on_file_selected(dialog, result):
            try:
                file = dialog.open_finish(result)
                if file:
                    file_path = file.get_path()
                    if file_path and self.current_chat:
                        self.send_attachment_async(file_path)
            except Exception as e:
                self.show_toast(f"Failed to select file: {e}")
        
        file_dialog.open(self, None, on_file_selected)
    
    def on_message_entry_changed(self, entry):
        """Handle message entry text changes for typing indicators."""
        if not self.current_chat:
            return
        
        text = entry.get_text()
        
        if text and not self.is_typing:
            # Start typing
            self.is_typing = True
            self.send_typing_indicator_async(True)
        
        # Reset the typing timeout
        if self.typing_timeout_id:
            GLib.source_remove(self.typing_timeout_id)
        
        def stop_typing():
            if self.is_typing:
                self.is_typing = False
                self.send_typing_indicator_async(False)
            self.typing_timeout_id = None
            return False
        
        # Stop typing after 3 seconds of inactivity
        self.typing_timeout_id = GLib.timeout_add(3000, stop_typing)
    
    def on_send_message(self, widget):
        """Handle send message button click or entry activation."""
        current_page = self.content_stack.get_visible_child()
        if not current_page or not self.current_chat:
            return
        
        input_area = getattr(current_page, 'input_area', None)
        if not input_area:
            return
        
        message_entry = getattr(input_area, 'message_entry', None)
        if not message_entry:
            return
        
        message_text = message_entry.get_text().strip()
        if not message_text:
            return
        
        # Clear the entry
        message_entry.set_text("")
        
        # Stop typing indicator
        if self.is_typing:
            self.is_typing = False
            self.send_typing_indicator_async(False)
        
        # Send the message
        self.send_message_async(message_text)
    
    def on_message_long_press(self, gesture, x, y, message):
        """Handle long press on message for reactions."""
        self.show_reaction_popover(gesture.get_widget(), message)
    
    def on_message_right_click(self, gesture, n_press, x, y, message):
        """Handle right click on message for context menu."""
        self.show_message_context_menu(gesture.get_widget(), message, x, y)
    
    def show_reaction_popover(self, widget, message):
        """Show reaction picker popover."""
        popover = Gtk.Popover()
        popover.set_parent(widget)
        popover.set_position(Gtk.PositionType.TOP)
        
        # Reaction buttons container
        reaction_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        reaction_box.set_margin_start(12)
        reaction_box.set_margin_end(12)
        reaction_box.set_margin_top(8)
        reaction_box.set_margin_bottom(8)
        
        # Common reactions
        reactions = [
            ("❤️", "love"),
            ("👍", "like"),
            ("👎", "dislike"),
            ("😂", "laugh"),
            ("‼️", "emphasis"),
            ("❓", "question")
        ]
        
        for emoji, reaction_type in reactions:
            button = Gtk.Button()
            button.set_label(emoji)
            button.add_css_class("flat")
            button.connect("clicked", self.on_reaction_selected, message, reaction_type, popover)
            reaction_box.append(button)
        
        # Remove reaction button if this is from me
        if message.is_from_me:
            separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
            reaction_box.append(separator)
            
            remove_button = Gtk.Button()
            remove_button.set_label("Remove")
            remove_button.add_css_class("flat")
            remove_button.connect("clicked", self.on_reaction_removed, message, popover)
            reaction_box.append(remove_button)
        
        popover.set_child(reaction_box)
        popover.popup()
    
    def show_message_context_menu(self, widget, message, x, y):
        """Show context menu for message operations."""
        popover = Gtk.Popover()
        popover.set_parent(widget)
        popover.set_position(Gtk.PositionType.TOP)
        
        # Menu items container
        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        menu_box.set_margin_start(8)
        menu_box.set_margin_end(8)
        menu_box.set_margin_top(8)
        menu_box.set_margin_bottom(8)
        
        # Copy text
        if message.text:
            copy_button = Gtk.Button()
            copy_button.set_label("Copy Text")
            copy_button.add_css_class("flat")
            copy_button.connect("clicked", self.on_copy_message, message, popover)
            menu_box.append(copy_button)
        
        # Only show edit/unsend for own messages
        if message.is_from_me:
            if message.text:  # Only allow editing text messages
                edit_button = Gtk.Button()
                edit_button.set_label("Edit Message")
                edit_button.add_css_class("flat")
                edit_button.connect("clicked", self.on_edit_message, message, popover)
                menu_box.append(edit_button)
            
            unsend_button = Gtk.Button()
            unsend_button.set_label("Unsend Message")
            unsend_button.add_css_class("flat")
            unsend_button.add_css_class("destructive-action")
            unsend_button.connect("clicked", self.on_unsend_message, message, popover)
            menu_box.append(unsend_button)
        
        popover.set_child(menu_box)
        popover.popup()
    
    def on_reaction_selected(self, button, message, reaction_type, popover):
        """Handle reaction selection."""
        popover.popdown()
        self.send_reaction_async(message.guid, reaction_type)
    
    def on_reaction_removed(self, button, message, popover):
        """Handle reaction removal."""
        popover.popdown()
        self.remove_reaction_async(message.guid)
    
    def on_copy_message(self, button, message, popover):
        """Handle copying message text."""
        popover.popdown()
        if message.text:
            clipboard = Gdk.Display.get_default().get_clipboard()
            clipboard.set(message.text)
            self.show_toast("Message copied to clipboard")
    
    def on_edit_message(self, button, message, popover):
        """Handle editing message."""
        popover.popdown()
        self.show_edit_dialog(message)
    
    def on_unsend_message(self, button, message, popover):
        """Handle unsending message."""
        popover.popdown()
        self.unsend_message_async(message.guid)
    
    def show_edit_dialog(self, message):
        """Show dialog to edit a message."""
        dialog = Adw.AlertDialog()
        dialog.set_heading("Edit Message")
        dialog.set_body("Enter the new message text:")
        
        # Create entry for new text
        entry = Gtk.Entry()
        entry.set_text(message.text or "")
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        entry.set_margin_top(12)
        entry.set_margin_bottom(12)
        
        # Add entry to dialog
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.append(entry)
        dialog.set_extra_child(content_box)
        
        # Add buttons
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")
        
        def on_response(dialog, response):
            if response == "save":
                new_text = entry.get_text().strip()
                if new_text and new_text != message.text:
                    self.edit_message_async(message.guid, new_text)
        
        dialog.connect("response", on_response)
        dialog.present(self)
    
    # Async helper methods
    
    def send_message_async(self, message_text: str):
        """Send a message asynchronously."""
        if not self.current_chat:
            return
        
        config = self.get_application().config_manager.get_server_config()
        if not config['url'] or not config['password']:
            self.show_toast("No server configuration")
            return
        
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(
                    self.chat_service.send_message(
                        config['url'], config['password'], 
                        self.current_chat.guid, message_text
                    )
                )
                loop.close()
                
                if success:
                    # Immediate refresh
                    GLib.idle_add(self.refresh_current_chat_messages)
                    
                    # Schedule additional refresh after 1 second to catch any delayed messages
                    def delayed_refresh():
                        # Force sync messages from server to get the latest
                        def sync_and_refresh():
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(
                                    self.chat_service.sync_chat_messages(
                                        config['url'], config['password'], 
                                        self.current_chat.guid, limit=50
                                    )
                                )
                                loop.close()
                                
                                # Refresh the message view
                                GLib.idle_add(self.refresh_current_chat_messages)
                            except Exception as e:
                                pass  # Silently handle delayed refresh errors
                        
                        # Run sync in thread to avoid blocking
                        import threading
                        thread = threading.Thread(target=sync_and_refresh, daemon=True)
                        thread.start()
                        return False  # Don't repeat the timeout
                    
                    # Schedule the delayed refresh for 1 second later
                    GLib.timeout_add_seconds(1, delayed_refresh)
                else:
                    GLib.idle_add(lambda: self.show_toast("Failed to send message"))
            except Exception as e:
                GLib.idle_add(lambda: self.show_toast(f"Error: {e}"))
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    def send_attachment_async(self, file_path: str):
        """Send an attachment asynchronously."""
        if not self.current_chat:
            return
        
        config = self.get_application().config_manager.get_server_config()
        if not config['url'] or not config['password']:
            self.show_toast("No server configuration")
            return
        
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(
                    self.chat_service.send_attachment(
                        config['url'], config['password'], 
                        self.current_chat.guid, file_path
                    )
                )
                loop.close()
                
                if success:
                    # Refresh the message view
                    GLib.idle_add(self.refresh_current_chat_messages)
                    GLib.idle_add(lambda: self.show_toast("Image sent"))
                else:
                    GLib.idle_add(lambda: self.show_toast("Failed to send image"))
            except Exception as e:
                GLib.idle_add(lambda: self.show_toast(f"Error: {e}"))
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    def send_typing_indicator_async(self, typing: bool):
        """Send typing indicator asynchronously."""
        if not self.current_chat:
            return
        
        config = self.get_application().config_manager.get_server_config()
        if not config['url'] or not config['password']:
            return
        
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    self.chat_service.send_typing_indicator(
                        config['url'], config['password'], 
                        self.current_chat.guid, typing
                    )
                )
                loop.close()
            except Exception as e:
                pass  # Silently handle typing indicator errors
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    def load_chat_avatar_async(self, image_widget: Gtk.Image, chat: ChatRecord):
        """Load chat avatar asynchronously."""
        config = self.get_application().config_manager.get_server_config()
        if not config['url'] or not config['password']:
            return
        
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                avatar_data = None
                
                if chat.is_group_chat:
                    # Try to get group chat icon
                    avatar_data = loop.run_until_complete(
                        self.chat_service.get_chat_icon(
                            config['url'], config['password'], chat.guid
                        )
                    )
                else:
                    # For individual chats, use the first participant's address
                    participants = chat.participants
                    if participants and len(participants) > 0:
                        # Find the participant that's not us
                        for participant in participants:
                            # participant is a HandleRecord, use its address
                            address = participant.address if hasattr(participant, 'address') else str(participant)
                            if '@' in address or address.startswith('+'):
                                avatar_data = loop.run_until_complete(
                                    self.chat_service.get_contact_avatar(
                                        config['url'], config['password'], address
                                    )
                                )
                                break
                
                # If no avatar data, try to generate initials fallback
                if not avatar_data:
                    fallback_name = chat.display_title or "Unknown"
                    avatar_data = self.chat_service.generate_fallback_avatar(fallback_name, 40)
                
                loop.close()
                
                # Update UI on main thread
                if avatar_data:
                    def update_avatar():
                        try:
                            # Check if the widget is still valid
                            if image_widget and not image_widget.get_parent() is None:
                                new_image = self.load_image_from_data(avatar_data, 40)
                                # Copy properties from new image to existing widget
                                paintable = new_image.get_paintable()
                                if paintable:
                                    image_widget.set_from_paintable(paintable)
                        except Exception as e:
                            pass  # Silently handle UI update errors
                        return False  # Remove from idle queue
                    
                    GLib.idle_add(update_avatar)
                
            except Exception as e:
                pass  # Silently handle avatar loading errors
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    def mark_chat_read_async(self, chat_guid: str):
        """Mark a chat as read asynchronously."""
        config = self.get_application().config_manager.get_server_config()
        if not config['url'] or not config['password']:
            return
        
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    self.chat_service.mark_chat_read(
                        config['url'], config['password'], chat_guid
                    )
                )
                loop.close()
            except Exception as e:
                pass  # Silently handle mark read errors
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    def send_reaction_async(self, message_guid: str, reaction_type: str):
        """Send a reaction asynchronously."""
        config = self.get_application().config_manager.get_server_config()
        if not config['url'] or not config['password']:
            self.show_toast("No server configuration")
            return
        
        # Get the current chat GUID
        chat_guid = self.current_chat.guid if self.current_chat else None
        # print(f"🎭 UI: Starting send reaction - guid={message_guid}, type={reaction_type}, chat_guid={chat_guid}")
        
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(
                    self.chat_service.send_reaction(
                        config['url'], config['password'], 
                        message_guid, reaction_type, chat_guid
                    )
                )
                loop.close()
                
                if success:
                    # print(f"✅ UI: Reaction sent successfully")
                    # Refresh messages to show the new reaction
                    GLib.idle_add(self.refresh_current_chat_messages)
                    GLib.idle_add(lambda: self.show_toast("Reaction sent"))
                else:
                    # print(f"❌ UI: Failed to send reaction")
                    GLib.idle_add(lambda: self.show_toast("Failed to send reaction"))
            except Exception as e:
                # print(f"❌ UI: Exception sending reaction: {e}")
                GLib.idle_add(lambda: self.show_toast(f"Error: {e}"))
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    def remove_reaction_async(self, message_guid: str):
        """Remove a reaction asynchronously."""
        config = self.get_application().config_manager.get_server_config()
        if not config['url'] or not config['password']:
            self.show_toast("No server configuration")
            return
        
        # Get the current chat GUID
        chat_guid = self.current_chat.guid if self.current_chat else None
        # print(f"🎭 UI: Starting remove reaction - guid={message_guid}, chat_guid={chat_guid}")
        
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(
                    self.chat_service.remove_reaction(
                        config['url'], config['password'], 
                        message_guid, chat_guid
                    )
                )
                loop.close()
                
                if success:
                    # print(f"✅ UI: Reaction removed successfully")
                    # Refresh messages to show the reaction removal
                    GLib.idle_add(self.refresh_current_chat_messages)
                    GLib.idle_add(lambda: self.show_toast("Reaction removed"))
                else:
                    # print(f"❌ UI: Failed to remove reaction")
                    GLib.idle_add(lambda: self.show_toast("Failed to remove reaction"))
            except Exception as e:
                # print(f"❌ UI: Exception removing reaction: {e}")
                GLib.idle_add(lambda: self.show_toast(f"Error: {e}"))
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    def edit_message_async(self, message_guid: str, new_text: str):
        """Edit a message asynchronously."""
        if not self.current_chat:
            return
        
        config = self.get_application().config_manager.get_server_config()
        if not config['url'] or not config['password']:
            self.show_toast("No server configuration")
            return
        
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(
                    self.chat_service.edit_message(
                        config['url'], config['password'], 
                        message_guid, new_text, self.current_chat.guid
                    )
                )
                loop.close()
                
                if success:
                    # Refresh the message view
                    GLib.idle_add(self.refresh_current_chat_messages)
                    GLib.idle_add(lambda: self.show_toast("Message edited"))
                else:
                    GLib.idle_add(lambda: self.show_toast("Failed to edit message"))
            except Exception as e:
                GLib.idle_add(lambda: self.show_toast(f"Error: {e}"))
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    def unsend_message_async(self, message_guid: str):
        """Unsend a message asynchronously."""
        if not self.current_chat:
            return
        
        config = self.get_application().config_manager.get_server_config()
        if not config['url'] or not config['password']:
            self.show_toast("No server configuration")
            return
        
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(
                    self.chat_service.unsend_message(
                        config['url'], config['password'], 
                        message_guid, self.current_chat.guid
                    )
                )
                loop.close()
                
                if success:
                    # Refresh the message view
                    GLib.idle_add(self.refresh_current_chat_messages)
                    GLib.idle_add(lambda: self.show_toast("Message unsent"))
                else:
                    GLib.idle_add(lambda: self.show_toast("Failed to unsend message"))
            except Exception as e:
                GLib.idle_add(lambda: self.show_toast(f"Error: {e}"))
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    def refresh_current_chat_messages(self):
        """Refresh messages for the current chat."""
        if not self.current_chat:
            return
        
        current_page = self.content_stack.get_visible_child()
        if not current_page:
            return
        
        messages_box = getattr(current_page, 'messages_box', None)
        messages_area = getattr(current_page, 'messages_area', None)
        
        if messages_box and messages_area:
            self.load_chat_messages(self.current_chat, messages_box, messages_area)
    
    def create_about_dialog(self, server_info: dict, icloud_info: dict = None, statistics: dict = None):
        """Create and show the about dialog with the fetched information."""
        dialog = Adw.AlertDialog()
        dialog.set_heading("About BlueBubbles")
        
        # Build the information text
        info_parts = []
        # Server Information
        info_parts.append("Server Information")
        info_parts.append(f"Server Version: {server_info.get('server_version', 'Unknown')}")
        info_parts.append(f"macOS Version: {server_info.get('os_version', 'Unknown')}")
        info_parts.append(f"Private API: {'✅ Enabled' if server_info.get('private_api', False) else '❌ Disabled'}")
        info_parts.append(f"Helper Connected: {'✅ Yes' if server_info.get('helper_connected', False) else '❌ No'}")
        if server_info.get('proxy_service'):
            info_parts.append(f"• Proxy Service: {server_info.get('proxy_service')}")
        
        info_parts.append("")  # Empty line
        
        # iMessage/iCloud Information
        if icloud_info:
            info_parts.append("iMessage Information")
            info_parts.append(f"Apple ID: {icloud_info.get('apple_id', 'Unknown')}")
            if icloud_info.get('account_name') and icloud_info.get('account_name') != 'Unknown':
                info_parts.append(f"Account Name: {icloud_info.get('account_name')}")
            info_parts.append(f"Login Status: {icloud_info.get('login_status_message', 'Unknown')}")
            info_parts.append(f"SMS Forwarding: {'✅ Enabled' if icloud_info.get('sms_forwarding_enabled', False) else '❌ Disabled'}")
            
            # Show aliases if available
            aliases = icloud_info.get('vetted_aliases', [])
            if aliases and len(aliases) > 1:  # Only show if there are multiple aliases
                info_parts.append(f"Email Aliases: {len(aliases)} configured")
                for alias in aliases[:3]:  # Show first 3 aliases
                    status = "✅" if alias.get('Status') == 3 else "⚠️"
                    info_parts.append(f"  - {status} {alias.get('Alias', 'Unknown')}")
                if len(aliases) > 3:
                    info_parts.append(f"  - ... and {len(aliases) - 3} more")
        else:
            info_parts.append("iMessage Information")
            info_parts.append("iCloud information unavailable")
        
        info_parts.append("")  # Empty line
        
        # Statistics
        if statistics:
            info_parts.append("Database Statistics")
            info_parts.append(f"Messages: {statistics.get('messages', 0):,}")
            info_parts.append(f"Chats: {statistics.get('chats', 0):,}")
            info_parts.append(f"Contacts: {statistics.get('handles', 0):,}")
            info_parts.append(f"Attachments: {statistics.get('attachments', 0):,}")
        else:
            info_parts.append("Database Statistics")
            info_parts.append("Statistics unavailable")
        
        # Join all parts with newlines
        body_text = "\n".join(info_parts)
        dialog.set_body(body_text)
        
        # Add close button
        dialog.add_response("close", "Close")
        dialog.set_default_response("close")
        
        # Show the dialog
        dialog.present(self)
    
    async def load_server_info_async(self, url: str, password: str):
        """Load server information asynchronously."""
        try:
            api_method = self.get_application().config_manager.get_api_method()
            async with BlueBubblesClient(url, password, api_method) as client:
                server_info = await client.get_server_info()
                version = server_info.get('server_version', 'Unknown')
                
                def update_title():
                    self.set_title(f"BlueBubbles - Server v{version}")
                
                GLib.idle_add(update_title)
        
        except Exception as e:
            error_msg = str(e)
            def show_error():
                self.show_toast(f"Failed to load server info: {error_msg}")
            
            GLib.idle_add(show_error)

    def start_message_monitoring(self):
        """Start background message monitoring."""
        config = self.config_manager.get_server_config()
        if not config['url'] or not config['password']:
            # print("⚠️  Cannot start message monitoring: No server configuration")
            return
        
        # Add callback for new message notifications
        self.chat_service.add_new_message_callback(self.on_new_message_detected)
        
        # Get message check interval from config (default 3 seconds)
        check_interval = self.config_manager.get('app.message_check_interval', 3)
        
        # Start the monitoring (ChatService handles the threading)
        self.chat_service.start_message_checking(
            config['url'], 
            config['password'], 
            check_interval
        )
        
        # print("🚀 Message monitoring started in background")
    
    def on_new_message_detected(self, chat_guid: str):
        """Called when a new message is detected in a chat."""
        # print(f"📨 New message detected in chat: {chat_guid}")
        
        # Update the UI on the main thread
        def update_ui():
            # Get the updated chat with the new message
            updated_chat = self.chat_service.get_chat_by_guid(chat_guid)
            if not updated_chat:
                # print(f"⚠️  Could not find chat {chat_guid} after new message")
                return
            
            # Update chat in our local list and move it to the top
            self.move_chat_to_top(updated_chat)
            
            # If this is the currently selected chat, refresh the messages
            if self.current_chat and self.current_chat.guid == chat_guid:
                self.refresh_current_chat_messages()
            
            # Show a toast notification
            chat_name = updated_chat.display_name if updated_chat.display_name else chat_guid[:8]
            self.show_toast(f"New message in {chat_name}")
        
        GLib.idle_add(update_ui)
    
    def move_chat_to_top(self, updated_chat):
        """Move a chat to the top of the list and update its preview."""
        # Find the existing chat in our local list
        chat_index = -1
        for i, chat in enumerate(self.chats):
            if chat.guid == updated_chat.guid:
                chat_index = i
                break
        
        if chat_index >= 0:
            # Remove the old chat from the list
            old_chat = self.chats.pop(chat_index)
            # print(f"📌 Moving chat {updated_chat.display_title} to top (was at index {chat_index})")
        else:
            pass  # Silently handle adding new chat to top
        
        # Add the updated chat to the beginning
        self.chats.insert(0, updated_chat)
        
        # Update the UI list efficiently
        self.update_chat_list_order(updated_chat, chat_index)
    
    def update_chat_list_order(self, updated_chat, old_index):
        """Efficiently update the chat list order without full rebuild."""
        # Find the existing row in the UI
        existing_row = None
        if old_index >= 0:
            # Find the row by comparing chat GUIDs
            child = self.chat_list.get_first_child()
            current_index = 0
            while child:
                if hasattr(child, 'chat') and child.chat.guid == updated_chat.guid:
                    existing_row = child
                    break
                child = child.get_next_sibling()
                current_index += 1
        
        if existing_row:
            # Remove the existing row
            self.chat_list.remove(existing_row)
            # print(f"🔄 Removed existing chat row for {updated_chat.display_title}")
        
        # Create a new row with updated data and insert at the top
        new_row = self.create_chat_row(updated_chat)
        self.chat_list.insert(new_row, 0)
        # print(f"⬆️ Moved {updated_chat.display_title} to top of chat list")
        
        # Update the selection if this was the current chat
        if self.current_chat and self.current_chat.guid == updated_chat.guid:
            self.chat_list.select_row(new_row)
            # Update the current_chat reference
            self.current_chat = updated_chat
    
    def refresh_current_chat_messages(self):
        """Refresh messages for the currently selected chat."""
        if not self.current_chat:
            # print("❌ No current chat selected")
            return
        
        # print(f"🔄 Refreshing messages for current chat: {self.current_chat.display_title}")
        
        # Reload messages from cache (they should already be updated by the background task)
        messages = self.chat_service.get_cached_chat_messages(self.current_chat.guid, limit=50)
        # print(f"📥 Retrieved {len(messages)} messages from cache")
        
        # Update the message list using the correct chat view name
        chat_view_name = f"chat_{self.current_chat.guid}"
        chat_view = self.content_stack.get_child_by_name(chat_view_name)
        # print(f"🎯 Looking for chat view: {chat_view_name}")
        # print(f"🎯 Chat view found: {chat_view is not None}")
        
        if chat_view:
            has_messages_box = hasattr(chat_view, 'messages_box')
            # print(f"📦 Chat view has messages_box: {has_messages_box}")
            
            if has_messages_box:
                # Add new messages efficiently
                self.add_new_messages_to_chat(chat_view.messages_box, messages)
                
                # Scroll to bottom if we have the messages_area
                if hasattr(chat_view, 'messages_area'):
                    GLib.idle_add(self.scroll_to_bottom, chat_view.messages_area)
            else:
                pass  # Silently handle missing messages_box
        else:
            pass  # Silently handle missing chat view
    
    def add_new_messages_to_chat(self, messages_box, new_messages):
        """Efficiently add new messages to the chat without clearing everything."""
        # print(f"🔍 Checking for new messages to add. Total messages from cache: {len(new_messages)}")
        
    # Ignore reaction-only events; they will be reflected as badges on their parent messages
        new_messages = [m for m in new_messages if not self.is_reaction_event(m)]

        # Get currently displayed messages by checking existing children
        existing_guids = set()
        child_count = 0
        child = messages_box.get_first_child()
        while child:
            child_count += 1
            if hasattr(child, 'message_guid'):
                existing_guids.add(child.message_guid)
                # Silently track existing messages
            else:
                # Silently handle children without message_guid
                pass
            child = child.get_next_sibling()
        
        # print(f"🔍 Currently displayed widgets: {child_count}, with message GUIDs: {len(existing_guids)}")
        
        # Find truly new messages
        messages_to_add = []
        for message in new_messages:
            if message.guid not in existing_guids:
                messages_to_add.append(message)
                # print(f"🔍 New message found: {message.guid} - {message.text[:50] if message.text else 'No text'}...")
            else:
                # Silently skip already displayed messages
                pass
        
        if messages_to_add:
            # print(f"➕ Adding {len(messages_to_add)} new messages to chat")
            
            # Sort by date to maintain chronological order
            messages_to_add.sort(key=lambda m: m.date_created)
            
            # Add new messages at the bottom
            for message in messages_to_add:
                message_widget = self.create_message_widget(message)
                # Store the message GUID for future reference
                message_widget.message_guid = message.guid
                messages_box.append(message_widget)
                # print(f"➕ Added message widget for: {message.guid}")
        else:
            # Silently handle case where no new messages need to be added
            pass

        # After adding/confirming messages, update reaction badges for all visible messages
        # to reflect any recent reaction changes.
        child = messages_box.get_first_child()
        while child:
            try:
                if hasattr(child, 'message_guid'):
                    guid = child.message_guid
                    # Lookup the corresponding message data
                    msg = next((m for m in new_messages if m.guid == guid), None)
                    if msg is None:
                        child = child.get_next_sibling()
                        continue
                    # Recalculate reactions for this message
                    reactions = self.chat_service.get_message_reactions(guid)
                    # Build the updated reactions widget
                    if reactions:
                        updated = self.create_reactions_widget(reactions, msg.is_from_me)
                    else:
                        updated = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
                        if msg.is_from_me:
                            updated.set_halign(Gtk.Align.END)
                        else:
                            updated.set_halign(Gtk.Align.START)
                    # Replace existing reactions widget if we have a reference
                    if hasattr(child, 'reactions_widget'):
                        try:
                            child.remove(child.reactions_widget)
                        except Exception:
                            pass
                        child.reactions_widget = updated
                        child.append(updated)
            except Exception:
                pass
            child = child.get_next_sibling()
    
    def on_window_destroy(self, window):
        """Called when the window is being destroyed."""
        # print("🛑 Window destroying, stopping message monitoring...")
        
        # Stop message monitoring
        self.chat_service.stop_message_checking()
        
        # Remove callback
        self.chat_service.remove_new_message_callback(self.on_new_message_detected)
