// Claude Code Viewer JavaScript - Extended for X-IDE

class ClaudeViewer {
    constructor() {
        this.pendingFavorite = null; // Store pending favorite data for modal
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupCodeCopyButtons();
        this.setupSearch();
        this.setupFavorites();
        this.setupAddFavoriteModal();
        
        // X-IDE Specific
        this.setupGlobalSearchIDE();
        this.setupFavoritesModalIDE();
    }

    setupEventListeners() {
        // Theme toggle
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
        
        const themeToggleApp = document.getElementById('theme-toggle-app');
        if (themeToggleApp) {
            themeToggleApp.addEventListener('click', () => this.toggleTheme());
        }

        // Search form
        const searchForm = document.getElementById('search-form');
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => this.handleSearch(e));
        }

        // Clear filters
        const clearBtn = document.getElementById('clear-filters');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearFilters());
        }

        // Auto-submit on filter change
        const filters = document.querySelectorAll('.auto-filter');
        filters.forEach(filter => {
            filter.addEventListener('change', () => this.autoSubmitFilters());
        });
    }

    setupCodeCopyButtons() {
        // Add copy buttons to all code blocks and pre elements
        const codeElements = document.querySelectorAll('.code-block, .message-content pre');
        
        codeElements.forEach(block => {
            // Skip if copy button already exists
            if (block.querySelector('.copy-btn')) return;
            
            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-btn';
            copyBtn.textContent = 'Copy';
            copyBtn.onclick = () => this.copyCode(block);
            
            // Make block relative positioned
            block.style.position = 'relative';
            block.appendChild(copyBtn);
        });
    }

    setupSearch() {
        // Setup search input with debounce
        const searchInput = document.getElementById('search');
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    if (e.target.value.length > 2 || e.target.value.length === 0) {
                        this.autoSubmitFilters();
                    }
                }, 500);
            });
        }
    }

    setupFavorites() {
        // Load favorites count badge
        this.updateFavoritesCount();

        // Setup session favorite button
        const sessionBtn = document.getElementById('session-favorite-toggle');
        if (sessionBtn) {
            this.checkSessionFavoriteStatus(sessionBtn);
            sessionBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleSessionFavorite(sessionBtn);
            });
        }

        // Setup message favorite toggle buttons
        const favoriteButtons = document.querySelectorAll('.favorite-toggle');
        favoriteButtons.forEach(btn => {
            // Check if this message is already favorited
            this.checkFavoriteStatus(btn);

            // Add click event listener
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.toggleFavorite(btn);
            });
        });
    }
    
    // --- X-IDE Global Search ---
    setupGlobalSearchIDE() {
        const form = document.getElementById('global-search-form-ide');
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const input = document.getElementById('search-input-ide');
            const query = input.value.trim();
            if (!query) return;
            
            await this.performGlobalSearchIDE(query);
        });
    }
    
    async performGlobalSearchIDE(query) {
        const resultsContainer = document.getElementById('search-results-container-ide');
        const resultsDiv = document.getElementById('search-results-ide');
        const resultsCount = document.getElementById('search-results-count-ide');
        const initialState = document.getElementById('search-initial-state-ide');
        
        if (!resultsDiv) return;

        // Show loading
        initialState.classList.add('hidden');
        resultsContainer.classList.remove('hidden');
        resultsDiv.innerHTML = `
            <div class="flex items-center justify-center py-8">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
        `;
        
        try {
            const response = await fetch(`/api/search/global?q=${encodeURIComponent(query)}&limit=20`);
            const data = await response.json();
            
            resultsCount.textContent = `(${data.total} results)`;
            
            if (data.results.length === 0) {
                resultsDiv.innerHTML = `
                    <div class="text-center py-8 text-gray-500">
                        No results found for "${query}"
                    </div>
                `;
                return;
            }
            
            let html = '';
            for (const result of data.results) {
                html += `
                    <div class="bg-gray-50 dark:bg-gray-900/50 rounded-lg p-4 hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors cursor-pointer"
                         onclick="window.location.href='/x-ide?view=${result.view}&project_name=${encodeURIComponent(result.project_name)}&session_id=${encodeURIComponent(result.session_id)}&search=${encodeURIComponent(query)}'">
                        <div class="flex justify-between items-start mb-1">
                            <h4 class="font-medium text-gray-900 dark:text-white line-clamp-1">${result.session_title}</h4>
                            <span class="text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 px-1.5 py-0.5 rounded uppercase font-bold">${result.view}</span>
                        </div>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">${result.project_display_name}</p>
                        <div class="text-sm text-gray-600 dark:text-gray-300 line-clamp-2">
                            ${result.first_messages && result.first_messages.length > 0 ? result.first_messages[0].content.substring(0, 150) : 'No preview available'}
                        </div>
                    </div>
                `;
            }
            resultsDiv.innerHTML = html;
            
        } catch (error) {
            console.error('Search failed:', error);
            resultsDiv.innerHTML = '<div class="text-center text-red-500">Search failed</div>';
        }
    }
    
    // --- X-IDE Favorites Modal ---
    setupFavoritesModalIDE() {
        window.openFavoritesModal = () => {
             const modal = document.getElementById('favorites-list-modal');
             if (modal) {
                 modal.classList.remove('hidden');
                 this.loadFavoritesListIDE();
             }
        };
    }
    
    async loadFavoritesListIDE() {
        const container = document.getElementById('favorites-list-container');
        if (!container) return;
        
        container.innerHTML = `
            <div class="flex items-center justify-center h-full">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
        `;
        
        try {
            const response = await fetch('/api/favorites?limit=50');
            const data = await response.json();
            
            if (data.favorites.length === 0) {
                container.innerHTML = `
                    <div class="flex flex-col items-center justify-center h-full text-gray-500">
                        <i class="bi bi-star text-4xl mb-2 opacity-20"></i>
                        <p>No favorites yet</p>
                    </div>
                `;
                return;
            }
            
            let html = '<div class="space-y-3">';
            for (const fav of data.favorites) {
                const link = fav.type === 'session' 
                    ? `/x-ide?view=${fav.view}&project_name=${encodeURIComponent(fav.project_name)}&session_id=${encodeURIComponent(fav.session_id)}`
                    : `/x-ide?view=${fav.view}&project_name=${encodeURIComponent(fav.project_name)}&session_id=${encodeURIComponent(fav.session_id)}&highlight=${fav.message_line}`;
                
                html += `
                    <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow relative group">
                         <div class="flex justify-between items-start">
                             <div>
                                 <h4 class="font-medium text-gray-900 dark:text-white mb-1">
                                     <a href="${link}" class="hover:underline">${fav.title}</a>
                                 </h4>
                                 <p class="text-xs text-gray-500 dark:text-gray-400 mb-2">
                                     ${fav.type === 'session' ? '<i class="bi bi-journal-bookmark mr-1"></i>Session' : '<i class="bi bi-chat-square-text mr-1"></i>Message'} 
                                     • ${fav.view} • ${fav.project_name}
                                 </p>
                                 ${fav.annotation ? `<div class="text-sm text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-900/50 p-2 rounded italic">"${fav.annotation}"</div>` : ''}
                                 ${fav.content_preview ? `<div class="mt-2 text-xs text-gray-500 dark:text-gray-400 line-clamp-2 border-l-2 border-gray-300 dark:border-gray-600 pl-2">${fav.content_preview}</div>` : ''}
                             </div>
                             <button onclick="window.claudeViewer.removeFavoriteById('${fav.id}', this)" class="text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity" title="Remove">
                                 <i class="bi bi-trash"></i>
                             </button>
                         </div>
                    </div>
                `;
            }
            html += '</div>';
            container.innerHTML = html;
            
        } catch (error) {
             console.error('Failed to load favorites:', error);
             container.innerHTML = '<div class="text-center text-red-500">Failed to load favorites</div>';
        }
    }
    
    async removeFavoriteById(id, btn) {
        if(!confirm('Are you sure you want to remove this favorite?')) return;
        
        try {
            const response = await fetch(`/api/favorites/${id}`, { method: 'DELETE' });
            if(response.ok) {
                // Reload list
                this.loadFavoritesListIDE();
                this.updateFavoritesCount();
                // Update current page status if needed
                const toggleBtn = document.querySelector(`[data-favorite-id="${id}"]`);
                if(toggleBtn) this.markAsNotFavorited(toggleBtn);
            }
        } catch(e) {
            console.error(e);
        }
    }

    async updateFavoritesCount() {
        try {
            const response = await fetch('/api/favorites/statistics');
            if (response.ok) {
                const stats = await response.json();
                const badge = document.getElementById('favorites-count-badge');
                if (badge && stats.total > 0) {
                    badge.textContent = stats.total;
                    badge.classList.remove('hidden');
                }
            }
        } catch (error) {
            console.error('Failed to load favorites count:', error);
        }
    }

    async checkFavoriteStatus(btn) {
        const view = btn.dataset.view;
        const project = btn.dataset.project;
        const session = btn.dataset.session;
        const line = btn.dataset.line;

        try {
            const response = await fetch(`/api/favorites/check/${view}/${project}/${session}?message_line=${line}`);
            if (response.ok) {
                const data = await response.json();
                if (data.exists) {
                    this.markAsFavorited(btn, data.favorite_id);
                }
            }
        } catch (error) {
            console.error('Failed to check favorite status:', error);
        }
    }

    async toggleFavorite(btn) {
        const isFavorited = btn.classList.contains('favorited');

        if (isFavorited) {
            // Remove favorite
            const favoriteId = btn.dataset.favoriteId;
            await this.removeFavorite(btn, favoriteId);
        } else {
            // Add favorite
            await this.addFavorite(btn);
        }
    }

    async addFavorite(btn) {
        const view = btn.dataset.view;
        const project = btn.dataset.project;
        const session = btn.dataset.session;
        const line = btn.dataset.line;
        const content = btn.dataset.content;

        // Generate default title from content
        const defaultTitle = content.substring(0, 50) + (content.length > 50 ? '...' : '');

        // Prepare payload
        const payload = {
            type: 'message',
            view: view,
            project_name: project,
            session_id: session,
            content_preview: content,
            message_line: parseInt(line),
            message_content: content,
            tags: []
        };

        // Show modal for user to add title and annotation
        this.showAddFavoriteModal({
            button: btn,
            defaultTitle: defaultTitle,
            previewTitle: defaultTitle,
            previewMeta: `Message • ${view} • ${project} • Line ${line}`,
            payload: payload
        });
    }

    async removeFavorite(btn, favoriteId) {
        try {
            const response = await fetch(`/api/favorites/${favoriteId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                this.markAsNotFavorited(btn);
                this.showNotification('Removed from favorites', 'success');
                this.updateFavoritesCount();
            } else {
                this.showNotification('Failed to remove favorite', 'error');
            }
        } catch (error) {
            console.error('Failed to remove favorite:', error);
            this.showNotification('Failed to remove favorite', 'error');
        }
    }

    markAsFavorited(btn, favoriteId) {
        btn.classList.add('favorited');
        btn.dataset.favoriteId = favoriteId;
        btn.classList.remove('text-gray-400', 'dark:text-gray-500');
        btn.classList.add('text-amber-500', 'dark:text-amber-400');
        const icon = btn.querySelector('i');
        icon.classList.remove('bi-star');
        icon.classList.add('bi-star-fill');
        btn.title = 'Remove from favorites';
    }

    markAsNotFavorited(btn) {
        btn.classList.remove('favorited');
        delete btn.dataset.favoriteId;
        btn.classList.remove('text-amber-500', 'dark:text-amber-400');
        btn.classList.add('text-gray-400', 'dark:text-gray-500');
        const icon = btn.querySelector('i');
        icon.classList.remove('bi-star-fill');
        icon.classList.add('bi-star');
        btn.title = 'Add to favorites';
    }

    async checkSessionFavoriteStatus(btn) {
        const view = btn.dataset.view;
        const project = btn.dataset.project;
        const session = btn.dataset.session;

        try {
            const response = await fetch(`/api/favorites/check/${view}/${project}/${session}`);
            if (response.ok) {
                const data = await response.json();
                if (data.exists) {
                    this.markAsFavorited(btn, data.favorite_id);
                }
            }
        } catch (error) {
            console.error('Failed to check session favorite status:', error);
        }
    }

    async toggleSessionFavorite(btn) {
        const isFavorited = btn.classList.contains('favorited');

        if (isFavorited) {
            const favoriteId = btn.dataset.favoriteId;
            await this.removeFavorite(btn, favoriteId);
        } else {
            const view = btn.dataset.view;
            const project = btn.dataset.project;
            const session = btn.dataset.session;
            const defaultTitle = `Session: ${session.substring(0, 12)}...`;

            const payload = {
                type: 'session',
                view: view,
                project_name: project,
                session_id: session,
                tags: []
            };

            // Show modal for user to add title and annotation
            this.showAddFavoriteModal({
                button: btn,
                defaultTitle: defaultTitle,
                previewTitle: defaultTitle,
                previewMeta: `Session • ${view} • ${project}`,
                payload: payload
            });
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 z-50 px-6 py-3 rounded-lg shadow-lg transition-all duration-300 transform translate-x-0 ${
            type === 'success' ? 'bg-green-500 text-white' :
            type === 'error' ? 'bg-red-500 text-white' :
            'bg-blue-500 text-white'
        }`;
        notification.textContent = message;

        document.body.appendChild(notification);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            notification.style.transform = 'translateX(400px)';
            notification.style.opacity = '0';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }

    toggleTheme() {
        const html = document.documentElement;
        const isDark = html.classList.contains('dark');

        if (isDark) {
            html.classList.remove('dark');
            localStorage.setItem('theme', 'light');
        } else {
            html.classList.add('dark');
            localStorage.setItem('theme', 'dark');
        }

        // Smooth transition
        html.style.transition = 'background-color 0.3s ease, color 0.3s ease';
        setTimeout(() => {
            html.style.transition = '';
        }, 300);
    }

    copyCode(codeBlock) {
        // Get the code content - handle both .code-block and direct pre elements
        let code;
        if (codeBlock.tagName === 'PRE') {
            code = codeBlock.textContent;
        } else {
            const preElement = codeBlock.querySelector('pre');
            code = preElement ? preElement.textContent : codeBlock.textContent;
        }
        
        if (navigator.clipboard) {
            navigator.clipboard.writeText(code).then(() => {
                this.showCopyFeedback(codeBlock);
            });
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = code;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            this.showCopyFeedback(codeBlock);
        }
    }

    showCopyFeedback(codeBlock) {
        const copyBtn = codeBlock.querySelector('.copy-btn');
        const originalText = copyBtn.textContent;
        
        copyBtn.textContent = 'Copied!';
        copyBtn.style.background = 'rgba(16, 185, 129, 0.2)';
        
        setTimeout(() => {
            copyBtn.textContent = originalText;
            copyBtn.style.background = '';
        }, 2000);
    }

    handleSearch(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const params = new URLSearchParams();
        
        for (let [key, value] of formData.entries()) {
            if (value.trim()) {
                params.append(key, value.trim());
            }
        }
        
        // Redirect with search parameters
        const url = new URL(window.location);
        url.search = params.toString();
        window.location.href = url.toString();
    }

    autoSubmitFilters() {
        const form = document.getElementById('search-form');
        if (form) {
            form.submit();
        }
    }

    clearFilters() {
        // Clear all form inputs
        const form = document.getElementById('search-form');
        if (form) {
            form.reset();
            
            // Remove URL parameters and redirect
            const url = new URL(window.location);
            url.search = '';
            window.location.href = url.toString();
        }
    }

    // Utility methods
    formatFileSize(bytes) {
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 Bytes';
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    formatDate(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) {
            return 'Today';
        } else if (diffDays === 1) {
            return 'Yesterday';
        } else if (diffDays < 7) {
            return `${diffDays} days ago`;
        } else {
            return date.toLocaleDateString();
        }
    }

    // Search highlighting
    highlightSearchTerms(text, searchTerm) {
        if (!searchTerm) return text;
        
        const regex = new RegExp(`(${searchTerm})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    // Smooth scroll to element
    scrollToElement(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.scrollIntoView({ behavior: 'smooth' });
        }
    }

    // Show loading state
    showLoading(element) {
        if (element) {
            element.innerHTML = `
                <div class="loading">
                    <div class="spinner"></div>
                    Loading...
                </div>
            `;
        }
    }

    // Initialize pagination
    setupPagination() {
        const paginationLinks = document.querySelectorAll('.pagination .page-link');
        paginationLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const url = new URL(link.href);
                this.loadPage(url.searchParams.get('page'));
            });
        });
    }

    loadPage(pageNumber) {
        const url = new URL(window.location);
        url.searchParams.set('page', pageNumber);
        window.location.href = url.toString();
    }

    // Setup add favorite modal event listeners
    setupAddFavoriteModal() {
        const modal = document.getElementById('add-favorite-modal');
        if (!modal) return;

        // Close button
        document.getElementById('close-add-favorite-modal')?.addEventListener('click', () => {
            this.closeAddFavoriteModal();
        });

        // Cancel button
        document.getElementById('cancel-add-favorite')?.addEventListener('click', () => {
            this.closeAddFavoriteModal();
        });

        // Save button
        document.getElementById('save-add-favorite')?.addEventListener('click', () => {
            this.saveFavoriteFromModal();
        });

        // Click outside modal to close
        modal.addEventListener('click', (e) => {
            if (e.target.id === 'add-favorite-modal') {
                this.closeAddFavoriteModal();
            }
        });

        // ESC key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
                this.closeAddFavoriteModal();
            }
        });
    }

    // Show add favorite modal
    showAddFavoriteModal(favoriteData) {
        this.pendingFavorite = favoriteData;

        // Set preview info
        document.getElementById('favorite-preview-title').textContent = favoriteData.previewTitle;
        document.getElementById('favorite-preview-meta').textContent = favoriteData.previewMeta;

        // Set default title
        document.getElementById('favorite-title-input').value = favoriteData.defaultTitle || '';

        // Clear annotation
        document.getElementById('favorite-annotation-input').value = '';

        // Show modal
        document.getElementById('add-favorite-modal').classList.remove('hidden');

        // Focus on annotation
        setTimeout(() => {
            document.getElementById('favorite-annotation-input').focus();
        }, 100);
    }

    // Close add favorite modal
    closeAddFavoriteModal() {
        document.getElementById('add-favorite-modal').classList.add('hidden');
        this.pendingFavorite = null;
        document.getElementById('favorite-title-input').value = '';
        document.getElementById('favorite-annotation-input').value = '';
    }

    // Save favorite from modal
    async saveFavoriteFromModal() {
        if (!this.pendingFavorite) return;

        const customTitle = document.getElementById('favorite-title-input').value.trim();
        const annotation = document.getElementById('favorite-annotation-input').value.trim();

        // Use custom title if provided, otherwise use default
        const title = customTitle || this.pendingFavorite.defaultTitle;

        const payload = {
            ...this.pendingFavorite.payload,
            title: title,
            annotation: annotation || null
        };

        const saveBtn = document.getElementById('save-add-favorite');
        const originalText = saveBtn.innerHTML;

        try {
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<i class="bi bi-hourglass-split mr-2 animate-spin"></i>Saving...';

            const response = await fetch('/api/favorites', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                const data = await response.json();

                // Mark button as favorited if provided
                if (this.pendingFavorite.button) {
                    this.markAsFavorited(this.pendingFavorite.button, data.favorite_id);
                }

                this.showNotification('Added to favorites', 'success');
                this.updateFavoritesCount();
                this.closeAddFavoriteModal();
            } else {
                const error = await response.json();
                this.showNotification('Failed to add favorite: ' + (error.detail || 'Unknown error'), 'error');
            }
        } catch (error) {
            console.error('Failed to add favorite:', error);
            this.showNotification('Failed to add favorite', 'error');
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalText;
        }
    }
}

// Initialize theme before DOM loads to prevent flash
(function() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
        document.documentElement.classList.add('dark');
    }
})();

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize the main app
    window.claudeViewer = new ClaudeViewer();

    // Setup pagination if present
    window.claudeViewer.setupPagination();
    
    // Add X-IDE global search trigger
    window.openGlobalSearch = () => {
        document.getElementById('global-search-modal').classList.remove('hidden');
        document.getElementById('search-input-ide').focus();
    };

    // Add loading state to navigation links
    const navLinks = document.querySelectorAll('a[href^="/"], a[href^="?"]');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            // Only show loader for navigation links, not anchors or target="_blank"
            if (!link.getAttribute('href').startsWith('#') && link.getAttribute('target') !== '_blank') {
                showPageLoader();
            }
        });
    });

    // Hide loader when page is fully loaded or restored
    window.addEventListener('load', hidePageLoader);
    window.addEventListener('pageshow', hidePageLoader);
    window.addEventListener('popstate', hidePageLoader);
});

// Page loader functions
function showPageLoader() {
    const loader = document.getElementById('page-loader');
    if (loader) {
        loader.classList.remove('hidden');
    }
}

function hidePageLoader() {
    const loader = document.getElementById('page-loader');
    if (loader) {
        loader.classList.add('hidden');
    }
}

// Export for use in other scripts
window.showPageLoader = showPageLoader;
window.hidePageLoader = hidePageLoader;

// Utility functions for templates
window.formatFileSize = (bytes) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
};

window.formatRelativeTime = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    
    if (diffDays === 0) {
        return 'Today';
    } else if (diffDays === 1) {
        return 'Yesterday';
    } else if (diffDays < 7) {
        return `${diffDays} days ago`;
    } else {
        return date.toLocaleDateString();
    }
};
