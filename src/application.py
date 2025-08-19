"""
Main Application Module
Handles the main GTK4/Adwaita application lifecycle
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib
from pathlib import Path
from pathlib import Path

from .config.manager import ConfigManager
from .ui.login_window import LoginWindow
from .ui.main_window import MainWindow
from .ui.preferences_dialog import PreferencesDialog
from .db.manager import DatabaseManager
from .services.chat_service import ChatService

class BlueBubblesApplication(Adw.Application):
    """Main application class that manages the entire application lifecycle."""
    
    def __init__(self):
        super().__init__(
            application_id='com.github.bluebubbles.client',
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )
        
        self.config_manager = ConfigManager()
        
        # Initialize database and services
        self.db_manager = DatabaseManager()
        self.chat_service = ChatService(self.db_manager, self.config_manager)
        
        self.main_window = None
        self.login_window = None
        
        self.connect('activate', self.on_activate)
        self.connect('startup', self.on_startup)
    
    def on_startup(self, app):
        """Called when the application starts up."""
        self.setup_actions()
        self.apply_theme_preference()
    
    def load_styles(self):
        """Load custom CSS styles."""
        try:
            css_provider = Gtk.CssProvider()
            css_path = Path(__file__).parent / 'ui' / 'styles.css'
            css_provider.load_from_path(str(css_path))
            
            # Apply to default display
            if self.main_window:
                display = self.main_window.get_display()
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    css_provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
        except Exception as e:
            pass  # Silently handle CSS loading errors
        
    def on_activate(self, app):
        """Called when the application is activated."""
        if self.config_manager.has_valid_config():
            self.show_main_window()
        else:
            self.show_login_window()
    
    def setup_actions(self):
        """Set up application-wide actions."""
        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', self.on_quit_action)
        self.add_action(quit_action)
        self.set_accels_for_action('app.quit', ['<primary>q'])
        
        prefs_action = Gio.SimpleAction.new('preferences', None)
        prefs_action.connect('activate', self.on_preferences_action)
        self.add_action(prefs_action)
        self.set_accels_for_action('app.preferences', ['<primary>comma'])
        
        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', self.on_about_action)
        self.add_action(about_action)
    
    def show_login_window(self):
        """Show the login window."""
        if self.login_window is None:
            self.login_window = LoginWindow(application=self)
        self.login_window.present()
    
    def show_main_window(self):
        """Show the main application window."""
        if self.main_window is None:
            self.main_window = MainWindow(application=self)
            self.load_styles()  # Load styles after window is created
        self.main_window.present()
    
    def get_chat_service(self) -> ChatService:
        """Get the chat service instance."""
        return self.chat_service
    
    def on_login_success(self):
        """Called when login is successful."""
        if self.login_window:
            self.login_window.close()
        self.show_main_window()
    
    def on_quit_action(self, action, param):
        """Handle quit action."""
        self.quit()
    
    def on_preferences_action(self, action, param):
        """Handle preferences action."""
        if hasattr(self, 'main_window') and self.main_window:
            prefs_dialog = PreferencesDialog(self)
            prefs_dialog.present(self.main_window)
        else:
            prefs_dialog = PreferencesDialog(self)
            prefs_dialog.present()
    
    def on_about_action(self, action, param):
        """Handle about action."""
        if self.main_window:
            self.main_window.show_about_dialog()
    
    def apply_theme_preference(self):
        """Apply the saved theme preference."""
        dark_mode = self.config_manager.get('appearance.dark_mode', False)
        style_manager = Adw.StyleManager.get_default()
        
        if dark_mode:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_manager.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
