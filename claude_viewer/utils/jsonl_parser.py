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
                # Get files based on parser type
                if self.parser_type == "claude":
                    # Get JSONL files in this project
                    session_files = [f for f in os.listdir(project_path) if f.endswith('.jsonl')]
                elif self.parser_type == "qwen":
                    # Get chats directory in this project
                    chats_path = os.path.join(project_path, 'chats')
                    if os.path.exists(chats_path):
                        session_files = [f for f in os.listdir(chats_path) if f.endswith('.json')]
                    else:
                        session_files = []
                else:
                    session_files = []

                # Get the modification time of the project directory
                mtime = os.path.getmtime(project_path)
                mod_time = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

                projects.append({
                    "name": project_dir,
                    "display_name": self._format_project_name(project_dir),  # Use formatted display name
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

                    sessions.append({
                        "id": filename.replace('.jsonl', ''),
                        "filename": filename,
                        "path": file_path,
                        "size": file_stats.st_size,
                        "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                        "message_count": message_count
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

                        sessions.append({
                            "id": filename.replace('.json', ''),
                            "filename": filename,
                            "path": file_path,
                            "size": file_stats.st_size,
                            "modified": datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
                            "message_count": message_count
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
                # For Claude JSONL files, count non-empty lines
                with open(file_path, 'r', encoding='utf-8') as f:
                    return sum(1 for line in f if line.strip())
            elif self.parser_type == "qwen":
                # For Qwen JSON files, load the JSON and count messages
                with open(file_path, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    return len(session_data.get('messages', []))
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