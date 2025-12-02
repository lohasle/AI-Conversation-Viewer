"""
SQLite database management for favorites and annotations
"""

import sqlite3
import hashlib
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import json


class FavoritesDB:
    """Manage favorites and annotations in SQLite database"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database connection

        Args:
            db_path: Path to database file. Defaults to ~/.aicode-viewer/favorites.db
        """
        if db_path is None:
            db_dir = Path.home() / ".aicode-viewer"
            db_dir.mkdir(exist_ok=True)
            db_path = db_dir / "favorites.db"

        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        self.initialize_db()

    def initialize_db(self):
        """Create database tables if they don't exist"""
        cursor = self.conn.cursor()

        # Favorites table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS favorites (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL CHECK(type IN ('session', 'message')),
                view TEXT NOT NULL,
                project_name TEXT NOT NULL,
                session_id TEXT NOT NULL,
                message_line INTEGER,
                message_hash TEXT,
                title TEXT NOT NULL,
                annotation TEXT,
                content_preview TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Tags table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                color TEXT,
                is_auto BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Favorite-Tag relationship table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS favorite_tags (
                favorite_id TEXT NOT NULL,
                tag_id INTEGER NOT NULL,
                FOREIGN KEY (favorite_id) REFERENCES favorites(id) ON DELETE CASCADE,
                FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE,
                PRIMARY KEY (favorite_id, tag_id)
            )
        """
        )

        # Create indexes for better query performance
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_favorites_view ON favorites(view)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_favorites_project ON favorites(project_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_favorites_created ON favorites(created_at DESC)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_favorites_type ON favorites(type)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_favorites_session ON favorites(session_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_favorites_composite ON favorites(view, project_name, session_id)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_favorite_tags_favorite ON favorite_tags(favorite_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_favorite_tags_tag ON favorite_tags(tag_id)"
        )

        # Enable WAL mode for better concurrent access
        cursor.execute("PRAGMA journal_mode=WAL")

        # Optimize SQLite settings
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        cursor.execute("PRAGMA temp_store=MEMORY")

        self.conn.commit()

    @staticmethod
    def generate_message_hash(content: str) -> str:
        """Generate a stable hash for message content"""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    def add_favorite(
        self,
        favorite_type: str,
        view: str,
        project_name: str,
        session_id: str,
        title: str,
        annotation: Optional[str] = None,
        content_preview: Optional[str] = None,
        message_line: Optional[int] = None,
        message_hash: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Add a new favorite

        Args:
            favorite_type: 'session' or 'message'
            view: IDE type (claude/qwen/cursor/trae/kiro)
            project_name: Project name
            session_id: Session identifier
            title: Favorite title
            annotation: User annotation (Markdown)
            content_preview: Message content preview
            message_line: Message line number (for message-level favorites)
            message_hash: Message content hash (for stability)
            tags: List of tag names

        Returns:
            Favorite ID (UUID)
        """
        favorite_id = str(uuid.uuid4())
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT INTO favorites (
                id, type, view, project_name, session_id,
                message_line, message_hash, title, annotation, content_preview
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                favorite_id,
                favorite_type,
                view,
                project_name,
                session_id,
                message_line,
                message_hash,
                title,
                annotation,
                content_preview,
            ),
        )

        # Add tags
        if tags:
            for tag_name in tags:
                tag_id = self._get_or_create_tag(tag_name)
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO favorite_tags (favorite_id, tag_id)
                    VALUES (?, ?)
                """,
                    (favorite_id, tag_id),
                )

        self.conn.commit()
        return favorite_id

    def remove_favorite(self, favorite_id: str) -> bool:
        """
        Remove a favorite by ID

        Args:
            favorite_id: Favorite UUID

        Returns:
            True if deleted, False if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM favorites WHERE id = ?", (favorite_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_annotation(self, favorite_id: str, annotation: str) -> bool:
        """
        Update favorite annotation

        Args:
            favorite_id: Favorite UUID
            annotation: New annotation text (Markdown)

        Returns:
            True if updated, False if not found
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE favorites
            SET annotation = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (annotation, favorite_id),
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def update_favorite_tags(self, favorite_id: str, tags: List[str]):
        """
        Replace all tags for a favorite

        Args:
            favorite_id: Favorite UUID
            tags: New list of tag names
        """
        cursor = self.conn.cursor()

        # Remove existing tags
        cursor.execute(
            "DELETE FROM favorite_tags WHERE favorite_id = ?", (favorite_id,)
        )

        # Add new tags
        for tag_name in tags:
            tag_id = self._get_or_create_tag(tag_name)
            cursor.execute(
                """
                INSERT INTO favorite_tags (favorite_id, tag_id)
                VALUES (?, ?)
            """,
                (favorite_id, tag_id),
            )

        cursor.execute(
            """
            UPDATE favorites SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (favorite_id,),
        )

        self.conn.commit()

    def get_favorites(
        self,
        favorite_type: Optional[str] = None,
        view: Optional[str] = None,
        project_name: Optional[str] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get favorites with filters

        Args:
            favorite_type: Filter by type ('session' or 'message')
            view: Filter by IDE
            project_name: Filter by project
            tag: Filter by tag name
            search: Search in title, annotation, and content
            limit: Maximum results
            offset: Skip first N results

        Returns:
            List of favorite dictionaries
        """
        query = """
            SELECT DISTINCT f.* FROM favorites f
            LEFT JOIN favorite_tags ft ON f.id = ft.favorite_id
            LEFT JOIN tags t ON ft.tag_id = t.id
            WHERE 1=1
        """
        params = []

        if favorite_type:
            query += " AND f.type = ?"
            params.append(favorite_type)

        if view:
            query += " AND f.view = ?"
            params.append(view)

        if project_name:
            query += " AND f.project_name = ?"
            params.append(project_name)

        if tag:
            query += " AND t.name = ?"
            params.append(tag)

        if search:
            query += " AND (f.title LIKE ? OR f.annotation LIKE ? OR f.content_preview LIKE ?)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern, search_pattern])

        query += " ORDER BY f.created_at DESC"

        if limit:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

        cursor = self.conn.cursor()
        cursor.execute(query, params)

        favorites = []
        for row in cursor.fetchall():
            favorite = dict(row)
            favorite["tags"] = self._get_favorite_tags(favorite["id"])
            favorites.append(favorite)

        return favorites

    def get_favorite_by_id(self, favorite_id: str) -> Optional[Dict[str, Any]]:
        """Get a single favorite by ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM favorites WHERE id = ?", (favorite_id,))
        row = cursor.fetchone()

        if row:
            favorite = dict(row)
            favorite["tags"] = self._get_favorite_tags(favorite_id)
            return favorite
        return None

    def check_favorite_exists(
        self,
        view: str,
        project_name: str,
        session_id: str,
        message_line: Optional[int] = None,
    ) -> Optional[str]:
        """
        Check if a favorite already exists

        Returns:
            Favorite ID if exists, None otherwise
        """
        cursor = self.conn.cursor()

        if message_line is not None:
            cursor.execute(
                """
                SELECT id FROM favorites
                WHERE view = ? AND project_name = ? AND session_id = ? AND message_line = ?
            """,
                (view, project_name, session_id, message_line),
            )
        else:
            cursor.execute(
                """
                SELECT id FROM favorites
                WHERE view = ? AND project_name = ? AND session_id = ? AND type = 'session'
            """,
                (view, project_name, session_id),
            )

        row = cursor.fetchone()
        return row["id"] if row else None

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """Get all tags with usage count"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT t.*, COUNT(ft.favorite_id) as usage_count
            FROM tags t
            LEFT JOIN favorite_tags ft ON t.id = ft.tag_id
            GROUP BY t.id
            ORDER BY usage_count DESC, t.name ASC
        """
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """Get favorites statistics"""
        cursor = self.conn.cursor()

        # Total count
        cursor.execute("SELECT COUNT(*) as total FROM favorites")
        total = cursor.fetchone()["total"]

        # By type
        cursor.execute(
            """
            SELECT type, COUNT(*) as count FROM favorites GROUP BY type
        """
        )
        by_type = {row["type"]: row["count"] for row in cursor.fetchall()}

        # By IDE
        cursor.execute(
            """
            SELECT view, COUNT(*) as count FROM favorites GROUP BY view
        """
        )
        by_view = {row["view"]: row["count"] for row in cursor.fetchall()}

        # Top tags
        cursor.execute(
            """
            SELECT t.name, COUNT(ft.favorite_id) as count
            FROM tags t
            JOIN favorite_tags ft ON t.id = ft.tag_id
            GROUP BY t.id
            ORDER BY count DESC
            LIMIT 10
        """
        )
        top_tags = [
            {"name": row["name"], "count": row["count"]} for row in cursor.fetchall()
        ]

        return {
            "total": total,
            "by_type": by_type,
            "by_view": by_view,
            "top_tags": top_tags,
        }

    def _get_or_create_tag(self, tag_name: str, color: Optional[str] = None) -> int:
        """Get tag ID or create if doesn't exist"""
        cursor = self.conn.cursor()

        cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
        row = cursor.fetchone()

        if row:
            return row["id"]

        # Auto-assign color if not provided
        if color is None:
            colors = [
                "#3b82f6",
                "#8b5cf6",
                "#ec4899",
                "#f59e0b",
                "#10b981",
                "#14b8a6",
                "#f97316",
                "#6366f1",
            ]
            cursor.execute("SELECT COUNT(*) as count FROM tags")
            count = cursor.fetchone()["count"]
            color = colors[count % len(colors)]

        cursor.execute(
            """
            INSERT INTO tags (name, color) VALUES (?, ?)
        """,
            (tag_name, color),
        )
        self.conn.commit()

        return cursor.lastrowid

    def _get_favorite_tags(self, favorite_id: str) -> List[Dict[str, Any]]:
        """Get all tags for a favorite"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT t.* FROM tags t
            JOIN favorite_tags ft ON t.id = ft.tag_id
            WHERE ft.favorite_id = ?
            ORDER BY t.name
        """,
            (favorite_id,),
        )
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        """Close database connection"""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
