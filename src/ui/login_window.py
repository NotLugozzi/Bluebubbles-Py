"""
Login Window
Handles the initial setup and authentication with BlueBubbles server
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio
import asyncio
import threading
from ..api.client import BlueBubblesClient, BlueBubblesAPIError

class LoginWindow(Adw.ApplicationWindow):
    """Login window for connecting to BlueBubbles server."""
    
    def __init__(self, application):
        super().__init__(application=application)
        
        self.set_title("BlueBubbles - Connect to Server")
        self.set_default_size(480, 360)
        self.set_resizable(False)
        
        # Build UI
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface."""
        # Create main content with toast overlay
        content = Adw.ToastOverlay()
        
        # Create a toolbar view to properly handle the header bar
        toolbar_view = Adw.ToolbarView()
        
        # Create header bar
        header_bar = Adw.HeaderBar()
        header_bar.set_show_end_title_buttons(True)
        toolbar_view.add_top_bar(header_bar)
        
        content.set_child(toolbar_view)
        self.set_content(content)
        
        # Create main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main_box.set_valign(Gtk.Align.CENTER)
        main_box.set_halign(Gtk.Align.CENTER)
        main_box.set_spacing(24)
        main_box.set_margin_top(48)
        main_box.set_margin_bottom(48)
        main_box.set_margin_start(48)
        main_box.set_margin_end(48)
        
        # App icon and title
        icon_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        icon_box.set_spacing(12)
        
        # App icon (using a fallback icon)
        app_icon = Gtk.Image()
        app_icon.set_from_icon_name("network-server-symbolic")
        app_icon.set_pixel_size(64)
        app_icon.add_css_class("accent")
        icon_box.append(app_icon)
        
        # App title
        title_label = Gtk.Label()
        title_label.set_markup("<span size='x-large' weight='bold'>BlueBubbles</span>")
        icon_box.append(title_label)
        
        # Subtitle
        subtitle_label = Gtk.Label()
        subtitle_label.set_text("Connect to your BlueBubbles server")
        subtitle_label.add_css_class("dim-label")
        icon_box.append(subtitle_label)
        
        main_box.append(icon_box)
        
        # Create form group
        form_group = Adw.PreferencesGroup()
        form_group.set_title("Server Configuration")
        form_group.set_description("Enter your BlueBubbles server details")
        
        # Server URL row
        self.url_row = Adw.EntryRow()
        self.url_row.set_title("Server URL")
        self.url_row.set_text("http://")
        self.url_row.connect("notify::text", self.on_input_changed)
        form_group.add(self.url_row)
        
        # Password row
        self.password_row = Adw.PasswordEntryRow()
        self.password_row.set_title("Password")
        self.password_row.connect("notify::text", self.on_input_changed)
        form_group.add(self.password_row)
        
        main_box.append(form_group)
        
        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button_box.set_spacing(12)
        button_box.set_halign(Gtk.Align.CENTER)
        
        # Test connection button
        self.test_button = Gtk.Button()
        self.test_button.set_label("Test Connection")
        self.test_button.add_css_class("suggested-action")
        self.test_button.set_sensitive(False)
        self.test_button.connect("clicked", self.on_test_clicked)
        button_box.append(self.test_button)
        
        # Connect button
        self.connect_button = Gtk.Button()
        self.connect_button.set_label("Connect")
        self.connect_button.add_css_class("suggested-action")
        self.connect_button.set_sensitive(False)
        self.connect_button.connect("clicked", self.on_connect_clicked)
        button_box.append(self.connect_button)
        
        main_box.append(button_box)
        
        # Status spinner (hidden initially)
        self.spinner = Gtk.Spinner()
        self.spinner.set_visible(False)
        main_box.append(self.spinner)
        
        # Set the main box as the content of the toolbar view
        toolbar_view.set_content(main_box)
        self.toast_overlay = content
        
        # Load existing config if available
        self.load_existing_config()
    
    def load_existing_config(self):
        """Load existing configuration if available."""
        config = self.get_application().config_manager.get_server_config()
        if config['url']:
            self.url_row.set_text(config['url'])
        if config['password']:
            self.password_row.set_text(config['password'])
    
    def on_input_changed(self, widget, param):
        """Handle input changes to enable/disable buttons."""
        url = self.url_row.get_text().strip()
        password = self.password_row.get_text().strip()
        
        has_input = bool(url and password and url != "http://")
        self.test_button.set_sensitive(has_input)
        self.connect_button.set_sensitive(has_input)
    
    def show_toast(self, message: str, timeout: int = 3):
        """Show a toast notification."""
        toast = Adw.Toast()
        toast.set_title(message)
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)
    
    def set_loading(self, loading: bool):
        """Set loading state."""
        self.spinner.set_visible(loading)
        if loading:
            self.spinner.start()
        else:
            self.spinner.stop()
        
        self.test_button.set_sensitive(not loading)
        self.connect_button.set_sensitive(not loading)
        self.url_row.set_sensitive(not loading)
        self.password_row.set_sensitive(not loading)
    
    def on_test_clicked(self, button):
        """Handle test connection button click."""
        url = self.url_row.get_text().strip()
        password = self.password_row.get_text().strip()
        
        # Run the async function in a thread to avoid event loop issues
        def run_async():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.test_connection_async(url, password))
                loop.close()
            except Exception as e:
                def show_error():
                    self.show_toast(f"Test failed: {str(e)}")
                    self.set_loading(False)
                GLib.idle_add(show_error)
        
        thread = threading.Thread(target=run_async, daemon=True)
        thread.start()
    
    def on_connect_clicked(self, button):
        """Handle connect button click."""
        url = self.url_row.get_text().strip()
        password = self.password_row.get_text().strip()
        
        # Save configuration and connect
        self.get_application().config_manager.set_server_config(url, password)
        self.show_toast("Configuration saved successfully!")
        
        # Notify application of successful login
        GLib.idle_add(self.get_application().on_login_success)
    
    async def test_connection_async(self, url: str, password: str):
        """Test connection to BlueBubbles server asynchronously."""
        def set_loading_state(loading):
            GLib.idle_add(self.set_loading, loading)
        
        def show_result(success, message):
            GLib.idle_add(self.show_toast, message)
        
        set_loading_state(True)
        
        try:
            api_method = self.application.config_manager.get_api_method()
            async with BlueBubblesClient(url, password, api_method) as client:
                success = await client.test_connection()
                if success:
                    # Get server info for additional validation
                    server_info = await client.get_server_info()
                    version = server_info.get('server_version', 'Unknown')
                    show_result(True, f"Connection successful! Server version: {version}")
                else:
                    show_result(False, "Connection failed! Check your server URL and password.")
        
        except BlueBubblesAPIError as e:
            show_result(False, f"Connection error: {str(e)}")
        except Exception as e:
            show_result(False, f"Unexpected error: {str(e)}")
        finally:
            set_loading_state(False)
