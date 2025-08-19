"""
Preferences Dialog
Handles application preferences and settings
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio


class PreferencesDialog(Adw.PreferencesDialog):
    """Preferences dialog for application settings."""
    
    def __init__(self, application):
        super().__init__()
        self.application = application
        self.config_manager = application.config_manager
        
        self.set_title("Preferences")
        
        self.setup_ui()
        self.load_preferences()
    
    def setup_ui(self):
        """Set up the preferences dialog UI."""
        # Create main preferences page
        main_page = Adw.PreferencesPage()
        main_page.set_title("General")
        main_page.set_icon_name("preferences-system-symbolic")
        
        # Appearance Group
        appearance_group = Adw.PreferencesGroup()
        appearance_group.set_title("Appearance")
        appearance_group.set_description("Customize the application appearance")
        
        # Dark Mode Toggle
        self.dark_mode_row = Adw.SwitchRow()
        self.dark_mode_row.set_title("Dark Mode")
        self.dark_mode_row.set_subtitle("Use dark theme for the application interface")
        self.dark_mode_row.connect("notify::active", self.on_dark_mode_changed)
        appearance_group.add(self.dark_mode_row)
        
        # Text Width Setting
        self.text_width_row = Adw.SpinRow()
        self.text_width_row.set_title("Text Width")
        self.text_width_row.set_subtitle("Maximum width for text content (affects message display and readability)")
        
        # Set up adjustment for text width (range: 60-150, step: 5, default: 80)
        adjustment = Gtk.Adjustment()
        adjustment.set_lower(60)
        adjustment.set_upper(150)
        adjustment.set_step_increment(5)
        adjustment.set_page_increment(10)
        adjustment.set_value(80)  # Default value
        
        self.text_width_row.set_adjustment(adjustment)
        self.text_width_row.connect("notify::value", self.on_text_width_changed)
        appearance_group.add(self.text_width_row)
        
        main_page.add(appearance_group)
        
        # Server Group
        server_group = Adw.PreferencesGroup()
        server_group.set_title("Server")
        server_group.set_description("Manage your BlueBubbles server connection")
        
        # Server Info Row (Read-only display)
        server_config = self.config_manager.get_server_config()
        if server_config['url']:
            self.server_info_row = Adw.ActionRow()
            self.server_info_row.set_title("Current Server")
            self.server_info_row.set_subtitle(server_config['url'])
            
            # Add an icon to show connection status
            status_icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
            status_icon.add_css_class("success")
            self.server_info_row.add_prefix(status_icon)
            
            server_group.add(self.server_info_row)
        
        # Forget Server Button
        self.forget_server_row = Adw.ActionRow()
        self.forget_server_row.set_title("Forget Server")
        self.forget_server_row.set_subtitle("Remove saved server configuration and return to login")
        
        forget_button = Gtk.Button()
        forget_button.set_label("Forget")
        forget_button.add_css_class("destructive-action")
        forget_button.set_valign(Gtk.Align.CENTER)
        forget_button.connect("clicked", self.on_forget_server_clicked)
        
        self.forget_server_row.add_suffix(forget_button)
        self.forget_server_row.set_activatable_widget(forget_button)
        
        server_group.add(self.forget_server_row)
        
        main_page.add(server_group)
        
        # Add the main page to the dialog
        self.add(main_page)
        
        # Advanced page (for future use)
        advanced_page = Adw.PreferencesPage()
        advanced_page.set_title("Advanced")
        advanced_page.set_icon_name("dialog-warning-symbolic")
        
        # API Method Group
        api_group = Adw.PreferencesGroup()
        api_group.set_title("⚠️ Dangerous Zone")
        api_group.set_description("These settings can break functionality. Only modify if you know what you're doing!")
        
        # API Method Selection
        self.api_method_row = Adw.SwitchRow()
        self.api_method_row.set_title("🔴 Use Private API")
        self.api_method_row.set_subtitle("⚠️ EXPERIMENTAL: Switch from AppleScript to Private API\n❌ This may cause instability, crashes, or data loss\n🚫 NOT recommended for general use")
        self.api_method_row.connect("notify::active", self.on_api_method_changed)
        
        # Make the toggle look dangerous
        self.api_method_row.add_css_class("error")
        
        api_group.add(self.api_method_row)
        
        # Warning expandable row
        warning_row = Adw.ExpanderRow()
        warning_row.set_title("⚠️ Read This Before Enabling")
        warning_row.set_subtitle("Important warnings about Private API usage")
        warning_row.add_css_class("error")
        
        # Warning content
        warning_content = Gtk.Label()
        warning_content.set_markup("""<b>🚨 DANGER: EXPERIMENTAL FEATURE 🚨</b>

<b>Using Private API may:</b>
• Cause app crashes and system instability
• Break compatibility with future macOS updates
• Potentially violate Apple's terms of service
• Lead to unexpected behavior or data corruption
• Require technical knowledge to troubleshoot

