import json
import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import re
from datetime import datetime
import difflib

class JSONLParser:
    def __init__(self, projects_path: str = None, parser_type: str = "claude"):
        """
        Initialize parser for either Claude (.jsonl) or Qwen (.json) files

        Args:
            projects_path: Path to projects directory
            parser_type: Either "claude" for JSONL format or "qwen" for JSON format
        """
        self.parser_type = parser_type
        if parser_type == "claude":
            self.projects_path = projects_path or os.path.expanduser("~/.claude/projects")
        elif parser_type == "qwen":
            self.projects_path = projects_path or os.path.expanduser("~/.qwen/tmp")
        elif parser_type == "cursor":
            default_path = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Cursor", "User", "workspaceStorage")
            self.projects_path = projects_path or os.environ.get("CURSOR_WORKSPACE_STORAGE_PATH", default_path)
        elif parser_type == "trae":
            default_path = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Trae", "User", "workspaceStorage")
            self.projects_path = projects_path or os.environ.get("TRAE_WORKSPACE_STORAGE_PATH", default_path)
        elif parser_type == "kiro":
            # Kiro primary path is workspaceStorage (contains workspace.json)
            default_path = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Kiro", "User", "workspaceStorage")
            self.projects_path = projects_path or os.environ.get("KIRO_WORKSPACE_STORAGE_PATH", default_path)
            # Sessions are stored in globalStorage workspace-sessions
            self.kiro_sessions_path = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Kiro", "User", "globalStorage", "kiro.kiroagent", "workspace-sessions")
        else:
            raise ValueError(f"Unsupported parser type: {parser_type}")
    
    def get_projects(self) -> List[Dict]:
        """Scan and return all projects based on parser type"""
        import os
        from datetime import datetime
        projects = []
        if not os.path.exists(self.projects_path):
            return projects

        for project_dir in os.listdir(self.projects_path):
            project_path = os.path.join(self.projects_path, project_dir)
            if os.path.isdir(project_path):
                if self.parser_type == "claude":
                    session_files = [f for f in os.listdir(project_path) if f.endswith('.jsonl')]
                elif self.parser_type == "qwen":
                    chats_path = os.path.join(project_path, 'chats')
                    if os.path.exists(chats_path):
                        session_files = [f for f in os.listdir(chats_path) if f.endswith('.json')]
                    else:
                        session_files = []
                elif self.parser_type == "kiro":
                    # Kiro: Read workspace.json to get folder path, then map to sessions
                    workspace_json = os.path.join(project_path, 'workspace.json')
                    if os.path.exists(workspace_json):
                        try:
                            import json
                            with open(workspace_json, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                                folder_uri = data.get('folder', '')
                                folder_path = folder_uri.replace('file://', '')

                                # Convert to base64 for sessions lookup
                                sessions_dir_name = self._path_to_base64(folder_path)
                                sessions_path = os.path.join(self.kiro_sessions_path, sessions_dir_name)

                                # Check sessions.json
                                sessions_json_file = os.path.join(sessions_path, 'sessions.json')
                                if os.path.exists(sessions_json_file):
                                    with open(sessions_json_file, 'r', encoding='utf-8') as sf:
                                        sessions_data = json.load(sf)
                                        session_files = [s['sessionId'] + '.json' for s in sessions_data if isinstance(s, dict)]
                                else:
                                    session_files = []
                        except Exception as e:
                            session_files = []
                    else:
                        session_files = []
                elif self.parser_type in ["cursor", "trae"]:
                    workspace_json = os.path.join(project_path, 'workspace.json')
                    state_db = os.path.join(project_path, 'state.vscdb')
                    if os.path.exists(state_db):
                        session_files = ['state.vscdb']
                    else:
                        session_files = []
                
                # Get the modification time of the project directory
                mtime = os.path.getmtime(project_path)
                mod_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

                display_name = self._format_project_name(project_dir)
                if self.parser_type in ["cursor", "trae"]:
                    # Extra safety: recompute display name from workspace.json directly
                    display_name = self._format_cursor_display_name(project_dir) or display_name
                elif self.parser_type == "kiro":
                    # For Kiro, decode the base64 directory name
                    display_name = self._format_kiro_display_name(project_dir) or display_name
                projects.append({
                    "name": project_dir,
                    "display_name": display_name,
                    "path": project_path,
                    "session_count": len(session_files),
                    "sessions": session_files,
                    "modified_time": mtime,  # Add modification time for sorting
                    "modified_time_str": mod_time,  # Add formatted modification time for display
                    "source": self.parser_type  # Add source information
                })

        # Sort projects by modification time in descending order (newest first)
        return sorted(projects, key=lambda x: x["modified_time"], reverse=True)
    
    def get_sessions(self, project_name: str) -> List[Dict]:
        """Get all session files for a project with metadata"""
        project_path = os.path.join(self.projects_path, project_name)
        sessions = []

        if not os.path.exists(project_path):
            return sessions

        if self.parser_type == "claude":
            # Process Claude JSONL files
            for filename in os.listdir(project_path):
                if filename.endswith('.jsonl'):
                    file_path = os.path.join(project_path, filename)
                    file_stats = os.stat(file_path)

                    # Count messages in file
                    message_count = self._count_messages(file_path)

                    # Extract session title from first user message
                    session_title = self._extract_session_title(file_path)

                    sessions.append({
                        "id": filename.replace('.jsonl', ''),
                        "filename": filename,
                        "path": file_path,
                        "size": file_stats.st_size,
                        "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                        "message_count": message_count,
                        "title": session_title
                    })
        elif self.parser_type == "qwen":
            # Process Qwen JSON files in chats subdirectory
            chats_path = os.path.join(project_path, 'chats')
            if os.path.exists(chats_path):
                for filename in os.listdir(chats_path):
                    if filename.endswith('.json'):
                        file_path = os.path.join(chats_path, filename)
                        file_stats = os.stat(file_path)

                        # Count messages in file
                        message_count = self._count_messages(file_path)

                        # Extract session title from first user message
                        session_title = self._extract_session_title(file_path)

                        sessions.append({
                            "id": filename.replace('.json', ''),
                            "filename": filename,
                            "path": file_path,
                            "size": file_stats.st_size,
                            "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                            "message_count": message_count,
                            "title": session_title
                        })
        elif self.parser_type == "kiro":
            # Kiro: Get folder path from workspace.json, then map to sessions directory
            workspace_json = os.path.join(project_path, 'workspace.json')
            if os.path.exists(workspace_json):
                try:
                    with open(workspace_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        folder_uri = data.get('folder', '')
                        folder_path = folder_uri.replace('file://', '')

                        # Map to sessions directory
                        sessions_dir_name = self._path_to_base64(folder_path)
                        sessions_path = os.path.join(self.kiro_sessions_path, sessions_dir_name)
                        sessions_json_file = os.path.join(sessions_path, 'sessions.json')

                        if os.path.exists(sessions_json_file):
                            with open(sessions_json_file, 'r', encoding='utf-8') as sf:
                                sessions_data = json.load(sf)
                                for session_info in sessions_data:
                                    session_id = session_info.get('sessionId')
                                    session_file = os.path.join(sessions_path, f"{session_id}.json")
                                    if os.path.exists(session_file):
                                        file_stats = os.stat(session_file)
                                        # Count messages by reading the JSON file
                                        try:
                                            with open(session_file, 'r', encoding='utf-8') as ssf:
                                                session_content = json.load(ssf)
                                                message_count = len(session_content.get('history', []))
                                        except:
                                            message_count = 0

                                        sessions.append({
                                            "id": session_id,
                                            "filename": f"{session_id}.json",
                                            "path": session_file,
                                            "size": file_stats.st_size,
                                            "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                                            "message_count": message_count,
                                            "title": session_info.get('title', 'Untitled Session')
                                        })
                except Exception as e:
                    pass
        elif self.parser_type in ["cursor", "trae"]:
            state_db = os.path.join(project_path, 'state.vscdb')
            if os.path.exists(state_db):
                try:
                    message_count = self._cursor_count_prompts(state_db)
                except Exception:
                    message_count = 0
                try:
                    session_key = self._discover_state_key(state_db)
                except Exception:
                    session_key = "aiService.prompts"

                # Extract session title from first user message
                session_title = self._extract_session_title(state_db)

                file_stats = os.stat(state_db)
                sessions.append({
                    "id": session_key or "aiService.prompts",
                    "filename": "state.vscdb",
                    "path": state_db,
                    "size": file_stats.st_size,
                    "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                    "message_count": message_count,
                    "title": session_title
                })

        return sorted(sessions, key=lambda x: x["modified"], reverse=True)
    
    def get_conversation(
        self,
        project_name: str,
        session_id: str,
        page: int = 1,
        per_page: int = 50,
        search: Optional[str] = None,
        message_type: Optional[str] = None
    ) -> Dict:
        """Get paginated conversation data with optional filtering"""

        if self.parser_type == "claude":
            session_path = os.path.join(self.projects_path, project_name, f"{session_id}.jsonl")
        elif self.parser_type == "qwen":
            project_path = os.path.join(self.projects_path, project_name)
            session_path = os.path.join(project_path, 'chats', f"{session_id}.json")
        elif self.parser_type == "kiro":
            # Kiro: Get folder path from workspace.json, then map to sessions directory
            project_path = os.path.join(self.projects_path, project_name)
            workspace_json = os.path.join(project_path, 'workspace.json')

            if os.path.exists(workspace_json):
                try:
                    with open(workspace_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        folder_uri = data.get('folder', '')
                        folder_path = folder_uri.replace('file://', '')

                        # Map to sessions directory
                        sessions_dir_name = self._path_to_base64(folder_path)
                        sessions_path = os.path.join(self.kiro_sessions_path, sessions_dir_name)
                        session_path = os.path.join(sessions_path, f"{session_id}.json")
                except:
                    return {"messages": [], "total": 0, "page": page, "per_page": per_page}
            else:
                return {"messages": [], "total": 0, "page": page, "per_page": per_page}
        elif self.parser_type in ["cursor", "trae"]:
            project_path = os.path.join(self.projects_path, project_name)
            session_path = os.path.join(project_path, 'state.vscdb')
        else:
            return {"messages": [], "total": 0, "page": page, "per_page": per_page}

        if not os.path.exists(session_path):
            return {"messages": [], "total": 0, "page": page, "per_page": per_page}

        messages = []

        if self.parser_type == "claude":
            # Read Claude JSONL format
            with open(session_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    try:
                        data = json.loads(line.strip())

                        # Parse different message types
                        parsed_message = self._parse_message(data, line_num)

                        # Apply filters
                        if self._should_include_message(parsed_message, search, message_type):
                            messages.append(parsed_message)

                    except json.JSONDecodeError:
                        continue
        elif self.parser_type == "qwen":
            # Read Qwen JSON format
            with open(session_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

                for idx, msg_data in enumerate(session_data.get('messages', []), 1):
                    # Parse different message types
                    parsed_message = self._parse_message(msg_data, idx)

                    # Apply filters
                    if self._should_include_message(parsed_message, search, message_type):
                        messages.append(parsed_message)
        elif self.parser_type == "kiro":
            # Read Kiro JSON session format
            with open(session_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
                history = session_data.get('history', [])

                for idx, msg_data in enumerate(history, 1):
                    parsed_message = self._parse_kiro_message(msg_data, idx)
                    if self._should_include_message(parsed_message, search, message_type):
                        messages.append(parsed_message)
        elif self.parser_type in ["cursor", "trae"]:
            prompts = self._cursor_query_prompts(session_path)
            for idx, msg_data in enumerate(prompts, 1):
                parsed_message = self._parse_cursor_message(msg_data, idx)
                if self._should_include_message(parsed_message, search, message_type):
                    messages.append(parsed_message)

        # Pagination
        total = len(messages)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_messages = messages[start_idx:end_idx]

        return {
            "messages": paginated_messages,
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": (total + per_page - 1) // per_page
        }
    
    def _parse_message(self, data: Dict, line_num: int) -> Dict:
        """Parse different types of messages based on parser type"""
        if self.parser_type == "claude":
            # Original Claude JSONL message parsing
            base_message = {
                "line_number": line_num,
                "raw_type": data.get("type", "unknown"),
                "timestamp": data.get("timestamp"),
            }

            # Handle different message types
            if data.get("type") == "summary":
                return {
                    **base_message,
                    "type": "summary",
                    "content": data.get("summary", ""),
                    "uuid": data.get("leafUuid", ""),
                    "display_type": "Summary"
                }
            elif data.get("type") in ["user", "assistant"]:
                # Direct user/assistant messages (new format)
                message_data = data.get("message", {})
                content = message_data.get("content", "")

                if isinstance(content, list):
                    # Handle structured content (tool calls, etc.)
                    content = self._parse_structured_content(content)

                return {
                    **base_message,
                    "type": "message",
                    "role": data.get("type"),
                    "content": content,
                    "display_type": data.get("type", "").title(),
                    "has_code": self._contains_code(content)
                }
            elif "role" in data:
                # Legacy format - User/Assistant messages
                content = data.get("content", "")
                if isinstance(content, list):
                    # Handle structured content (tool calls, etc.)
                    content = self._parse_structured_content(content)

                return {
                    **base_message,
                    "type": "message",
                    "role": data.get("role"),
                    "content": content,
                    "display_type": data.get("role", "").title(),
                    "has_code": self._contains_code(content)
                }
            else:
                # Other types (system messages, etc.)
                return {
                    **base_message,
                    "type": "other",
                    "content": json.dumps(data, indent=2),
                    "display_type": data.get("type", "Unknown").title()
                }
        elif self.parser_type == "qwen":
            # Qwen JSON message parsing
            base_message = {
                "line_number": line_num,
                "timestamp": data.get("timestamp"),
            }

            message_type = data.get("type", "unknown")

            if message_type == "user":
                return {
                    **base_message,
                    "type": "message",
                    "role": "user",
                    "content": data.get("content", ""),
                    "display_type": "User",
                    "has_code": self._contains_code(data.get("content", ""))
                }
            elif message_type == "qwen":
                return {
                    **base_message,
                    "type": "message",
                    "role": "assistant",  # Map 'qwen' to 'assistant' to match UI expectations
                    "content": data.get("content", ""),
                    "display_type": "Assistant",
                    "has_code": self._contains_code(data.get("content", ""))
                }
            else:
                # Handle other message types
                return {
                    **base_message,
                    "type": "other",
                    "content": json.dumps(data, indent=2),
                    "display_type": message_type.title()
                }
        
    def _parse_cursor_message(self, data: Dict, line_num: int) -> Dict:
        base_message = {
            "line_number": line_num,
            "timestamp": data.get("timestamp"),
        }
        role = data.get("role")
        if role is None:
            if data.get("from"):
                role = "user" if str(data.get("from")).lower() == "user" else "assistant"
            elif data.get("isUser") is not None:
                role = "user" if data.get("isUser") else "assistant"
            else:
                role = "assistant" if data.get("outputText") else "user"
        content = (
            data.get("content") or
            data.get("text") or
            data.get("prompt") or
            data.get("message") or
            data.get("inputText") or
            data.get("outputText") or
            data.get("value") or
            data.get("body") or
            data.get("textContent") or
            ""
        )
        if isinstance(content, list):
            content = "\n\n".join(str(x) for x in content)
        return {
            **base_message,
            "type": "message",
            "role": role,
            "content": content,
            "display_type": "User" if role == "user" else "Assistant",
            "has_code": self._contains_code(content)
        }
    
    def _parse_structured_content(self, content_list: List) -> str:
        """Parse structured content from tool calls"""
        parsed_parts = []
        for item in content_list:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    # Regular text content - preserve line breaks
                    text_content = item.get("text", "")
                    parsed_parts.append(text_content)
                elif item.get("type") == "image":
                    # Image content
                    parsed_parts.append("📷 **[Image attached]**")
                elif item.get("type") == "tool_use":
                    # Tool use - format nicely
                    tool_name = item.get("name", "unknown_tool")
                    tool_params = item.get("input", {})
                    
                    # Special handling for Edit tool calls - show as diff
                    if tool_name == "Edit" and tool_params.get("old_string") and tool_params.get("new_string"):
                        file_path = tool_params.get("file_path", "unknown_file")
                        old_string = tool_params.get("old_string", "")
                        new_string = tool_params.get("new_string", "")
                        
                        # Generate diff HTML
                        diff_html = self._generate_diff_html(old_string, new_string, file_path)
                        parsed_parts.append(f"✏️ **Edit Tool: {file_path}**\n{diff_html}")
                    else:
                        # Regular tool use - format parameters readably
                        if tool_params:
                            param_lines = []
                            for key, value in tool_params.items():
                                if isinstance(value, str) and len(value) > 100:
                                    # Truncate very long strings
                                    param_lines.append(f"  **{key}**: {value[:100]}...")
                                else:
                                    param_lines.append(f"  **{key}**: {value}")
                            params_text = "\n".join(param_lines)
                        else:
                            params_text = "  (no parameters)"
                        
                        parsed_parts.append(f"🔧 **Tool Used: {tool_name}**\n{params_text}")
                    
                elif item.get("type") == "tool_result":
                    # Tool result - handle different result types
                    result_content = item.get("content", "")
                    
                    # Check for Edit tool results with diff information
                    tool_use_result = item.get("toolUseResult", {})
                    if (tool_use_result and 
                        tool_use_result.get("oldString") and 
                        tool_use_result.get("newString")):
                        # This is an Edit tool result with diff data
                        file_path = tool_use_result.get("filePath", "unknown_file")
                        old_string = tool_use_result.get("oldString", "")
                        new_string = tool_use_result.get("newString", "")
                        
                        # Generate diff HTML for tool result
                        diff_html = self._generate_diff_html(old_string, new_string, file_path)
                        parsed_parts.append(f"✅ **Edit Result: {file_path}**\n{diff_html}")
                        
                        # Also show the regular tool output if it contains useful info
                        if isinstance(result_content, str) and result_content.strip():
                            parsed_parts.append(f"📋 **Tool Output:**\n```\n{result_content}\n```")
                    else:
                        # Regular tool result handling
                        if isinstance(result_content, str):
                            # Check if already truncated in JSONL or if we need to truncate
                            if "... (output truncated)" in result_content:
                                # Already truncated in JSONL - keep as is
                                parsed_parts.append(f"📋 **Tool Output:**\n```\n{result_content}\n```")
                            elif len(result_content) > 5000:
                                # Only truncate very long results (increased limit)
                                result_content = result_content[:5000] + "\n... (output truncated by viewer)"
                                parsed_parts.append(f"📋 **Tool Output:**\n```\n{result_content}\n```")
                            else:
                                # Show full result
                                parsed_parts.append(f"📋 **Tool Output:**\n```\n{result_content}\n```")
                        else:
                            parsed_parts.append(f"📋 **Tool Output:**\n```json\n{json.dumps(result_content, indent=2)}\n```")
                else:
                    # Unknown content type
                    parsed_parts.append(f"ℹ️ **{item.get('type', 'Unknown')}:**\n```json\n{json.dumps(item, indent=2)}\n```")
            elif isinstance(item, str):
                # Simple string content
                parsed_parts.append(item)
            else:
                # Other types
                parsed_parts.append(str(item))
        
        return "\n\n".join(parsed_parts)
    
    def _contains_code(self, content: str) -> bool:
        """Check if content contains code blocks"""
        if not isinstance(content, str):
            return False
        
        # Look for common code patterns
        code_patterns = [
            r'```[\w]*\n',  # Markdown code blocks
            r'def \w+\(',   # Python functions
            r'class \w+',   # Class definitions
            r'import \w+',  # Import statements
            r'from \w+',    # From imports
            r'<[a-zA-Z][^>]*>',  # HTML tags
            r'\$\s*\w+',    # Shell commands
        ]
        
        return any(re.search(pattern, content) for pattern in code_patterns)
    
    def _should_include_message(
        self, 
        message: Dict, 
        search: Optional[str], 
        message_type: Optional[str]
    ) -> bool:
        """Apply search and type filters"""
        
        # Type filter
        if message_type and message.get("role", "").lower() != message_type.lower():
            return False
        
        # Search filter
        if search:
            search_text = search.lower()
            content = str(message.get("content", "")).lower()
            
            if search_text not in content:
                return False
        
        return True
    
    def _count_messages(self, file_path: str) -> int:
        """Count total messages in either JSONL or JSON file"""
        try:
            if self.parser_type == "claude":
                with open(file_path, 'r', encoding='utf-8') as f:
                    return sum(1 for line in f if line.strip())
            elif self.parser_type == "qwen":
                with open(file_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    return len(session_data.get('messages', []))
            elif self.parser_type in ["cursor", "trae", "kiro"]:
                return self._cursor_count_prompts(file_path)
        except:
            return 0
    
    def _format_project_name(self, project_dir: str) -> str:
        """Convert project directory name to readable format"""
        if self.parser_type == "claude":
            # Convert Claude project directory names to readable format
            if project_dir.startswith('-'):
                # Claude directories often start with dash followed by path components joined with dashes
                # Example: -Users-lohas-docker becomes Users/lohas/docker
                clean_name = project_dir[1:]  # Remove leading dash
                # Replace dashes with forward slashes to show as path
                path_parts = clean_name.split('-')

                # Only return the last 3 parts to avoid overly long paths
                if len(path_parts) > 3:
                    path_parts = path_parts[-3:]  # Take only the last 3 parts

                path_name = '/'.join(path_parts)

                # Return the path-like format
                return path_name
            else:
                # If no dash prefix, return as is
                return project_dir
        elif self.parser_type == "qwen":
            # For Qwen, look for more specific project information
            import os
            import json
            import re

            # The hash directory name is typically derived from the project's root directory path
            # We'll try multiple approaches to get a meaningful project name

            project_path = os.path.join(self.projects_path, project_dir)

            # First, check if there's a QWEN.md file with project info
            qwen_md_path = os.path.join(project_path, 'QWEN.md')
            if os.path.exists(qwen_md_path):
                try:
                    with open(qwen_md_path, 'r', encoding='utf-8') as f:
                        first_line = f.readline().strip()
                        if first_line.startswith('# '):
                            return first_line[2:]  # Remove '# ' prefix
                        elif first_line:
                            return first_line
                except:
                    pass

            # Try to infer the original project directory from the hash
            # Since Qwen identifies project roots with .git, we can look for patterns in session content
            chats_path = os.path.join(project_path, 'chats')
            if os.path.exists(chats_path):
                # Look for the most recent or first session file
                session_files = [f for f in os.listdir(chats_path) if f.endswith('.json')]
                if session_files:
                    # Sort by modification time to get the most recent first
                    session_files.sort(key=lambda x: os.path.getmtime(os.path.join(chats_path, x)), reverse=True)
                    for session_file in session_files:
                        try:
                            with open(os.path.join(chats_path, session_file), 'r', encoding='utf-8') as f:
                                session_data = json.load(f)

                                # Get the actual project path from the session data if available
                                project_hash_in_session = session_data.get('projectHash', '')
                                if project_hash_in_session == project_dir:
                                    # Look for project directory path in the messages
                                    messages = session_data.get('messages', [])
                                    if messages:
                                        # Look for any file paths that might indicate the original project directory
                                        for msg in messages[:10]:  # Check first 10 messages
                                            content = msg.get('content', '')
                                            # Look for patterns like /Users/username/path/to/project/ or similar
                                            # Try to identify the project root directory based on common patterns
                                            # Usually it's the directory that contains a .git folder
                                            matches = re.findall(r'/Users/[^/\s"]*/([^/\s"]+)/', content)
                                            if matches:
                                                # Find the most project-like directory name (not system directories)
                                                for match in reversed(matches):  # Check from most specific to least
                                                    if match and match not in ['.git', '.npm', '.pyenv', '.config', '.ssh', '.vscode', '.idea', 'node_modules']:
                                                        return match
                        except:
                            continue

            # Try to find if there's information in logs
            logs_path = os.path.join(project_path, 'logs.json')
            if os.path.exists(logs_path):
                try:
                    with open(logs_path, 'r', encoding='utf-8') as f:
                        logs_data = json.load(f)
                        if logs_data and len(logs_data) > 0:
                            # Look through logs for file paths
                            for log_entry in logs_data[:10]:  # Check first 10 entries
                                message = log_entry.get('message', '')
                                matches = re.findall(r'/Users/[^/\s"]*/([^/\s"]+)/', message)
                                if matches:
                                    for match in reversed(matches):  # Check from most specific to least
                                        if match and match not in ['.git', '.npm', '.pyenv', '.config', '.ssh', '.vscode', '.idea', 'node_modules']:
                                            return match
                except:
                    pass

            # If still no meaningful name found, extract potential project name from the hash indirectly
            # by looking at session content for file paths related to this project
            potential_project_names = []
            if os.path.exists(chats_path):
                session_files = [f for f in os.listdir(chats_path) if f.endswith('.json')]
                for session_file in session_files:
                    try:
                        with open(os.path.join(chats_path, session_file), 'r', encoding='utf-8') as f:
                            session_data = json.load(f)
                            messages = session_data.get('messages', [])
                            for msg in messages:
                                content = msg.get('content', '')
                                # Look for common project file patterns that might reveal the project name
                                patterns = [
                                    r'cd\s+([^\s]+)',  # cd commands often reveal project directory
                                    r'pwd.*?([^\s/]+)$', # pwd commands
                                    r'(/Users/[^/\s"]*/([^/\s"]+)/)', # Full paths again
                                ]

                                for pattern in patterns:
                                    matches = re.findall(pattern, content, re.MULTILINE)
                                    for match in matches:
                                        # If it's a tuple (from capturing groups), get the relevant part
                                        if isinstance(match, tuple):
                                            match = match[-1] if match[-1] else match[0]

                                        if match and match not in ['.git', '.npm', '.pyenv', '.config', '.ssh', '.vscode', '.idea', 'node_modules', '~', 'tmp', 'home', 'Users']:
                                            potential_project_names.append(match)
                    except:
                        continue

            # If we found potential project names, return the most common one
            if potential_project_names:
                # Return the most frequent name
                from collections import Counter
                name_counts = Counter(potential_project_names)
                most_common = name_counts.most_common(1)
                if most_common:
                    return most_common[0][0]

            # If no specific name found, return a cleaned version of the hash
            return project_dir[:12]  # Shorten the hash for readability
        elif self.parser_type in ["cursor", "trae", "kiro"]:
            import os
            from urllib.parse import urlparse
            workspace_path = os.path.join(self.projects_path, project_dir)
            workspace_json = os.path.join(workspace_path, 'workspace.json')
            def _extract_path(data_obj):
                if not isinstance(data_obj, (dict, str)):
                    return None
                if isinstance(data_obj, str):
                    return data_obj
                cand = (
                    data_obj.get('folder') or
                    data_obj.get('path') or
                    data_obj.get('workspace') or
                    data_obj.get('workspacePath') or
                    data_obj.get('name')
                )
                if isinstance(cand, dict):
                    cand = cand.get('path') or cand.get('folder')
                if not cand and isinstance(data_obj.get('folders'), list) and data_obj['folders']:
                    first = data_obj['folders'][0]
                    if isinstance(first, dict):
                        cand = first.get('path') or first.get('folder') or first.get('name')
                    elif isinstance(first, str):
                        cand = first
                # VS Code style: configuration could be JSON string containing folders
                conf = data_obj.get('configuration')
                if not cand and conf:
                    try:
                        conf_obj = conf if isinstance(conf, dict) else json.loads(conf)
                        if isinstance(conf_obj, dict) and isinstance(conf_obj.get('folders'), list) and conf_obj['folders']:
                            first = conf_obj['folders'][0]
                            if isinstance(first, dict):
                                cand = first.get('path') or first.get('folder') or first.get('name')
                            elif isinstance(first, str):
                                cand = first
                    except Exception:
                        pass
                return cand
            full_path = None
            if os.path.exists(workspace_json):
                try:
                    with open(workspace_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        full_path = _extract_path(data)
                except Exception:
                    full_path = None
            if isinstance(full_path, str) and full_path:
                parsed = urlparse(full_path)
                uri_path = parsed.path if parsed.scheme == 'file' else full_path
                path_str = os.path.normpath(uri_path)
                base = os.path.basename(path_str.rstrip(os.sep)) or project_dir
                return base
            # Fallback: infer from state.vscdb entries
            state_db = os.path.join(workspace_path, 'state.vscdb')
            if os.path.exists(state_db):
                try:
                    import sqlite3
                    conn = sqlite3.connect(state_db)
                    cur = conn.cursor()
                    # keys likely containing recent file URIs
                    candidate_keys = ['history.entries','workbench.history.entries','recentlyOpeneds','fileHistory']
                    for k in candidate_keys:
                        try:
                            cur.execute('SELECT value FROM ItemTable WHERE key=?', (k,))
                            row = cur.fetchone()
                            if not row:
                                continue
                            data = row[0]
                            try:
                                data = json.loads(data)
                            except Exception:
                                data = None
                            if not data:
                                continue
                            from collections import Counter
                            names = []
                            def collect_name_from_uri(uri: str):
                                try:
                                    p = urlparse(uri)
                                    path = p.path if p.scheme == 'file' else uri
                                    path = os.path.normpath(path)
                                    # try to find git root
                                    probe = path
                                    found = None
                                    for _ in range(6):
                                        if os.path.isdir(probe) and os.path.exists(os.path.join(probe, '.git')):
                                            found = os.path.basename(probe)
                                            break
                                        new_probe = os.path.dirname(probe.rstrip(os.sep))
                                        if new_probe == probe:
                                            break
                                        probe = new_probe
                                    if not found:
                                        found = os.path.basename(os.path.dirname(path.rstrip(os.sep)))
                                    if found:
                                        names.append(found)
                                except Exception:
                                    pass
                            if isinstance(data, list):
                                for it in data:
                                    if isinstance(it, dict):
                                        res = it.get('editor', {}).get('resource') or it.get('resource') or it.get('path')
                                        if isinstance(res, str):
                                            collect_name_from_uri(res)
                                    elif isinstance(it, str):
                                        collect_name_from_uri(it)
                            elif isinstance(data, dict):
                                res = data.get('resource') or data.get('path')
                                if isinstance(res, str):
                                    collect_name_from_uri(res)
                            conn.close()
                            if names:
                                # choose most frequent
                                c = Counter(names)
                                return c.most_common(1)[0][0]
                        except Exception:
                            continue
                    conn.close()
                except Exception:
                    pass
            return project_dir
    
    def _generate_diff_html(self, old_string: str, new_string: str, file_path: str = "") -> str:
        """Generate HTML diff view from old_string and new_string"""
        # Split into lines for difflib
        old_lines = old_string.splitlines(keepends=True)
        new_lines = new_string.splitlines(keepends=True)
        
        # Generate unified diff
        diff = list(difflib.unified_diff(
            old_lines, 
            new_lines, 
            fromfile=f"a/{file_path}", 
            tofile=f"b/{file_path}",
            lineterm=""
        ))
        
        if not diff:
            return f"<div class='diff-no-changes'>No changes detected in {file_path}</div>"
        
        # Parse unified diff and create HTML
        html_lines = []
        html_lines.append(f'<div class="diff-container">')
        html_lines.append(f'<div class="diff-header">📝 <strong>File:</strong> {file_path}</div>')
        html_lines.append('<div class="diff-content">')
        
        line_num_old = 0
        line_num_new = 0
        
        for line in diff:
            if line.startswith('@@'):
                # Hunk header - extract line numbers
                match = re.search(r'-(\d+)(?:,\d+)?\s+\+(\d+)(?:,\d+)?', line)
                if match:
                    line_num_old = int(match.group(1))
                    line_num_new = int(match.group(2))
                html_lines.append(f'<div class="diff-hunk-header">{line.strip()}</div>')
            elif line.startswith('---') or line.startswith('+++'):
                # File headers - skip as we already show filename
                continue
            elif line.startswith('-'):
                # Removed line
                content = line[1:].rstrip('\n\r')
                html_lines.append(f'<div class="diff-line diff-removed">')
                html_lines.append(f'<span class="diff-line-number">{line_num_old}</span>')
                html_lines.append(f'<span class="diff-marker">-</span>')
                html_lines.append(f'<span class="diff-content">{self._escape_html(content)}</span>')
                html_lines.append('</div>')
                line_num_old += 1
            elif line.startswith('+'):
                # Added line
                content = line[1:].rstrip('\n\r')
                html_lines.append(f'<div class="diff-line diff-added">')
                html_lines.append(f'<span class="diff-line-number">{line_num_new}</span>')
                html_lines.append(f'<span class="diff-marker">+</span>')
                html_lines.append(f'<span class="diff-content">{self._escape_html(content)}</span>')
                html_lines.append('</div>')
                line_num_new += 1
            elif line.startswith(' '):
                # Context line
                content = line[1:].rstrip('\n\r')
                html_lines.append(f'<div class="diff-line diff-context">')
                html_lines.append(f'<span class="diff-line-number">{line_num_old}</span>')
                html_lines.append(f'<span class="diff-marker"> </span>')
                html_lines.append(f'<span class="diff-content">{self._escape_html(content)}</span>')
                html_lines.append('</div>')
                line_num_old += 1
                line_num_new += 1
        
        html_lines.append('</div>')  # diff-content
        html_lines.append('</div>')  # diff-container
        
        return '\n'.join(html_lines)
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML characters"""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#x27;'))

    def _format_cursor_display_name(self, project_dir: str) -> str:
        import os
        from urllib.parse import urlparse
        workspace_path = os.path.join(self.projects_path, project_dir)
        workspace_json = os.path.join(workspace_path, 'workspace.json')
        if not os.path.exists(workspace_json):
            return project_dir
        try:
            with open(workspace_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            return project_dir
        full_path = (
            data.get('folder') or
            data.get('path') or
            data.get('workspace') or
            data.get('workspacePath') or
            data.get('name')
        )
        if isinstance(full_path, dict):
            full_path = full_path.get('path') or full_path.get('folder')
        if not isinstance(full_path, str) or not full_path:
            return project_dir
        parsed = urlparse(full_path)
        uri_path = parsed.path if parsed.scheme == 'file' else full_path
        path_str = os.path.normpath(uri_path)
        parts = [p for p in path_str.split(os.sep) if p]
        if len(parts) > 3:
            parts = parts[-3:]
        return '/'.join(parts)

    def _cursor_count_prompts(self, db_path: str) -> int:
        import sqlite3

        # Define helper functions
        def _parse_json_maybe(value):
            if isinstance(value, str):
                v = value.strip()
                if (v.startswith('{') and v.endswith('}')) or (v.startswith('[') and v.endswith(']')):
                    try:
                        return json.loads(v)
                    except Exception:
                        return value
            return value

        def _extract_text_deep(obj):
            candidate_keys = ['content','text','prompt','message','inputText','outputText','body','textContent','query','question','request','description','desc','title']
            best = ''
            def visit(o):
                nonlocal best
                if isinstance(o, dict):
                    for k, v in o.items():
                        if isinstance(v, str) and v.strip():
                            if any(key in k for key in candidate_keys):
                                if len(v) > len(best):
                                    best = v
                        visit(v)
                elif isinstance(o, list):
                    for it in o:
                        visit(it)
            visit(obj)
            return best

        def _normalize_item(item):
            item = _parse_json_maybe(item)
            if isinstance(item, dict):
                payload = _parse_json_maybe(item.get('value')) if item.get('value') is not None else item
                if isinstance(payload, dict):
                    content = (
                        payload.get('content') or payload.get('text') or payload.get('prompt') or
                        payload.get('message') or payload.get('inputText') or payload.get('outputText') or
                        payload.get('body') or payload.get('textContent') or ''
                    )
                    if not content:
                        content = _extract_text_deep(payload) or ''
                    role = payload.get('role')
                    if role is None:
                        if payload.get('from'):
                            role = 'user' if str(payload.get('from')).lower() == 'user' else 'assistant'
                        elif payload.get('isUser') is not None:
                            role = 'user' if payload.get('isUser') else 'assistant'
                        else:
                            role = 'assistant' if payload.get('outputText') else 'user'
                    return {
                        'role': role,
                        'content': content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
                        'timestamp': payload.get('timestamp') or payload.get('time') or item.get('timestamp')
                    }
                else:
                    pv = str(payload)
                    return {'role': 'assistant', 'content': pv, 'timestamp': item.get('timestamp')}
            elif isinstance(item, list):
                out = []
                for it in item:
                    n = _normalize_item(it)
                    if isinstance(n, list):
                        out.extend(n)
                    else:
                        out.append(n)
                return out
            else:
                s = str(item)
                return {'role': 'assistant', 'content': s}

        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            # Determine the key based on parser type
            if self.parser_type == 'cursor':
                key = 'aiService.prompts'
            elif self.parser_type == 'trae':
                # Try the known key first, fall back to auto-detection
                cur.execute("SELECT value FROM ItemTable WHERE key=?", ('icube-ai-agent-storage-input-history',))
                row = cur.fetchone()
                if row:
                    key = 'icube-ai-agent-storage-input-history'
                else:
                    key = self._find_state_key(cur)
            elif self.parser_type == 'kiro':
                key = self._find_state_key(cur)
            else:
                key = self._find_state_key(cur)

            if not key:
                conn.close()
                return 0
            cur.execute("SELECT value FROM ItemTable WHERE key=?", (key,))
            row = cur.fetchone()
            conn.close()
            if not row:
                return 0
            raw = row[0]
            try:
                data = json.loads(raw)
            except Exception:
                return 0
            if isinstance(data, dict):
                items = (
                    data.get('prompts') or
                    data.get('messages') or
                    data.get('items') or
                    data.get('history') or
                    data.get('chatHistory') or
                    data.get('threads') or
                    data.get('sessions') or
                    []
                )
                items = _parse_json_maybe(items)
                if not isinstance(items, list) or not items:
                    def _find_items_deep(o):
                        best = None
                        best_len = 0
                        def visit(x):
                            nonlocal best, best_len
                            if isinstance(x, list) and x and isinstance(x[0], dict):
                                l = len(x)
                                if l > best_len:
                                    best = x
                                    best_len = l
                                for it in x:
                                    visit(it)
                            elif isinstance(x, dict):
                                for v in x.values():
                                    visit(v)
                        visit(o)
                        return best
                    deep_items = _find_items_deep(data)
                    if isinstance(deep_items, list):
                        items = deep_items
            elif isinstance(data, list):
                items = data
            else:
                items = []
            def _nonempty_count(arr):
                c = 0
                for it in arr:
                    n = _normalize_item(it)
                    if isinstance(n, list):
                        for a in n:
                            if isinstance(a, dict) and isinstance(a.get('content'), str) and a.get('content').strip():
                                c += 1
                    else:
                        if isinstance(n, dict) and isinstance(n.get('content'), str) and n.get('content').strip():
                            c += 1
                return c
            return _nonempty_count(items)
        except Exception:
            return 0

    def _cursor_query_prompts(self, db_path: str) -> List[Dict]:
        import sqlite3
        results = []
        def _parse_json_maybe(value):
            if isinstance(value, str):
                v = value.strip()
                if (v.startswith('{') and v.endswith('}')) or (v.startswith('[') and v.endswith(']')):
                    try:
                        return json.loads(v)
                    except Exception:
                        return value
            return value
        def _extract_text_deep(obj):
            # find best non-empty string from common text keys deep in structure
            candidate_keys = ['content','text','prompt','message','inputText','outputText','body','textContent','query','question','request','description','desc','title']
            best = ''
            def visit(o):
                nonlocal best
                if isinstance(o, dict):
                    for k, v in o.items():
                        if isinstance(v, str) and v.strip():
                            if any(key in k for key in candidate_keys):
                                if len(v) > len(best):
                                    best = v
                        visit(v)
                elif isinstance(o, list):
                    for it in o:
                        visit(it)
            visit(obj)
            return best
        def _normalize_item(item):
            # item can be dict or string or nested json string
            item = _parse_json_maybe(item)
            if isinstance(item, dict):
                # some stores put payload in 'value' as JSON string
                payload = _parse_json_maybe(item.get('value')) if item.get('value') is not None else item
                if isinstance(payload, dict):
                    content = (
                        payload.get('content') or payload.get('text') or payload.get('prompt') or
                        payload.get('message') or payload.get('inputText') or payload.get('outputText') or
                        payload.get('body') or payload.get('textContent') or ''
                    )
                    if not content:
                        content = _extract_text_deep(payload) or ''
                    role = payload.get('role')
                    if role is None:
                        if payload.get('from'):
                            role = 'user' if str(payload.get('from')).lower() == 'user' else 'assistant'
                        elif payload.get('isUser') is not None:
                            role = 'user' if payload.get('isUser') else 'assistant'
                        else:
                            role = 'assistant' if payload.get('outputText') else 'user'
                    return {
                        'role': role,
                        'content': content if isinstance(content, str) else json.dumps(content, ensure_ascii=False),
                        'timestamp': payload.get('timestamp') or payload.get('time') or item.get('timestamp')
                    }
                else:
                    # payload remains string
                    pv = str(payload)
                    return {'role': 'assistant', 'content': pv, 'timestamp': item.get('timestamp')}
            elif isinstance(item, list):
                # flatten list of items
                out = []
                for it in item:
                    n = _normalize_item(it)
                    if isinstance(n, list):
                        out.extend(n)
                    else:
                        out.append(n)
                return out
            else:
                # primitive string
                s = str(item)
                return {'role': 'assistant', 'content': s}
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()

            # Determine the key based on parser type
            key = None
            row = None
            if self.parser_type == 'cursor':
                key = 'aiService.prompts'
            elif self.parser_type == 'trae':
                # Try the known key first, fall back to auto-detection
                cur.execute("SELECT value FROM ItemTable WHERE key=?", ('icube-ai-agent-storage-input-history',))
                row = cur.fetchone()
                if row:
                    key = 'icube-ai-agent-storage-input-history'
                else:
                    key = self._find_state_key(cur)
            elif self.parser_type == 'kiro':
                key = self._find_state_key(cur)
            else:
                key = self._find_state_key(cur)

            if not key:
                conn.close()
                return results

            # Only query if we haven't already fetched the row
            if not row:
                cur.execute("SELECT value FROM ItemTable WHERE key=?", (key,))
                row = cur.fetchone()
            conn.close()
            if not row:
                return results
            raw = row[0]
            data = _parse_json_maybe(raw)
            if isinstance(data, dict):
                items = (
                    data.get('prompts') or data.get('messages') or data.get('items') or
                    data.get('history') or data.get('chatHistory') or data.get('threads') or data.get('sessions') or []
                )
                if not isinstance(items, list) or not items:
                    def _find_items_deep(o):
                        best = None
                        best_len = 0
                        def visit(x):
                            nonlocal best, best_len
                            if isinstance(x, list) and x and isinstance(x[0], dict):
                                l = len(x)
                                if l > best_len:
                                    best = x
                                    best_len = l
                                for it in x:
                                    visit(it)
                            elif isinstance(x, dict):
                                for v in x.values():
                                    visit(v)
                        visit(o)
                        return best
                    deep_items = _find_items_deep(data)
                    if isinstance(deep_items, list):
                        items = deep_items
            elif isinstance(data, list):
                items = data
            else:
                items = []
            for item in items:
                norm = _normalize_item(item)
                if isinstance(norm, list):
                    for n in norm:
                        if isinstance(n, dict) and isinstance(n.get('content'), str) and n.get('content').strip():
                            results.append(n)
                else:
                    if isinstance(norm, dict) and isinstance(norm.get('content'), str) and norm.get('content').strip():
                        results.append(norm)
            return results
        except Exception:
            return results

    def _find_state_key(self, cur) -> Optional[str]:
        import json
        patterns = [
            '%prompt%', '%prompts%', '%ai%', '%aiService.%', '%chat%', '%chat.%', '%chatHistory%',
            '%messages%', '%message%', '%history%', '%conversation%', '%threads%', '%sessions%', '%kiro%'
        ]
        seen = []
        for pat in patterns:
            try:
                cur.execute("SELECT key FROM ItemTable WHERE key LIKE ? LIMIT 100", (pat,))
                seen += [row[0] for row in cur.fetchall()]
            except Exception:
                continue
        keys = list(dict.fromkeys(seen))
        blacklist = (
            'memento/', 'workbench.', 'terminal', 'scm.', 'debug.', 'vscode.', 'output.',
            'workbench.panel.', 'workbench.view.', 'workbench.activity', 'workbench.explorer',
            'workbench.editor', 'workbench.sideBar', 'workbench.panelpart', 'workbench.auxiliary',
            'workbench.zenMode', 'workbench.search.'
        )
        keys = [k for k in keys if not any(k.startswith(b) for b in blacklist)]
        best_key = None
        best_score = -1
        for key in keys:
            try:
                cur.execute("SELECT value FROM ItemTable WHERE key= ?", (key,))
                row = cur.fetchone()
                if not row:
                    continue
                val = row[0]
                try:
                    data = json.loads(val)
                except Exception:
                    continue
                score = 0
                if isinstance(data, list):
                    score = len(data)
                    if data and isinstance(data[0], dict) and any(k in data[0] for k in ['text','content','prompt','message','inputText','outputText','body','textContent']):
                        score += 1000
                elif isinstance(data, dict):
                    items = data.get('prompts') or data.get('messages') or data.get('items') or data.get('history') or data.get('chatHistory') or data.get('threads') or data.get('sessions') or []
                    if isinstance(items, list):
                        score = len(items)
                        if items and isinstance(items[0], dict) and any(k in items[0] for k in ['text','content','prompt','message','inputText','outputText','body','textContent']):
                            score += 1000
                    else:
                        def _extract_items_any(o):
                            best = None
                            best_len = 0
                            text_keys = ['text','content','prompt','message','inputText','outputText','body','textContent']
                            def visit(x):
                                nonlocal best, best_len
                                if isinstance(x, list):
                                    if x and isinstance(x[0], dict) and any(k in x[0] for k in text_keys):
                                        l = len(x)
                                        if l > best_len:
                                            best = x
                                            best_len = l
                                    for it in x:
                                        visit(it)
                                elif isinstance(x, dict):
                                    for v in x.values():
                                        visit(v)
                            visit(o)
                            return best, best_len
                        best, best_len = _extract_items_any(data)
                        if best_len:
                            score = best_len + 1000
                if score > best_score:
                    best_score = score
                    best_key = key
            except Exception:
                continue
        if best_key:
            return best_key

        # fallback: check top largest values if pattern search failed
        try:
            cur.execute("SELECT key, value FROM ItemTable ORDER BY LENGTH(value) DESC LIMIT 50")
            rows = cur.fetchall()
            for key, val in rows:
                if any(key.startswith(b) for b in blacklist):
                    continue
                try:
                    data = json.loads(val)
                except Exception:
                    continue
                if isinstance(data, list) and data and isinstance(data[0], dict):
                    if any(k in data[0] for k in ['text','content','prompt','message','role','type','inputText','outputText','body','textContent']):
                        return key
                if isinstance(data, dict):
                    items = data.get('prompts') or data.get('messages') or data.get('items') or data.get('history') or data.get('chatHistory') or data.get('threads') or data.get('sessions') or []
                    if isinstance(items, list) and items and isinstance(items[0], dict):
                        if any(k in items[0] for k in ['text','content','prompt','message','role','type','inputText','outputText','body','textContent']):
                            return key
                    else:
                        def _extract_items_any2(o):
                            text_keys = ['text','content','prompt','message','role','type','inputText','outputText','body','textContent']
                            def visit(x):
                                if isinstance(x, list) and x and isinstance(x[0], dict):
                                    if any(k in x[0] for k in text_keys):
                                        return True
                                    for it in x:
                                        if visit(it):
                                            return True
                                elif isinstance(x, dict):
                                    for v in x.values():
                                        if visit(v):
                                            return True
                                return False
                            return visit(o)
                        if _extract_items_any2(data):
                            return key
        except Exception:
            pass
        return best_key

    def _discover_state_key(self, db_path: str) -> Optional[str]:
        import sqlite3
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            key = 'aiService.prompts' if self.parser_type == 'cursor' else self._find_state_key(cur)
            conn.close()
            return key
        except Exception:
            return None

    def get_session_summary(self, project_name: str, session_id: str) -> Optional[str]:
        """
        Extract full session summary if available
        
        Returns:
            Full summary text or None if no summary exists
        """
        try:
            if self.parser_type == "claude":
                session_path = os.path.join(self.projects_path, project_name, f"{session_id}.jsonl")
            elif self.parser_type == "qwen":
                project_path = os.path.join(self.projects_path, project_name)
                session_path = os.path.join(project_path, 'chats', f"{session_id}.json")
            elif self.parser_type == "kiro":
                project_path = os.path.join(self.projects_path, project_name)
                workspace_json = os.path.join(project_path, 'workspace.json')
                if os.path.exists(workspace_json):
                    with open(workspace_json, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        folder_uri = data.get('folder', '')
                        folder_path = folder_uri.replace('file://', '')
                        sessions_dir_name = self._path_to_base64(folder_path)
                        sessions_path = os.path.join(self.kiro_sessions_path, sessions_dir_name)
                        session_path = os.path.join(sessions_path, f"{session_id}.json")
                else:
                    return None
            elif self.parser_type in ["cursor", "trae"]:
                project_path = os.path.join(self.projects_path, project_name)
                session_path = os.path.join(project_path, 'state.vscdb')
            else:
                return None

            if not os.path.exists(session_path):
                return None

            if self.parser_type == "claude":
                with open(session_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            if data.get("type") == "summary":
                                return data.get("summary", "").strip()
                        except json.JSONDecodeError:
                            continue
                return None

            elif self.parser_type == "qwen":
                with open(session_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    messages = session_data.get('messages', [])
                    for msg in messages:
                        if msg.get('type') == 'summary':
                            return msg.get('content', '').strip()
                return None

            elif self.parser_type == "kiro":
                with open(session_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    history = session_data.get('history', [])
                    for msg in history:
                        message = msg.get('message', {})
                        if message.get('type') == 'summary':
                            return message.get('content', '').strip()
                return None

            elif self.parser_type in ["cursor", "trae"]:
                prompts = self._cursor_query_prompts(session_path)
                for prompt in prompts:
                    if prompt.get('type') == 'summary':
                        return prompt.get('content', '').strip()
                return None

        except Exception:
            return None

    def _extract_session_title(self, file_path: str, max_length: int = 100) -> str:
        """
        Extract session title with priority:
        1. Summary content (if available)
        2. First user message
        3. "Untitled Session" as fallback
        """
        try:
            if self.parser_type == "claude":
                # Read Claude JSONL file
                summary_content = None
                first_user_message = None
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            
                            # Priority 1: Look for summary
                            if data.get("type") == "summary":
                                summary = data.get("summary", "").strip()
                                if summary:
                                    summary_content = summary[:max_length]
                                    break  # Found summary, use it immediately
                            
                            # Priority 2: Look for first user message
                            if first_user_message is None:
                                if data.get("type") == "user":
                                    message_data = data.get("message", {})
                                    content = message_data.get("content", "")
                                    if isinstance(content, str) and content.strip():
                                        first_user_message = content.strip()[:max_length]
                                    elif isinstance(content, list):
                                        # Extract text from structured content
                                        for item in content:
                                            if isinstance(item, dict) and item.get("type") == "text":
                                                text = item.get("text", "").strip()
                                                if text:
                                                    first_user_message = text[:max_length]
                                                    break
                                elif data.get("role") == "user":
                                    # Legacy format
                                    content = data.get("content", "")
                                    if isinstance(content, str) and content.strip():
                                        first_user_message = content.strip()[:max_length]
                        except json.JSONDecodeError:
                            continue
                
                # Return summary if found, otherwise first user message
                return summary_content or first_user_message or "Untitled Session"

            elif self.parser_type == "qwen":
                # Read Qwen JSON file
                with open(file_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    messages = session_data.get('messages', [])
                    
                    # Look for summary in messages
                    summary_content = None
                    first_user_message = None
                    
                    for msg in messages:
                        # Check for summary type
                        if msg.get('type') == 'summary':
                            content = msg.get('content', '').strip()
                            if content:
                                summary_content = content[:max_length]
                                break
                        
                        # Get first user message
                        if first_user_message is None and msg.get('type') == 'user':
                            content = msg.get('content', '').strip()
                            if content:
                                first_user_message = content[:max_length]
                    
                    return summary_content or first_user_message or "Untitled Session"

            elif self.parser_type in ["cursor", "trae", "kiro"]:
                # Read from database
                prompts = self._cursor_query_prompts(file_path)
                
                summary_content = None
                first_user_message = None
                
                for prompt in prompts:
                    # Check for summary
                    if prompt.get('type') == 'summary':
                        content = prompt.get('content', '').strip()
                        if content:
                            summary_content = content[:max_length]
                            break
                    
                    # Get first user message
                    if first_user_message is None and prompt.get('role') == 'user':
                        content = prompt.get('content', '').strip()
                        if content:
                            first_user_message = content[:max_length]
                
                return summary_content or first_user_message or "Untitled Session"

        except Exception:
            return "Untitled Session"

    def _path_to_base64(self, path: str) -> str:
        """Convert a file path to Kiro's base64 directory name format"""
        import base64
        # Remove file:// prefix if present
        clean_path = path.replace('file://', '')
        # Encode to base64
        encoded_bytes = clean_path.encode('utf-8')
        encoded = base64.b64encode(encoded_bytes).decode('utf-8')
        # Remove = padding
        encoded = encoded.rstrip('=')
        # Add trailing underscores based on original padding
        padding_count = (3 - (len(encoded_bytes) % 3)) % 3
        if padding_count == 1:
            encoded += '__'
        elif padding_count == 2:
            encoded += '_'
        return encoded

    def _format_kiro_display_name(self, hash_dir: str) -> str:
        """Get display name from workspace.json in workspaceStorage"""
        workspace_json = os.path.join(self.projects_path, hash_dir, 'workspace.json')
        if not os.path.exists(workspace_json):
            return hash_dir

        try:
            with open(workspace_json, 'r') as f:
                data = json.load(f)
                folder_uri = data.get('folder', '')
                # Extract path from file:// URI
                folder_path = folder_uri.replace('file://', '')
                # Get last 3 path components
                parts = [p for p in folder_path.split('/') if p]
                if len(parts) > 3:
                    parts = parts[-3:]
                return '/'.join(parts)
        except Exception:
            return hash_dir

    def _parse_kiro_message(self, data: Dict, line_num: int) -> Dict:
        """Parse Kiro message format"""
        base_message = {
            "line_number": line_num,
            "timestamp": None,
        }

        # Extract message data
        message = data.get('message', {})
        role = message.get('role', 'assistant')
        content_items = message.get('content', [])

        # Combine all text content
        content_parts = []
        for item in content_items:
            if isinstance(item, dict):
                if item.get('type') == 'text':
                    content_parts.append(item.get('text', ''))
                elif item.get('type') == 'image':
                    content_parts.append('📷 **[Image attached]**')
            elif isinstance(item, str):
                content_parts.append(item)

        content = '\n\n'.join(content_parts)

        return {
            **base_message,
            "type": "message",
            "role": role,
            "content": content,
            "display_type": "User" if role == "user" else "Assistant",
            "has_code": self._contains_code(content)
        }
