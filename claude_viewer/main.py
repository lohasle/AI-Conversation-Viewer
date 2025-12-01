"""FastAPI main application for Claude Code Viewer."""

import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Request, Response, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from .utils.jsonl_parser import JSONLParser
from .i18n import get_translation, TRANSLATIONS
from .db.favorites_db import FavoritesDB
import markdown
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound
import re
import html

# Get the package directory
PACKAGE_DIR = Path(__file__).parent

# Try to find static and templates directories
# First try relative to package (for installed package)
STATIC_DIR = PACKAGE_DIR / "static"
TEMPLATES_DIR = PACKAGE_DIR / "templates"

# If not found, try relative to parent (for development)
if not STATIC_DIR.exists():
    STATIC_DIR = PACKAGE_DIR.parent / "static"
if not TEMPLATES_DIR.exists():
    TEMPLATES_DIR = PACKAGE_DIR.parent / "templates"

# Create FastAPI app
app = FastAPI(
    title="Claude Code Conversation Viewer",
    description="View, search and browse Claude Code conversation history",
    version="1.0.0"
)

# Setup static files and templates
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Initialize favorites database
favorites_db = FavoritesDB()

# Configuration
GITHUB_URL = os.environ.get("GITHUB_REPO_URL", "https://github.com/lohasle/AI-Conversation-Viewer")

# Helper functions
def get_language_from_cookie(request: Request) -> str:
    """Get language preference from cookie, default to 'en'."""
    return request.cookies.get("lang", "en")

def highlight_search_text(text: str, query: str) -> str:
    """Highlight search query in text."""
    if not query or not text:
        return text

    # Escape HTML in both text and query to prevent XSS
    text = html.escape(text)
    query = html.escape(query)

    # Create a case-insensitive pattern
    pattern = re.compile(f'({re.escape(query)})', re.IGNORECASE)
    # Replace with highlighted version
    highlighted = pattern.sub(r'<mark class="bg-yellow-200 dark:bg-yellow-800 px-1 rounded">\1</mark>', text)
    return highlighted

def add_template_context(request: Request, context: dict) -> dict:
    """Add common context variables to all templates."""
    lang = get_language_from_cookie(request)

    # Add translation function
    context['t'] = lambda key: get_translation(key, lang)
    context['lang'] = lang
    context['github_url'] = GITHUB_URL
    context['available_languages'] = list(TRANSLATIONS.keys())

    return context

