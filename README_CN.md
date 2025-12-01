# AI 对话查看器 🔍

一个美观、统一的 Web 界面，用于浏览和搜索多个平台的 AI 对话历史记录。

![Version](https://img.shields.io/badge/version-1.1.4-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)

## ✨ 核心特性

- 🤖 **多 IDE 来源** — 支持 Claude、通义千问，并提供 Cursor/Trae/Kiro 视图切换
- 🔎 **全局与会话搜索** — 跨所有 IDE 或在单个会话中搜索，关键词高亮显示
- 📁 **项目与会话浏览** — 按日期分组，展示活动时间线与丰富元数据
- 💻 **Markdown + 代码高亮** — Pygments 渲染代码块与内联代码，阅读体验佳
- 🧩 **工具调用可视化** — 结构化的工具名称、参数与输出结果清晰呈现
- 🧾 **编辑操作 Diff** — 对 Edit 工具结果生成统一 Diff，标注新增/删除行
- 🎛️ **筛选与分页** — 支持按角色（用户/助手/摘要）、每页数量筛选与大线程分页
- 🎨 **现代体验** — 深浅主题切换、响应式布局、代码块一键复制
- 🌍 **国际化** — 内置中英文切换，界面文案一致
- 📈 **仪表盘与统计** — 全局统计卡片与最近会话列表，快速导航

### 功能详解

- 多 IDE 支持
  - 顶部导航一键切换 `Claude`/`Qwen`/`Cursor`/`Trae`/`Kiro`
  - 自动探测默认数据路径；可通过环境变量覆盖：
    - `CLAUDE_PROJECTS_PATH`、`QWEN_PROJECTS_PATH`、`CURSOR_WORKSPACE_STORAGE_PATH`、`TRAE_WORKSPACE_STORAGE_PATH`、`KIRO_WORKSPACE_STORAGE_PATH`

- 项目与会话浏览
  - 项目展示会话数量、修改时间与基于工作区元数据的友好名称
  - 会话卡片显示消息数、文件大小、修改时间与自动提取的标题；支持最近活动时间线

- 对话详情视图
  - Markdown 渲染与代码高亮（支持围栏代码与内联代码）
  - 会话内搜索与关键词高亮；按 `user`/`assistant`/`summary` 角色筛选
  - 对长列表进行分页；超长工具输出智能截断以保证性能与可读性
  - 工具调用以人性化格式展示参数与结果
  - Edit 工具的结果内嵌统一 Diff（行号、增删标记等）

- 全局仪表盘与搜索
  - 跨所有 IDE 的全局搜索，带结果预览与快速跳转
  - 每个 IDE 的统计卡（项目/会话计数与可用性），并展示最近会话

- 国际化与主题
  - 通过 Cookie 切换语言；英文/中文界面文案完整覆盖
  - 主题切换深/浅色并持久化；移动端友好

- 健康检查与诊断
  - `/health` 接口提供各 IDE 存储路径与项目/会话统计，便于部署与排障

### 收藏与注释

- 支持收藏会话与单条消息，并持久化保存
  - 在会话页顶部或消息行右侧点击星标可添加到收藏
  - 通过顶部导航进入“收藏”页面进行浏览、筛选、编辑与移除
- 存储
  - 使用 SQLite 持久化，位置为 `~/.aicode-viewer/favorites.db`
  - 支持标签、注释文本与内容预览
- 筛选与统计
  - 可按 `type`（会话/消息）、IDE `view`、`tag`、文本 `search` 进行筛选
  - 收藏统计展示：按类型和 IDE 的数量，以及热门标签

实现位置参考
- 收藏数据库：`claude_viewer/db/favorites_db.py`
- 收藏页面与星标按钮：`claude_viewer/templates/favorites.html`、`claude_viewer/templates/conversation.html`

## 🚀 快速开始

### 安装

```bash
pip install ai-coder-viewer
```

### 使用方法

```bash
# 使用默认设置启动（自动查找 ~/.claude/projects）
aicode-viewer

# 指定自定义 Claude 项目路径
aicode-viewer --projects-path /path/to/your/claude/projects

# 自定义端口
aicode-viewer --port 8080

# 允许其他机器访问
aicode-viewer --host 0.0.0.0 --port 3000
```

然后在浏览器中打开：`http://localhost:6300`

## 📸 界面截图

### 主面板 - Claude 视图
浏览所有 Claude Code 项目，查看会话数量和详细统计信息。

![Claude 主面板](img/claude_index.png)

### 主面板 - 通义千问视图
无缝切换不同 AI 平台，查看对话历史记录。

![通义千问主面板](img/qwen_index.png)

### 对话详情
查看对话内容，包含格式化、语法高亮和搜索功能。

![对话视图](img/session_detail.png)

### 全局搜索
跨所有对话和项目搜索，即时显示结果。

![搜索结果](img/agent.png)

## 🛠️ 命令行选项

```bash
aicode-viewer --help
```

**可用选项：**
- `--projects-path` - Claude 项目目录路径（默认：`~/.claude/projects`）
- `--host` - 服务器绑定地址（默认：`127.0.0.1`）
- `--port` - 运行端口（默认：`6300`）
- `--version` - 显示版本信息

## 📁 工作原理

AI 对话平台将对话历史存储在 JSONL 文件中。本工具：

1. **扫描** 您的 AI 项目目录（Claude：`~/.claude/projects/`，通义千问：本地存储）
2. **解析** 来自多个 AI 平台的 JSONL 对话文件
3. **展示** 在统一、美观的 Web 界面中
4. **支持** 跨所有对话的强大搜索和过滤功能
5. **提供** 多语言界面支持国际用户

## 🔧 开发指南

### 本地开发

```bash
git clone https://github.com/lohasle/AI-Conversation-Viewer
cd AI-Conversation-Viewer
pip install -e .
aicode-viewer
```

#### 热更新运行

```bash
uvicorn claude_viewer.main:app --reload --host 127.0.0.1 --port 6300
```

#### 配置数据路径

- `CLAUDE_PROJECTS_PATH` — Claude 项目目录
- `QWEN_PROJECTS_PATH` — 通义千问本地数据目录
- `CURSOR_WORKSPACE_STORAGE_PATH` — Cursor 工作区存储
- `TRAE_WORKSPACE_STORAGE_PATH` — Trae 工作区存储
- `KIRO_WORKSPACE_STORAGE_PATH` — Kiro 工作区存储

示例：

```bash
export CLAUDE_PROJECTS_PATH=~/.claude/projects
export QWEN_PROJECTS_PATH=~/.qwen/tmp
aicode-viewer --port 6300
```

#### 无需安装直接运行

```bash
python -m uvicorn claude_viewer.main:app --reload
```

### 项目结构

```
claude-code-viewer/
├── claude_viewer/                  # Python 包
│   ├── main.py                     # FastAPI 应用
│   ├── cli.py                      # 命令行入口
│   ├── i18n.py                     # 界面文案与国际化
│   ├── db/                         # 收藏 SQLite（增删改查、标签、统计）
│   ├── utils/                      # 解析与工具（Claude/Qwen 等）
│   ├── templates/                  # Jinja2 模板（仪表盘、项目、会话、收藏）
│   └── static/                     # 前端资源（CSS/JS）
├── img/                            # README 截图资源
├── pyproject.toml                  # 打包元数据（推荐）
├── setup.py                        # 兼容的打包元数据
├── MANIFEST.in                     # 资源打包配置
├── LICENSE                         # Apache 2.0 许可证
├── README.md / README_CN.md        # 文档（英文/中文）
├── QWEN.md                         # 通义千问相关说明
├── build_and_upload.sh             # 发布辅助脚本
└── .github/workflows/ci.yml        # CI 流水线
```

## 🤝 贡献指南

欢迎贡献！请遵循以下步骤：

1. **Fork** 本仓库
2. **创建** 功能分支（`git checkout -b feature/amazing-feature`）
3. **提交** 您的更改（`git commit -m 'Add amazing feature'`）
4. **推送** 到分支（`git push origin feature/amazing-feature`）
5. **提交** Pull Request

### 开发环境设置

```bash
git clone <your-fork>
cd claude-code-viewer
pip install -e ".[dev]"
```

## 🤖 支持的 AI 平台

目前支持：
- **Claude Code** — Anthropic 官方 Claude CLI 工具
- **Qwen（通义千问）** — 阿里云 AI 助手
- **Cursor** — AI 编码 IDE 工作区会话
- **Trae** — AI 编码 IDE 工作区会话
- **Kiro** — AI 编码 IDE 工作区会话

更多平台即将推出！

## 📋 系统要求

- **Python 3.8+**
- **AI 平台**（Claude Code、通义千问或其他支持的平台）
- **现代浏览器**（Chrome、Firefox、Safari、Edge）

## 🐛 常见问题

### "Projects path does not exist"（项目路径不存在）
确保已使用 Claude Code 并创建了对话文件。默认路径为 `~/.claude/projects`。

### "No JSONL files found"（未找到 JSONL 文件）
确保您已使用 Claude Code 并生成了对话历史。尝试使用 `--projects-path` 指定自定义路径。

### 端口已被占用
使用其他端口：`aicode-viewer --port 8080`

## 📄 开源协议

Apache 2.0 License - 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- 使用 [FastAPI](https://fastapi.tiangolo.com/) 和 [Bootstrap](https://getbootstrap.com/) 构建
- 语法高亮由 [Pygments](https://pygments.org/) 提供
- 为 AI 开发者社区创建

## 📊 亮点

- 🎯 **零配置** - 开箱即用，无需复杂设置
- ⚡ **快速启动** - 亚秒级启动时间
- 🔍 **全文搜索** - 即时搜索所有对话
- 📱 **移动响应式** - 在所有设备上无缝运行
- 🌍 **多语言** - 支持中英文界面
- 🤖 **多平台** - 支持多个 AI 平台

## 🗺️ 开发路线图

- [ ] 支持更多 AI 平台（Gemini 等）
- [ ] 导出对话到多种格式（PDF、Markdown、HTML）
- [ ] 高级过滤和标签系统
- [ ] 对话分析和统计
- [ ] 实时对话监控
- [ ] 支持在 Web 端继续对话和提问
- [ ] UI 美化，采用 IM 风格消息界面
 

---

**用 ❤️ 为 AI 开发者社区打造**

[问题反馈](https://github.com/lohasle/AI-Conversation-Viewer/issues) • [功能建议](https://github.com/lohasle/AI-Conversation-Viewer/issues/new)  • [English Docs](README.md)
