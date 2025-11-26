"""Internationalization support for AI Conversation Viewer."""

TRANSLATIONS = {
    'en': {
        # Navigation
        'app_name': 'AI Conversation Viewer',
        'qwen': 'Qwen',
        'claude': 'Claude',
        'cursor': 'Cursor',
        'trae': 'Trae',
        'kiro': 'Kiro',
        'status': 'Status',
        'projects': 'Projects',
        'search_results': 'Search Results',

        # Home page
        'recent_sessions': 'Recent Sessions',
        'projects_found': 'project(s) found',
        'search_placeholder': 'Search in all conversation content...',
        'search_button': 'Search',
        'search_across': 'Search across all sessions in all',
        'total_projects': 'Total Projects',
        'total_sessions': 'Total Sessions',
        'avg_per_project': 'Avg per Project',
        'view': 'View',
        'active': 'Active',

        # Project view
        'sessions': 'session(s)',
        'messages': 'messages',
        'session': 'Session',
        'session_activity_timeline': 'Session Activity Timeline',
        'showing_recent_sessions': 'Showing 10 most recent sessions of',
        'total': 'total',

        # Conversation view
        'search_messages': 'Search Messages',
        'message_type': 'Message Type',
        'per_page': 'Per Page',
        'all_messages': 'All Messages',
        'user_messages': 'User Messages',
        'assistant_messages': 'Assistant Messages',
        'summaries': 'Summaries',
        'clear_filters': 'Clear Filters',
        'conversation_messages': 'Conversation Messages',
        'results_for': 'Results for:',
        'showing': 'Showing',
        'of': 'of',
        'user': 'User',
        'assistant': 'Assistant',
        'summary': 'Summary',
        'code': 'Code',
        'line': 'Line',
        'page': 'Page',

        # Search
        'search': 'Search',
        'result': 'result(s) for',
        'matches': 'match(es)',
        'view_session': 'View Session',
        'new_search': 'New Search',

        # Empty states
        'no_sessions_found': 'No Sessions Found',
        'no_sessions_desc': 'Make sure',
        'has_been_used': 'has been used and projects exist in:',
        'check_system_status': 'Check System Status',
        'back_to_projects': 'Back to Projects',
        'no_sessions_in_project': "This project doesn't have any conversation sessions yet.",
        'no_messages_found': 'No Messages Found',
        'no_messages_desc': 'Try adjusting your search filters or clear them to see all messages.',
        'conversation_empty': 'This conversation appears to be empty or couldn\'t be loaded.',
        'no_results_found': 'No Results Found',
        'no_results_desc': 'No conversations contain',
        'try_different_term': 'Try a different search term or check your spelling.',

        # Footer
        'built_with': 'Built with FastAPI & Tailwind CSS',

        # Common
        'updated': 'Updated:',
        'modified': 'Modified',
        'browse_search': 'Browse and search your',
        'conversation_history': 'conversation history',
    },
    'zh': {
        # 导航
        'app_name': 'AI 对话查看器',
        'qwen': '通义千问',
        'claude': 'Claude',
        'cursor': 'Cursor',
        'trae': 'Trae',
        'kiro': 'Kiro',
        'status': '状态',
        'projects': '项目列表',
        'search_results': '搜索结果',

        # 首页
        'recent_sessions': '最近会话',
        'projects_found': '个项目',
        'search_placeholder': '搜索所有对话内容...',
        'search_button': '搜索',
        'search_across': '在所有',
        'total_projects': '项目总数',
        'total_sessions': '会话总数',
        'avg_per_project': '平均每项目',
        'view': '查看',
        'active': '当前',

        # 项目详情
        'sessions': '个会话',
        'messages': '条消息',
        'session': '会话',
        'session_activity_timeline': '会话时间线',
        'showing_recent_sessions': '显示最近 10 个会话，共',
        'total': '个',

        # 对话详情
        'search_messages': '搜索消息',
        'message_type': '消息类型',
        'per_page': '每页显示',
        'all_messages': '所有消息',
        'user_messages': '用户消息',
        'assistant_messages': '助手消息',
        'summaries': '摘要',
        'clear_filters': '清除筛选',
        'conversation_messages': '对话消息',
        'results_for': '搜索结果：',
        'showing': '显示',
        'of': '，共',
        'user': '用户',
        'assistant': '助手',
        'summary': '摘要',
        'code': '代码',
        'line': '行',
        'page': '第',

        # 搜索
        'search': '搜索',
        'result': '个结果',
        'matches': '条匹配',
        'view_session': '查看会话',
        'new_search': '新搜索',

        # 空状态
        'no_sessions_found': '未找到会话',
        'no_sessions_desc': '请确保',
        'has_been_used': '已被使用，且项目存在于：',
        'check_system_status': '检查系统状态',
        'back_to_projects': '返回项目列表',
        'no_sessions_in_project': '该项目尚无对话会话。',
        'no_messages_found': '未找到消息',
        'no_messages_desc': '请尝试调整搜索筛选条件或清除它们以查看所有消息。',
        'conversation_empty': '此对话为空或无法加载。',
        'no_results_found': '未找到结果',
        'no_results_desc': '没有对话包含',
        'try_different_term': '请尝试其他搜索词或检查拼写。',

        # 页脚
        'built_with': '基于 FastAPI & Tailwind CSS 构建',

        # 通用
        'updated': '更新于：',
        'modified': '修改于',
        'browse_search': '浏览和搜索你的',
        'conversation_history': '对话历史',
    }
}

def get_translation(key: str, lang: str = 'en') -> str:
    """Get translation for a key in the specified language."""
    if lang not in TRANSLATIONS:
        lang = 'en'
    return TRANSLATIONS[lang].get(key, TRANSLATIONS['en'].get(key, key))

def t(key: str, lang: str = 'en') -> str:
    """Shorthand for get_translation."""
    return get_translation(key, lang)