<b>This feature is intended for:</b>
• Advanced users and developers only
• Testing and experimental purposes
• Users who understand the risks involved

<b>⚠️ USE AT YOUR OWN RISK ⚠️</b>
We are not responsible for any damage or issues caused by enabling this feature.""")
        
        warning_content.set_wrap(True)
        warning_content.set_halign(Gtk.Align.START)
        warning_content.set_margin_top(10)
        warning_content.set_margin_bottom(10)
        warning_content.set_margin_start(10)
        warning_content.set_margin_end(10)
        warning_content.add_css_class("warning")
        
        warning_row.add_row(warning_content)
        api_group.add(warning_row)
        
        advanced_page.add(api_group)
        
        # Other Advanced Settings Group (placeholder for future)
        other_advanced_group = Adw.PreferencesGroup()
        other_advanced_group.set_title("Other Advanced Settings")
        other_advanced_group.set_description("Additional advanced configuration options")
        
        # Placeholder row
        placeholder_row = Adw.ActionRow()
        placeholder_row.set_title("More settings coming soon")
        placeholder_row.set_subtitle("Additional preferences will be added in future versions")
        placeholder_row.set_sensitive(False)
        
        other_advanced_group.add(placeholder_row)
        advanced_page.add(other_advanced_group)
        
        self.add(advanced_page)
    
    def load_preferences(self):
        """Load current preferences from config."""
        # Load dark mode preference
        dark_mode = self.config_manager.get('appearance.dark_mode', False)
        self.dark_mode_row.set_active(dark_mode)
        
        # Load text width preference
        text_width = self.config_manager.get('appearance.text_width', 80)
        self.text_width_row.set_value(text_width)
        
        # Load API method preference
        api_method = self.config_manager.get_api_method()
        self.api_method_row.set_active(api_method == 'private')
    
    def on_dark_mode_changed(self, switch_row, pspec):
        """Handle dark mode toggle change."""
        is_dark = switch_row.get_active()
        self.config_manager.set('appearance.dark_mode', is_dark)
        
        # Apply the theme change immediately
        style_manager = Adw.StyleManager.get_default()
        if is_dark:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
    
    def on_text_width_changed(self, spin_row, pspec):
        """Handle text width change."""
        width = int(spin_row.get_value())
        self.config_manager.set('appearance.text_width', width)
    
    def on_api_method_changed(self, switch_row, pspec):
        """Handle API method toggle change."""
        use_private = switch_row.get_active()
        
        if use_private:
            # Show a confirmation dialog for enabling private API
            dialog = Adw.AlertDialog()
            dialog.set_heading("⚠️ Enable Private API?")
            dialog.set_body("You are about to enable the Private API mode. This is an experimental feature that may cause instability, crashes, or other issues.\n\nThis feature is intended for advanced users only. Are you sure you want to proceed?")
            
            # Add responses
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("enable", "⚠️ Enable Anyway")
            
            # Make the enable button destructive
            dialog.set_response_appearance("enable", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")
            
            # Connect the response handler
            dialog.connect("response", self.on_api_method_confirmation, switch_row)
            
            # Present the confirmation dialog
            dialog.present(self)
        else:
            # Switching back to AppleScript is safe
            self.config_manager.set_api_method('applescript')
    
    def on_api_method_confirmation(self, dialog, response, switch_row):
        """Handle the API method confirmation dialog response."""
        if response == "enable":
            # User confirmed, enable private API
            self.config_manager.set_api_method('private')
        else:
            # User cancelled, revert the switch
            switch_row.set_active(False)
    
    def on_forget_server_clicked(self, button):
        """Handle forget server button click."""
        # Create confirmation dialog
        dialog = Adw.AlertDialog()
        dialog.set_heading("Forget Server?")
        dialog.set_body("This will remove your saved server configuration and return you to the login screen. You'll need to re-enter your server details to reconnect.")
        
        # Add responses
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("forget", "Forget Server")
        
        # Make the forget button destructive
        dialog.set_response_appearance("forget", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        # Connect the response handler
        dialog.connect("response", self.on_forget_server_response)
        
        # Present the confirmation dialog
        dialog.present(self)
    
    def on_forget_server_response(self, dialog, response):
        """Handle the response from the forget server confirmation dialog."""
        if response == "forget":
            # Clear the server configuration
            self.config_manager.clear_server_config()
            
            # Close the preferences dialog
            self.close()
            
            # Close the main window if it exists
            if self.application.main_window:
                self.application.main_window.close()
                self.application.main_window = None
            
            # Show the login window
            self.application.show_login_window()
    
    def get_text_width_chars(self) -> int:
        """Get the current text width setting in characters."""
        return self.config_manager.get('appearance.text_width', 80)
