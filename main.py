#!/usr/bin/env python3
"""
BlueBubbles GTK4 Client
A modern GTK4 application for connecting to BlueBubbles servers
"""

import gi
import sys
import os
from pathlib import Path

# Ensure we can find our modules when installed
if __name__ == '__main__':
    # Add the directory containing this script to the Python path
    script_dir = Path(__file__).parent.absolute()
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib
from src.application import BlueBubblesApplication

def main():
    """Main entry point for the application."""
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h']:
            print("BlueBubbles GTK4 Client")
            print("Usage: bluebubbles [options]")
            print("")
            print("Options:")
            print("  -h, --help     Show this help message")
            print("  --version      Show version information")
            return 0
        elif sys.argv[1] == '--version':
            print("BlueBubbles Client 1.0.0")
            return 0
    
    app = BlueBubblesApplication()
    return app.run(sys.argv)

if __name__ == '__main__':
    sys.exit(main())
