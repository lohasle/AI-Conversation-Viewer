# AI Conversation Viewer 🔍

A beautiful, unified web interface for browsing and searching your AI conversation history across multiple platforms.

![Version](https://img.shields.io/badge/version-1.1.2-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)

## ✨ Features

- 🤖 **Multi-Platform Support** - Works with Claude Code and Qwen (通义千问) conversation histories
- 🔍 **Powerful Search** - Full-text search across all conversations with keyword highlighting
- 📂 **Smart Organization** - Browse conversations by project with session metadata and statistics
- 💻 **Syntax Highlighting** - Beautiful code blocks with language detection and copy buttons
- 🎨 **Modern UI** - Clean, responsive interface with dark/light theme support
- 🌍 **Internationalization** - Multi-language support (English/Chinese)
- ⚡ **Fast Performance** - Efficient pagination for large conversation histories
- 🔧 **Tool Visualization** - Clear display of tool usage and outputs
- 📊 **Interactive Diff Viewer** - View code changes with side-by-side diff comparison

## 🚀 Quick Start

### Installation

```bash
pip install ai-coder-viewer
```

### Usage

```bash
# Start with default settings (looks for ~/.claude/projects)
aicode-viewer

# Custom Claude projects path
aicode-viewer --projects-path /path/to/your/claude/projects

# Custom port
aicode-viewer --port 8080

# Accessible from other machines
aicode-viewer --host 0.0.0.0 --port 3000
```

Then open your browser to: `http://localhost:6300`

## 📸 Screenshots

### Main Dashboard - Claude View
Browse all your Claude Code projects with session counts and detailed statistics.

![Claude Main Dashboard](img/claude_index.png)

### Main Dashboard - Qwen View
Seamlessly switch between different AI platforms to view their conversation histories.

![Qwen Main Dashboard](img/qwen_index.png)

### Conversation Details
View conversations with proper formatting, syntax highlighting, and search capabilities.

![Conversation View](img/session_detail.png)

### Global Search
Search across all conversations and projects with instant results.

![Search Results](img/agent.png)

## 🛠️ Command Line Options

```bash
aicode-viewer --help
```

**Available options:**
- `--projects-path` - Path to Claude projects directory (default: `~/.claude/projects`)
- `--host` - Host to bind the server (default: `127.0.0.1`)
- `--port` - Port to run on (default: `6300`)
- `--version` - Show version information

## 📁 How It Works

AI conversation platforms store conversation history in JSONL files. This tool:

1. **Scans** your AI projects directory (Claude: `~/.claude/projects/`, Qwen: local storage)
2. **Parses** JSONL conversation files from multiple AI platforms
3. **Presents** them in a unified, beautiful web interface
4. **Enables** powerful search and filtering across all conversations
5. **Supports** multi-language UI for international users

## 🔧 Development

### Local Development

```bash
git clone https://github.com/desis123/claude-code-viewer
cd claude-code-viewer
pip install -e .
aicode-viewer
```

### Project Structure

```
claude-code-viewer/
├── claude_viewer/          # Main package
│   ├── cli.py             # Command line interface  
│   ├── main.py            # FastAPI application
│   └── utils/             # Utilities (JSONL parser)
├── static/                # CSS, JavaScript
├── templates/             # HTML templates
└── setup.py              # Package configuration
```

## 🤝 Contributing

Contributions welcome! Please:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Development Setup

```bash
git clone <your-fork>
cd claude-code-viewer
pip install -e ".[dev]"
```

## 🤖 Supported AI Platforms

Currently supports:
- **Claude Code** - Anthropic's official CLI for Claude
- **Qwen (通义千问)** - Alibaba Cloud's AI assistant

More platforms coming soon!

## 📋 Requirements

- **Python 3.8+**
- **AI Platform** (Claude Code, Qwen, or other supported platforms)
- **Modern web browser** (Chrome, Firefox, Safari, Edge)

## 🐛 Troubleshooting

### "Projects path does not exist"
Make sure Claude Code has been used and has created conversation files. The default path is `~/.claude/projects`.

### "No JSONL files found"
Ensure you have used Claude Code and it has generated conversation history. Try specifying a custom path with `--projects-path`.

### Port already in use
Use a different port: `aicode-viewer --port 8080`

## 📄 License

Apache 2.0 License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/) and [Bootstrap](https://getbootstrap.com/)
- Syntax highlighting by [Pygments](https://pygments.org/)
- Created for the AI development community

## 📊 Highlights

- 🎯 **Zero configuration** - Works out of the box for most users
- ⚡ **Fast startup** - Sub-second launch time
- 🔍 **Full-text search** - Search across all conversations instantly
- 📱 **Mobile responsive** - Works seamlessly on all devices
- 🌍 **Multi-language** - English and Chinese UI support
- 🤖 **Multi-platform** - Support for multiple AI platforms

## 🗺️ Roadmap

- [ ] Support for more AI platforms (Cursor, Gemini, etc.)
- [ ] Export conversations to various formats (PDF, Markdown, HTML)
- [ ] Advanced filtering and tagging system
- [ ] Conversation analytics and statistics
- [ ] Real-time conversation monitoring
- [ ] API for programmatic access

---

**Made with ❤️ for the AI development community**

[Report Issues](https://github.com/lohasle/AI-Conversation-Viewer/issues) • [Feature Requests](https://github.com/lohasle/AI-Conversation-Viewer/issues/new)  • [中文文档](README_CN.md)