# Initialize parser with custom path from environment
def get_parser(parser_type: str = "qwen"):
    """Get JSONLParser instance with configured path."""
    if parser_type == "claude":
        claude_path = os.environ.get("CLAUDE_PROJECTS_PATH")
        if not claude_path:
            # Fallback to default
            claude_path = str(Path.home() / ".claude" / "projects")
        return JSONLParser(claude_path, parser_type="claude")
    elif parser_type == "qwen":
        qwen_path = os.environ.get("QWEN_PROJECTS_PATH")
        if not qwen_path:
            # Fallback to default
            qwen_path = str(Path.home() / ".qwen" / "tmp")
        return JSONLParser(qwen_path, parser_type="qwen")
    elif parser_type == "cursor":
        cursor_path = os.environ.get("CURSOR_WORKSPACE_STORAGE_PATH")
        if not cursor_path:
            cursor_path = str(Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage")
        return JSONLParser(cursor_path, parser_type="cursor")
    elif parser_type == "trae":
        trae_path = os.environ.get("TRAE_WORKSPACE_STORAGE_PATH")
        if not trae_path:
            trae_path = str(Path.home() / "Library" / "Application Support" / "Trae" / "User" / "workspaceStorage")
        return JSONLParser(trae_path, parser_type="trae")
    elif parser_type == "kiro":
        kiro_path = os.environ.get("KIRO_WORKSPACE_STORAGE_PATH")
        if not kiro_path:
            kiro_path = str(Path.home() / "Library" / "Application Support" / "Kiro" / "User" / "workspaceStorage")
        return JSONLParser(kiro_path, parser_type="kiro")
    else:
        raise ValueError(f"Unsupported parser type: {parser_type}")

# Pydantic models
class Project(BaseModel):
    name: str
    display_name: str
    path: str
    session_count: int
    sessions: List[str]
    source: Optional[str] = "qwen"  # Updated default to qwen since we're Qwen-only now
    modified_time: Optional[float] = None  # Add modification time
    modified_time_str: Optional[str] = None  # Add formatted modification time

class Session(BaseModel):
    id: str
    filename: str
    path: str
    size: int
    modified: str
    message_count: int

class Message(BaseModel):
    line_number: int
    type: str
    role: Optional[str] = None
    content: str
    display_type: str
    has_code: bool = False
    timestamp: Optional[str] = None
    uuid: Optional[str] = None

class ConversationResponse(BaseModel):
    messages: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int
    total_pages: int

# Favorites models
class TagModel(BaseModel):
    id: Optional[int] = None
    name: str
    color: Optional[str] = None
    is_auto: bool = False
    usage_count: Optional[int] = 0

class CreateFavoriteRequest(BaseModel):
    type: Literal["session", "message"] = Field(..., description="Favorite type")
    view: str = Field(..., description="IDE type")
    project_name: str
    session_id: str
    title: str
    annotation: Optional[str] = None
    content_preview: Optional[str] = None
    message_line: Optional[int] = None
    message_content: Optional[str] = None
    tags: List[str] = []

class UpdateFavoriteRequest(BaseModel):
    annotation: Optional[str] = None
    tags: Optional[List[str]] = None

class FavoriteModel(BaseModel):
    id: str
    type: str
    view: str
    project_name: str
    session_id: str
    message_line: Optional[int] = None
    message_hash: Optional[str] = None
    title: str
    annotation: Optional[str] = None
    content_preview: Optional[str] = None
    tags: List[TagModel] = []
    created_at: str
    updated_at: str

class FavoritesListResponse(BaseModel):
    favorites: List[FavoriteModel]
    total: int
    statistics: Optional[Dict[str, Any]] = None

# Custom markdown renderer with syntax highlighting
def render_markdown_with_code(text: str) -> str:
    """Render markdown with syntax highlighting for code blocks"""
    
    # Check if content already contains diff HTML - if so, preserve it
    if '<div class="diff-container">' in text:
        # This is diff content that's already HTML - just process markdown around it
        # but preserve the diff HTML blocks
        
        # Split content by diff containers to process markdown around them
        diff_parts = text.split('<div class="diff-container">')
        processed_parts = []
        
        for i, part in enumerate(diff_parts):
            if i == 0:
                # First part - before any diff, process as markdown
                processed_parts.append(process_markdown_text(part))
            else:
                # This part starts with diff content
                if '</div>' in part:
                    # Find where diff content ends
                    diff_end = part.rfind('</div>') + 6  # Include the closing tag
                    diff_html = '<div class="diff-container">' + part[:diff_end]
                    remaining_text = part[diff_end:]
                    
                    processed_parts.append(diff_html)
                    if remaining_text.strip():
                        processed_parts.append(process_markdown_text(remaining_text))
                else:
                    # Malformed diff HTML, process as regular markdown
                    processed_parts.append(process_markdown_text('<div class="diff-container">' + part))
        
        return ''.join(processed_parts)
    else:
        # Regular content without diffs
        return process_markdown_text(text)

def process_markdown_text(text: str) -> str:
    """Process text as markdown with syntax highlighting"""
    
    # Custom renderer for code blocks
    def highlight_code_block(match):
        language = match.group(1) or 'text'
        code = match.group(2)
        
        try:
            if language.lower() in ['text', 'plain', '']:
                lexer = guess_lexer(code)
            else:
                lexer = get_lexer_by_name(language.lower())
            
            formatter = HtmlFormatter(
                style='github-dark',
                cssclass='highlight',
                linenos=False
            )
            
            highlighted = highlight(code, lexer, formatter)
            return f'<div class="code-block">{highlighted}</div>'
            
        except (ClassNotFound, Exception):
            return f'<pre><code class="language-{language}">{code}</code></pre>'
    
    # Process code blocks first
    code_block_pattern = r'```(\w*)\n(.*?)\n```'
    text = re.sub(code_block_pattern, highlight_code_block, text, flags=re.DOTALL)
    
    # Process inline code
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    
    # Convert markdown to HTML
    html = markdown.markdown(text, extensions=['tables', 'fenced_code'])
    
    return html

# Routes
@app.get("/set-language/{lang}")
async def set_language(lang: str, request: Request):
    """Set language preference via cookie."""
    if lang not in TRANSLATIONS:
        lang = "en"

    # Get referer to redirect back
    referer = request.headers.get("referer", "/")

    # Create response with redirect
    response = RedirectResponse(url=referer, status_code=302)
    # Set language cookie for 1 year
    response.set_cookie(key="lang", value=lang, max_age=31536000)

    return response

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Dashboard homepage with statistics and global search"""
    context = {
        "request": request,
        "current_view": "dashboard"  # Set a special view type for dashboard
    }
    return templates.TemplateResponse("dashboard.html", add_template_context(request, context))

@app.get("/sessions", response_class=HTMLResponse)
async def sessions_view(request: Request, view: str = Query("qwen", regex="^(qwen|claude|cursor|trae|kiro)$")):
    """Sessions page showing projects based on selected view"""
    parser = get_parser(view)
    projects = parser.get_projects()

    # Add source information to distinguish projects
    for project in projects:
        project["source"] = view

    # Group projects by date for the frontend
    grouped_projects = {}
    for project in projects:
        date = project["modified_time_str"].split(' ')[0] if 'modified_time_str' in project else 'Unknown Date'
        if date not in grouped_projects:
            grouped_projects[date] = []
        grouped_projects[date].append(project)

    context = {
        "request": request,
        "projects": projects,
        "grouped_projects": grouped_projects,
        "current_view": view
    }

    return templates.TemplateResponse("index.html", add_template_context(request, context))

@app.get("/api/projects", response_model=List[Project])
async def get_projects(view: str = Query("qwen", regex="^(qwen|claude|cursor|trae|kiro)$")):
    """API endpoint to get projects based on selected view (Qwen or Claude)"""
    parser = get_parser(view)
    projects = parser.get_projects()

    # Add source information to distinguish projects
    for project in projects:
        project["source"] = view

    return projects

@app.get("/project/{project_name}", response_class=HTMLResponse)
async def project_view(request: Request, project_name: str, view: str = Query("qwen", regex="^(qwen|claude|cursor|trae|kiro)$")):
    """Project page showing all sessions"""
    parser = get_parser(view)
    sessions = parser.get_sessions(project_name)

    if not sessions:
        raise HTTPException(status_code=404, detail="Project not found")

    context = {
        "request": request,
        "project_name": project_name,
        "display_name": parser._format_project_name(project_name),
        "sessions": sessions,
        "current_view": view
    }

    return templates.TemplateResponse("project_view.html", add_template_context(request, context))

@app.get("/api/sessions/recent")
async def get_recent_sessions(limit: int = Query(20, le=100, ge=1)):
    """Get recent sessions across all IDEs"""
    all_sessions = []

    for view_name in ["claude", "qwen", "cursor", "trae", "kiro"]:
        try:
            parser = get_parser(view_name)
            projects = parser.get_projects()
        except Exception:
            continue

        for project in projects:
            try:
                sessions = parser.get_sessions(project["name"])
            except Exception:
                continue
            for session in sessions:
                try:
                    all_sessions.append({
                        "view": view_name,
                        "project_name": project.get("name"),
                        "project_display_name": project.get("display_name", project.get("name")),
                        "session_id": session.get("id"),
                        "session_title": session.get("title", session.get("id")),
                        "message_count": session.get("message_count", 0),
                        "modified": session.get("modified"),
                        "size": session.get("size", 0)
                    })
                except Exception:
                    continue

    # Filter out sessions without valid modified time and sort by modified time (descending)
    valid_sessions = [s for s in all_sessions if s.get("modified")]
    valid_sessions.sort(key=lambda x: x["modified"], reverse=True)

    return {
        "sessions": valid_sessions[:limit],
        "total": len(valid_sessions)
    }

@app.get("/api/sessions/{project_name}", response_model=List[Session])
async def get_sessions(project_name: str, view: str = Query("qwen", regex="^(qwen|claude|cursor|trae|kiro)$")):
    """API endpoint to get sessions for a project based on selected view"""
    parser = get_parser(view)
    sessions = parser.get_sessions(project_name)

    if not sessions:
        raise HTTPException(status_code=404, detail="Project not found")

    return sessions

@app.get("/conversation/{project_name}/{session_id}", response_class=HTMLResponse)
async def conversation_view(
    request: Request,
    project_name: str,
    session_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, le=200, ge=10),
    search: Optional[str] = Query(None),
    message_type: Optional[str] = Query(None),
    view: str = Query("qwen", regex="^(qwen|claude|cursor|trae|kiro)$")
):
    """Conversation viewer page"""
    parser = get_parser(view)
    sessions = parser.get_sessions(project_name)

    if not any(s['id'] == session_id for s in sessions):
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation = parser.get_conversation(
        project_name, session_id, page, per_page, search, message_type
    )

    

    # Render markdown content and highlight search terms
    for message in conversation["messages"]:
        if message.get("content"):
            rendered = render_markdown_with_code(message["content"])
            # Highlight search terms if present
            if search:
                message["rendered_content"] = highlight_search_text(rendered, search)
            else:
                message["rendered_content"] = rendered

    context = {
        "request": request,
        "project_name": project_name,
        "session_id": session_id,
        "conversation": conversation,
        "search": search,
        "message_type": message_type,
        "display_name": parser._format_project_name(project_name),
        "current_view": view
    }

    return templates.TemplateResponse("conversation.html", add_template_context(request, context))

@app.get("/api/conversation/{project_name}/{session_id}", response_model=ConversationResponse)
async def get_conversation(
    project_name: str,
    session_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, le=200, ge=10),
    search: Optional[str] = Query(None),
    message_type: Optional[str] = Query(None),
    view: str = Query("qwen", regex="^(qwen|claude|cursor|trae|kiro)$")
):
    """API endpoint to get conversation data based on selected view"""
    parser = get_parser(view)
    sessions = parser.get_sessions(project_name)

    if not any(s['id'] == session_id for s in sessions):
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation = parser.get_conversation(
        project_name, session_id, page, per_page, search, message_type
    )

    return ConversationResponse(**conversation)

@app.get("/search", response_class=HTMLResponse)
async def search_view(request: Request, q: str = Query(..., min_length=1), view: str = Query("qwen", regex="^(qwen|claude|cursor|trae|kiro)$")):
    """Search across all sessions in all projects based on selected view"""
    parser = get_parser(view)

    # Get all projects
    projects = parser.get_projects()

    search_results = []

    # Search in each project's sessions
    for project in projects:
        project_sessions = parser.get_sessions(project["name"])

        for session in project_sessions:
            # Get the full conversation for this session with search
            conversation = parser.get_conversation(
                project["name"], session["id"],
                page=1, per_page=100,  # Get up to 100 messages per session
                search=q  # Use the search query
            )

            if conversation["messages"]:  # If there are matching messages
                # Highlight search terms in first few messages
                first_messages = conversation["messages"][:3]
                for msg in first_messages:
                    if msg.get("content"):
                        msg["content"] = highlight_search_text(msg["content"], q)

                search_results.append({
                    "project": project,
                    "session": session,
                    "matching_messages_count": len(conversation["messages"]),
                    "first_few_messages": first_messages
                })

    context = {
        "request": request,
        "query": q,
        "results": search_results,
        "total_results": len(search_results),
        "current_view": view
    }

    return templates.TemplateResponse("search_results.html", add_template_context(request, context))

@app.get("/api/statistics")
async def get_statistics():
    """Get statistics for all IDE sessions"""
    stats = {}
    total_sessions = 0

    for view_name in ["claude", "qwen", "cursor", "trae", "kiro"]:
        try:
            parser = get_parser(view_name)
            projects = parser.get_projects()
            session_count = sum(p.get("session_count", 0) for p in projects)
            stats[view_name] = {
                "project_count": len(projects),
                "session_count": session_count,
                "available": True
            }
            total_sessions += session_count
        except Exception as e:
            stats[view_name] = {
                "project_count": 0,
                "session_count": 0,
                "available": False,
                "error": str(e)
            }

    return {
        "stats": stats,
        "total_sessions": total_sessions,
        "total_projects": sum(s["project_count"] for s in stats.values())
    }

@app.get("/api/search/global")
async def global_search(q: str = Query(..., min_length=1), limit: int = Query(50, le=200, ge=1)):
    """Search across all IDEs and sessions"""
    search_results = []

    for view_name in ["claude", "qwen", "cursor", "trae", "kiro"]:
        try:
            parser = get_parser(view_name)
            projects = parser.get_projects()
        except Exception:
            continue

        for project in projects:
            try:
                sessions = parser.get_sessions(project.get("name"))
            except Exception:
                continue

            for session in sessions:
                try:
                    conversation = parser.get_conversation(
                        project.get("name"), session.get("id"),
                        page=1, per_page=100,
                        search=q
                    )
                except Exception:
                    continue

                if conversation.get("messages"):
                    first_messages = conversation["messages"][:3]
                    try:
                        search_results.append({
                            "view": view_name,
                            "project_name": project.get("name"),
                            "project_display_name": project.get("display_name", project.get("name")),
                            "session_id": session.get("id"),
                            "session_title": session.get("title", session.get("id")),
                            "message_count": session.get("message_count", 0),
                            "matching_count": len(conversation.get("messages", [])),
                            "first_messages": first_messages,
                            "modified": session.get("modified")
                        })
                    except Exception:
                        continue

    # Filter out results without valid modified time and sort by modified time (descending)
    valid_results = [r for r in search_results if r.get("modified")]
    valid_results.sort(key=lambda x: x["modified"], reverse=True)

    return {
        "results": valid_results[:limit],
        "total": len(valid_results),
        "query": q
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    claude_parser = get_parser("claude")
    qwen_parser = get_parser("qwen")
    cursor_parser = get_parser("cursor")
    trae_parser = get_parser("trae")
    kiro_parser = get_parser("kiro")

    claude_path = os.environ.get("CLAUDE_PROJECTS_PATH", str(Path.home() / ".claude" / "projects"))
    qwen_path = os.environ.get("QWEN_PROJECTS_PATH", str(Path.home() / ".qwen" / "tmp"))
    cursor_path = os.environ.get("CURSOR_WORKSPACE_STORAGE_PATH", str(Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage"))
    trae_path = os.environ.get("TRAE_WORKSPACE_STORAGE_PATH", str(Path.home() / "Library" / "Application Support" / "Trae" / "User" / "workspaceStorage"))
    kiro_path = os.environ.get("KIRO_WORKSPACE_STORAGE_PATH", str(Path.home() / "Library" / "Application Support" / "Kiro" / "User" / "workspaceStorage"))

    claude_projects_exist = os.path.exists(claude_path)
    qwen_projects_exist = os.path.exists(qwen_path)
    cursor_projects_exist = os.path.exists(cursor_path)
    trae_projects_exist = os.path.exists(trae_path)
    kiro_projects_exist = os.path.exists(kiro_path)

    trae_key_samples = []
    kiro_key_samples = []
    if trae_projects_exist:
        import sqlite3
        base = trae_path
        for pr in trae_parser.get_projects()[:5]:
            state_db = os.path.join(base, pr["name"], "state.vscdb")
            if os.path.exists(state_db):
                try:
                    conn = sqlite3.connect(state_db)
                    cur = conn.cursor()
                    key = trae_parser._find_state_key(cur)
                    conn.close()
                except Exception:
                    key = None
                trae_key_samples.append({"project": pr["display_name"], "key": key})
    if kiro_projects_exist:
        import sqlite3
        base = kiro_path
        for pr in kiro_parser.get_projects()[:5]:
            state_db = os.path.join(base, pr["name"], "state.vscdb")
            if os.path.exists(state_db):
                try:
                    conn = sqlite3.connect(state_db)
                    cur = conn.cursor()
                    key = kiro_parser._find_state_key(cur)
                    conn.close()
                except Exception:
                    key = None
                kiro_key_samples.append({"project": pr["display_name"], "key": key})

    return {
        "status": "aicode-viewer healthy",
        "version": "1.1.2",
        "claude_projects_path": claude_path,
        "qwen_projects_path": qwen_path,
        "cursor_workspace_path": cursor_path,
        "claude_projects_directory_exists": claude_projects_exist,
        "qwen_projects_directory_exists": qwen_projects_exist,
        "cursor_workspace_directory_exists": cursor_projects_exist,
        "trae_workspace_directory_exists": trae_projects_exist,
        "kiro_workspace_directory_exists": kiro_projects_exist,
        "claude_projects_count": len(claude_parser.get_projects()) if claude_projects_exist else 0,
        "qwen_projects_count": len(qwen_parser.get_projects()) if qwen_projects_exist else 0,
        "cursor_projects_count": len(cursor_parser.get_projects()) if cursor_projects_exist else 0,
        "trae_projects_count": len(trae_parser.get_projects()) if trae_projects_exist else 0,
        "kiro_projects_count": len(kiro_parser.get_projects()) if kiro_projects_exist else 0,
        "total_projects_count": (len(claude_parser.get_projects()) if claude_projects_exist else 0) +
                                (len(qwen_parser.get_projects()) if qwen_projects_exist else 0) +
                                (len(cursor_parser.get_projects()) if cursor_projects_exist else 0) +
                                (len(trae_parser.get_projects()) if trae_projects_exist else 0) +
                                (len(kiro_parser.get_projects()) if kiro_projects_exist else 0),
        "trae_key_samples": trae_key_samples,
        "kiro_key_samples": kiro_key_samples
    }


# ==================== Favorites API Routes ====================

@app.post("/api/favorites", response_model=Dict[str, Any])
async def create_favorite(request: CreateFavoriteRequest):
    """Create a new favorite"""
    try:
        # Generate message hash if message content provided
        message_hash = None
        if request.message_content:
            message_hash = FavoritesDB.generate_message_hash(request.message_content)

        favorite_id = favorites_db.add_favorite(
            favorite_type=request.type,
            view=request.view,
            project_name=request.project_name,
            session_id=request.session_id,
            title=request.title,
            annotation=request.annotation,
            content_preview=request.content_preview,
            message_line=request.message_line,
            message_hash=message_hash,
            tags=request.tags
        )

        return {"success": True, "favorite_id": favorite_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create favorite: {str(e)}")


@app.get("/api/favorites", response_model=FavoritesListResponse)
async def get_favorites(
    type: Optional[str] = Query(None, regex="^(session|message)$"),
    view: Optional[str] = Query(None),
    project_name: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    include_stats: bool = Query(False)
):
    """Get favorites with filters"""
    try:
        favorites = favorites_db.get_favorites(
            favorite_type=type,
            view=view,
            project_name=project_name,
            tag=tag,
            search=search,
            limit=limit,
            offset=offset
        )

        # Convert to Pydantic models
        favorite_models = []
        for fav in favorites:
            # Convert tags to TagModel
            tag_models = [TagModel(**t) for t in fav.get('tags', [])]

            favorite_models.append(FavoriteModel(
                id=fav['id'],
                type=fav['type'],
                view=fav['view'],
                project_name=fav['project_name'],
                session_id=fav['session_id'],
                message_line=fav.get('message_line'),
                message_hash=fav.get('message_hash'),
                title=fav['title'],
                annotation=fav.get('annotation'),
                content_preview=fav.get('content_preview'),
                tags=tag_models,
                created_at=fav['created_at'],
                updated_at=fav['updated_at']
            ))

        statistics = None
        if include_stats:
            statistics = favorites_db.get_statistics()

        return FavoritesListResponse(
            favorites=favorite_models,
            total=len(favorite_models),
            statistics=statistics
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get favorites: {str(e)}")


@app.get("/api/favorites/statistics")
async def get_favorites_statistics():
    """Get favorites statistics"""
    try:
        return favorites_db.get_statistics()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@app.get("/api/favorites/check/{view}/{project_name}/{session_id}")
async def check_favorite_exists(
    view: str,
    project_name: str,
    session_id: str,
    message_line: Optional[int] = Query(None)
):
    """Check if a favorite exists"""
    try:
        favorite_id = favorites_db.check_favorite_exists(
            view=view,
            project_name=project_name,
            session_id=session_id,
            message_line=message_line
        )

        return {
            "exists": favorite_id is not None,
            "favorite_id": favorite_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check favorite: {str(e)}")


@app.get("/api/tags", response_model=List[TagModel])
async def get_all_tags():
    """Get all tags with usage counts"""
    try:
        tags = favorites_db.get_all_tags()
        return [TagModel(**tag) for tag in tags]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tags: {str(e)}")


@app.get("/api/favorites/{favorite_id}", response_model=FavoriteModel)
async def get_favorite(favorite_id: str):
    """Get a single favorite by ID"""
    try:
        fav = favorites_db.get_favorite_by_id(favorite_id)
        if not fav:
            raise HTTPException(status_code=404, detail="Favorite not found")

        tag_models = [TagModel(**t) for t in fav.get('tags', [])]

        return FavoriteModel(
            id=fav['id'],
            type=fav['type'],
            view=fav['view'],
            project_name=fav['project_name'],
            session_id=fav['session_id'],
            message_line=fav.get('message_line'),
            message_hash=fav.get('message_hash'),
            title=fav['title'],
            annotation=fav.get('annotation'),
            content_preview=fav.get('content_preview'),
            tags=tag_models,
            created_at=fav['created_at'],
            updated_at=fav['updated_at']
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get favorite: {str(e)}")


@app.put("/api/favorites/{favorite_id}", response_model=Dict[str, Any])
async def update_favorite(favorite_id: str, request: UpdateFavoriteRequest):
    """Update favorite annotation and/or tags"""
    try:
        if request.annotation is not None:
            success = favorites_db.update_annotation(favorite_id, request.annotation)
            if not success:
                raise HTTPException(status_code=404, detail="Favorite not found")

        if request.tags is not None:
            favorites_db.update_favorite_tags(favorite_id, request.tags)

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update favorite: {str(e)}")


@app.delete("/api/favorites/{favorite_id}", response_model=Dict[str, Any])
async def delete_favorite(favorite_id: str):
    """Delete a favorite"""
    try:
        success = favorites_db.remove_favorite(favorite_id)
        if not success:
            raise HTTPException(status_code=404, detail="Favorite not found")

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete favorite: {str(e)}")


@app.get("/favorites", response_class=HTMLResponse)
async def favorites_page(request: Request):
    """Favorites page"""
    context = {
        "request": request,
        "current_view": "favorites"
    }
    return templates.TemplateResponse("favorites.html", add_template_context(request, context))
