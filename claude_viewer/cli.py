#!/usr/bin/env python3
"""Command line interface for Claude Code Viewer."""

import argparse
import os
import sys
from pathlib import Path
import uvicorn

from . import __version__


def get_default_projects_path():
    """Get the default Claude projects path based on the operating system."""
    home = Path.home()
    
    # Standard Claude Code path
    claude_path = home / ".claude" / "projects"
    
    return str(claude_path)


def validate_projects_path(path):
    """Validate that the projects path exists and contains JSONL files."""
    projects_path = Path(path).expanduser().resolve()
    
    if not projects_path.exists():
        print(f"❌ Projects path does not exist: {projects_path}")
        print(f"💡 Make sure Claude Code has been used and created projects")
        print(f"💡 Or specify custom path with: --projects-path /your/path")
        return False
    
    if not projects_path.is_dir():
        print(f"❌ Projects path is not a directory: {projects_path}")
        return False
    
    # Check if it contains any project directories
    project_dirs = [d for d in projects_path.iterdir() if d.is_dir()]
    if not project_dirs:
        print(f"⚠️  No project directories found in: {projects_path}")
        print(f"💡 Make sure this is the correct Claude projects path")
        return False
    
    # Check for JSONL files
    jsonl_files = list(projects_path.glob("*/*.jsonl"))
    if not jsonl_files:
        print(f"⚠️  No JSONL conversation files found in: {projects_path}")
        print(f"💡 Projects exist but no conversations found")
        return False
    
    return True


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="claude-viewer",
        description="Beautiful web viewer for Claude Code conversation history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  claude-viewer                                    # Use default path (~/.claude/projects)
  claude-viewer --port 8080                       # Custom port
  claude-viewer --projects-path /custom/path      # Custom Claude projects path
  claude-viewer --host 0.0.0.0 --port 3000      # Accessible from other machines
        """
    )
    
    parser.add_argument(
        "--projects-path",
        type=str,
        default=get_default_projects_path(),
        help=f"Path to Claude projects directory (default: {get_default_projects_path()})"
    )
    
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=6300,
        help="Port to run the server on (default: 6300)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"claude-viewer {__version__}"
    )
    
    args = parser.parse_args()
    
    # Validate projects path
    if not validate_projects_path(args.projects_path):
        sys.exit(1)
    
    # Set environment variable for the app to use
    os.environ["CLAUDE_PROJECTS_PATH"] = str(Path(args.projects_path).expanduser().resolve())
    
    print(f"⚡ Claude Code Viewer v{__version__}")
    print(f"📁 Using projects: {os.environ['CLAUDE_PROJECTS_PATH']}")
    print(f"🌐 Starting server at http://{args.host}:{args.port}")
    print(f"🔍 Press Ctrl+C to stop")
    print()
    
    try:
        # Import and run the FastAPI app
        from .main import app
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info",
            access_log=False  # Reduce log noise
        )
    except KeyboardInterrupt:
        print("\n👋 Claude Code Viewer stopped")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()