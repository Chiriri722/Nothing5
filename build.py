import PyInstaller.__main__
import sys
from pathlib import Path

# Define project root
PROJECT_ROOT = Path(__file__).parent

def build():
    print("Building File Classifier executable...")
    
    # Common arguments
    args = [
        'main.py',                        # Entry point
        '--name=FileClassifier',          # Name of the executable
        '--clean',                        # Clean cache
        '--noconfirm',                    # Replace output directory without asking
        
        # Paths
        f'--paths={PROJECT_ROOT}',
        
        # Hidden imports (often missed by PyInstaller analysis)
        '--hidden-import=PIL',
        '--hidden-import=PIL.Image',
        '--hidden-import=dotenv',
        '--hidden-import=json',
        '--hidden-import=logging.config',
        '--hidden-import=modules',
        '--hidden-import=config',
        '--hidden-import=ui',
        '--hidden-import=watchdog',
        '--hidden-import=watchdog.observers',
        
        # Data files (if any needed)
        # '--add-data=config;config',     # Example: include config folder if needed inside bundle
    ]
    
    # Platform specific
    if sys.platform == "win32":
        # args.append('--windowed')         # No console window for GUI app (Commented out for debugging)
        pass
        # args.append('--icon=assets/icon.ico') # Add icon if available
    
    # Run PyInstaller
    PyInstaller.__main__.run(args)
    print("Build complete. Check 'dist/FileClassifier' folder.")

if __name__ == "__main__":
    build()
