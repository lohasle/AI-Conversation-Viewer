import json
import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import re
from datetime import datetime
import difflib

class QwenParser:
    def __init__(self, qwen_projects_path: str = None):
        self.qwen_projects_path = qwen_projects_path or os.path.expanduser("~/.qwen/tmp")

    def get_projects(self) -> List[Dict]:
        """Scan and return all Qwen projects from ~/.qwen/tmp"""
        projects = []
        if not os.path.exists(self.qwen_projects_path):
            return projects

        for project_hash in os.listdir(self.qwen_projects_path):
            project_path = os.path.join(self.qwen_projects_path, project_hash)
            if os.path.isdir(project_path):
                # Look for chat sessions in this project
                chats_path = os.path.join(project_path, 'chats')
                if os.path.exists(chats_path):
                    session_files = [f for f in os.listdir(chats_path) if f.endswith('.json')]
                    
                    # Get project name from QWEN.md if it exists
                    qwen_md_path = os.path.join(project_path, 'QWEN.md')
                    project_name = project_hash
                    if os.path.exists(qwen_md_path):
                        with open(qwen_md_path, 'r', encoding='utf-8') as f:
                            first_line = f.readline().strip()
                            if first_line.startswith('# '):
                                project_name = first_line[2:]  # Remove '# ' prefix
                            else:
                                project_name = first_line if first_line else project_hash

                    projects.append({
                        "name": project_hash,
                        "display_name": project_name,
                        "path": project_path,
                        "session_count": len(session_files),
                        "sessions": session_files
                    })

        return sorted(projects, key=lambda x: x["display_name"])

    def get_sessions(self, project_name: str) -> List[Dict]:
        """Get all session files for a Qwen project with metadata"""
        project_path = os.path.join(self.qwen_projects_path, project_name)
        chats_path = os.path.join(project_path, 'chats')
        sessions = []

        if not os.path.exists(chats_path):
            return sessions

        for filename in os.listdir(chats_path):
            if filename.endswith('.json'):
                file_path = os.path.join(chats_path, filename)
                file_stats = os.stat(file_path)

                # Count messages in file
                message_count = self._count_messages(file_path)

                sessions.append({
                    "id": filename.replace('.json', ''),  # Extract session ID from filename
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

        session_path = os.path.join(self.qwen_projects_path, project_name, 'chats', f"{session_id}.json")

        if not os.path.exists(session_path):
            return {"messages": [], "total": 0, "page": page, "per_page": per_page}

        # Load the JSON session file
        with open(session_path, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        messages = []
        for idx, msg_data in enumerate(session_data.get('messages', []), 1):
            # Parse message
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
        """Parse Qwen message format to match the expected UI structure"""
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
        """Count total messages in JSON file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
                return len(session_data.get('messages', []))
        except:
            return 0

    def _format_project_name(self, project_hash: str) -> str:
        """Convert project hash to readable format"""
        # Look up the actual project name from QWEN.md
        project_path = os.path.join(self.qwen_projects_path, project_hash)
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
        
        # If no QWEN.md or error reading it, return a shortened version of the hash
        return project_hash[:12]  # Shorten the hash for readability