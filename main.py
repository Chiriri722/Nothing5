# -*- coding: utf-8 -*-
"""
LLM-based File Classifier - Main Entry Point

Analyzes file content and automatically classifies files using LLM.
Supports both GUI and CLI modes.
"""

import sys
import argparse
import signal
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from modules.app import FileClassifierApp
import config.config as config

def main():
    """
    Main entry point function.
    Parses arguments and starts the application.
    """
    # Load credentials (deferred loading)
    config.load_credentials()

    parser = argparse.ArgumentParser(
        description="LLM-based File Classifier",
        epilog="Example: python main.py --gui (GUI Mode), python main.py --cli (CLI Mode)"
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Run in GUI mode (Default)"
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in CLI mode"
    )
    parser.add_argument(
        "--folder",
        type=str,
        help="Folder path to monitor on startup"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Log level"
    )
    
    args = parser.parse_args()
    
    # Determine mode (GUI is default unless CLI is specified)
    gui_mode = True
    if args.cli:
        gui_mode = False
    
    try:
        app = FileClassifierApp(gui_mode=gui_mode)
        
        if not gui_mode:
            if args.folder:
                # In CLI mode, if folder provided, start monitoring immediately?
                # Or just pass it to the CLI handler?
                # For now, let's inject it into the app state or handle it.
                # The CLI handler usually enters an interactive loop.
                # If we want to start monitoring immediately, we can call it.
                print(f"Starting monitoring for: {args.folder}")
                app._on_start_monitoring(args.folder)

            app.run_cli()
        else:
            # GUI Mode
            if args.folder:
                 # It's hard to trigger this before main loop, but we can try
                 # Or the GUI might pick it up if we passed it.
                 # Current GUI implementation doesn't take args, so we might need to manually trigger.
                 # However, usually GUI starts and user selects.
                 pass
            app.run_gui()
    
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    except ValueError as e:
        print(f"Configuration Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
