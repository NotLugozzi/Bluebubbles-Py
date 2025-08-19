#!/usr/bin/env python3
"""
BlueBubbles GTK4 Client
A modern GTK4 application for connecting to BlueBubbles servers
"""

import gi
import sys
import os
from pathlib import Path

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib
from src.application import BlueBubblesApplication

def main():
    """Main entry point for the application."""
    app = BlueBubblesApplication()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
