# Changelog

All notable changes to claude-code-viewer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-01-31

### Added
- **Diff Viewer**: Interactive diff visualization for Edit tool calls
  - Side-by-side view showing old_string vs new_string changes
  - Syntax-highlighted line-by-line diffs with + and - indicators
  - Color-coded additions (green) and removals (red)
  - Line numbers and context preservation
  - Support for both tool_use and tool_result Edit operations
  - Professional Git-style diff formatting
- Enhanced HTML rendering to preserve diff content
- Improved tool call visualization

### Changed
- Updated markdown renderer to handle pre-rendered HTML content
- Enhanced structured content parsing for better tool display

### Technical Details
- Added difflib-based diff generation with HTML output
- CSS styling for diff containers with dark/light theme support
- Responsive design for mobile diff viewing
- Automatic detection of Edit tool calls in JSONL content

## [1.0.0] - 2025-01-31

### Added
- Initial release of Claude Code Viewer
- Web interface for browsing Claude Code conversation history
- Full-text search across all conversations
- Project organization with session metadata
- Syntax highlighting for code blocks with copy buttons
- Modern responsive UI with dark/light theme support
- Fast pagination for large conversation histories
- Tool usage visualization and formatting
- Command line interface with simple configuration
- Cross-platform support (Windows, macOS, Linux)
- Auto-detection of Claude projects directory
- Health check endpoint for monitoring

### Features
- **Search & Filter**: Find specific conversations and filter by message type
- **Code Highlighting**: Automatic language detection and syntax highlighting
- **Responsive Design**: Works on desktop and mobile devices
- **Zero Configuration**: Works out of the box for most users
- **Simple CLI**: Easy command line interface with minimal options
- **Fast Performance**: Efficient pagination and caching

### Technical
- Built with FastAPI and modern web technologies
- Supports Python 3.8+
- Comprehensive error handling and validation
- Clean package structure for easy maintenance
- Full test coverage and CI/CD pipeline

### Documentation
- Comprehensive README with screenshots
- Command line help and examples
- Troubleshooting guide
- Contributing guidelines