// NAS Media Catalog UI - Main Application
class MediaCatalogApp {
    constructor() {
        this.apiBase = '/api';
        this.mediaFiles = [];
        this.playlists = [];
        this.selectedItems = new Set();
        this.currentView = 'grid';
        this.filters = {
            search: '',
            fileType: '',
            share: ''
        };
        this.mode = 'building';
        this.editingPlaylistId = null;
        this.editSnapshot = null;

        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.showLoading(true);
        
        try {
            await this.checkConnection();
            await this.loadInitialData();
        } catch (error) {
            console.error('Initialization error:', error);
            this.showToast('Failed to connect to server', 'error');
        } finally {
            this.showLoading(false);
        }
    }

    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tab = e.target.dataset.tab;
                this.switchTab(tab);
            });
        });

        // View controls
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const view = e.currentTarget.dataset.view;
                this.setView(view);
            });
        });

        // Filters
        document.getElementById('search-input').addEventListener('input', (e) => {
            this.filters.search = e.target.value;
            this.debounce(this.applyFilters.bind(this), 300)();
        });

        document.getElementById('file-type-filter').addEventListener('change', (e) => {
            this.filters.fileType = e.target.value;
            this.applyFilters();
        });

        document.getElementById('share-filter').addEventListener('change', (e) => {
            this.filters.share = e.target.value;
            this.applyFilters();
        });

        // Buttons
        document.getElementById('reconnect-btn').addEventListener('click', () => this.reconnectUPnP());
        document.getElementById('scan-btn').addEventListener('click', () => this.triggerScan());
        document.getElementById('new-playlist-btn').addEventListener('click', () => this.showPlaylistModal());
        document.getElementById('auto-generate-btn').addEventListener('click', () => this.generateAutoPlaylists());
        document.getElementById('clear-selection-btn').addEventListener('click', () => this.clearSelection());
        document.getElementById('save-playlist-btn').addEventListener('click', () => this.showPlaylistModal(true));

        // Modal controls
        document.getElementById('cancel-playlist-btn').addEventListener('click', () => this.hidePlaylistModal());
        document.getElementById('create-playlist-btn').addEventListener('click', () => this.createPlaylist());
        document.querySelector('.modal-close').addEventListener('click', () => this.hidePlaylistModal());

        // Close modal on backdrop click
        document.getElementById('playlist-modal').addEventListener('click', (e) => {
            if (e.target === e.currentTarget) {
                this.hidePlaylistModal();
            }
        });

        // Edit-mode buttons (in the right-hand panel)
        document.getElementById('edit-save-btn').addEventListener('click', () => this.saveEditedPlaylist());
        document.getElementById('edit-save-as-new-btn').addEventListener('click', () => this.saveAsNew());
        document.getElementById('edit-cancel-btn').addEventListener('click', () => this.cancelEdit());

        // Edit-mode banner buttons (above media grid)
        document.getElementById('banner-save-btn').addEventListener('click', () => this.saveEditedPlaylist());
        document.getElementById('banner-cancel-btn').addEventListener('click', () => this.cancelEdit());

        // Upload .m3u — both buttons share the same hidden input
        const uploadInput = document.getElementById('upload-playlist-input');
        document.getElementById('upload-playlist-btn').addEventListener('click', () => uploadInput.click());
        document.getElementById('upload-playlist-btn-tab').addEventListener('click', () => uploadInput.click());
        uploadInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.uploadM3U(file);
                e.target.value = ''; // reset so the same file can be re-picked
            }
        });
    }

    async checkConnection() {
        try {
            const response = await fetch(`${this.apiBase}/health/detailed`);
            const data = await response.json();
            
            const statusEl = document.getElementById('connection-status');
            if (data.status === 'healthy' && data.upnp_connected) {
                statusEl.className = 'connection-status connected';
                const serverName = data.upnp_server?.name || 'UPnP Server';
                statusEl.innerHTML = `<i class="fas fa-circle"></i> <span>Connected to ${serverName}</span>`;
            } else if (data.status === 'degraded') {
                statusEl.className = 'connection-status degraded';
                statusEl.innerHTML = '<i class="fas fa-circle"></i> <span>API Connected, UPnP Disconnected</span>';
            } else {
                throw new Error('Server not healthy');
            }
        } catch (error) {
            const statusEl = document.getElementById('connection-status');
            statusEl.className = 'connection-status disconnected';
            statusEl.innerHTML = '<i class="fas fa-circle"></i> <span>Disconnected</span>';
            throw error;
        }
    }

    async loadInitialData() {
        await Promise.all([
            this.loadMediaFiles(),
            this.loadPlaylists()
        ]);
        this.populateShareFilter();
    }

    async loadMediaFiles() {
        try {
            const response = await fetch(`${this.apiBase}/media`);
            if (!response.ok) throw new Error('Failed to load media files');
            
            this.mediaFiles = await response.json();
            this.renderMediaFiles();
        } catch (error) {
            console.error('Error loading media files:', error);
            this.showToast('Failed to load media files', 'error');
        }
    }

    async loadPlaylists() {
        try {
            const response = await fetch(`${this.apiBase}/playlists`);
            if (!response.ok) throw new Error('Failed to load playlists');
            
            this.playlists = await response.json();
            this.renderPlaylists();
            this.renderSidebarPlaylists();
        } catch (error) {
            console.error('Error loading playlists:', error);
            this.showToast('Failed to load playlists', 'error');
        }
    }

    populateShareFilter() {
        const shares = [...new Set(this.mediaFiles.map(file => file.share_name))].filter(Boolean);
        const shareFilter = document.getElementById('share-filter');
        
        // Clear existing options (except "All Shares")
        shareFilter.innerHTML = '<option value="">All Shares</option>';
        
        shares.forEach(share => {
            const option = document.createElement('option');
            option.value = share;
            option.textContent = share;
            shareFilter.appendChild(option);
        });
    }

    renderMediaFiles() {
        const container = document.getElementById('media-grid');
        const filteredFiles = this.getFilteredMediaFiles();
        
        if (filteredFiles.length === 0) {
            container.innerHTML = this.getEmptyState('No media files found', 'Try adjusting your filters or scan for media files.');
            return;
        }

        container.innerHTML = filteredFiles.map(file => this.createMediaItemHTML(file)).join('');
        
        // Add click listeners
        container.querySelectorAll('.media-item').forEach(item => {
            item.addEventListener('click', () => {
                const fileId = parseInt(item.dataset.fileId);
                this.toggleSelection(fileId);
            });
        });
    }

    createMediaItemHTML(file) {
        const isVideo = ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'm4v'].includes(file.file_type);
        const isSelected = this.selectedItems.has(file.id);
        const fileSize = this.formatFileSize(file.size);
        const modifiedDate = new Date(file.modified_time * 1000).toLocaleDateString();

        const m3uUrl = `/api/media/${file.id}/download.m3u`;

        return `
            <div class="media-item ${this.currentView === 'list' ? 'list-view' : ''} ${isSelected ? 'selected' : ''}" data-file-id="${file.id}">
                <div class="media-icon ${isVideo ? 'video' : 'audio'}">
                    <i class="fas fa-${isVideo ? 'video' : 'music'}"></i>
                </div>
                <div class="media-info">
                    <h3>${file.name}</h3>
                    <div class="media-meta">
                        <span>${file.file_type.toUpperCase()}</span>
                        <span>${fileSize}</span>
                        <span>${modifiedDate}</span>
                        ${file.share_name ? `<span>${file.share_name}</span>` : ''}
                    </div>
                </div>
                <div class="media-actions">
                    <a class="mrl-link-btn"
                       href="${m3uUrl}"
                       download
                       title="Download .vlc.m3u to open this file in VLC"
                       onclick="event.stopPropagation()">
                        <i class="fas fa-external-link-alt"></i>
                        <span class="mrl-label">VLC</span>
                    </a>
                </div>
                <div class="selection-indicator">
                    <i class="fas fa-check"></i>
                </div>
            </div>
        `;
    }

    renderPlaylists() {
        const container = document.getElementById('playlists-grid');
        
        if (this.playlists.length === 0) {
            container.innerHTML = this.getEmptyState('No playlists found', 'Create your first playlist to get started.');
            return;
        }

        container.innerHTML = this.playlists.map(playlist => this.createPlaylistCardHTML(playlist)).join('');
        
        // Add event listeners
        container.querySelectorAll('.playlist-card').forEach(card => {
            const playlistId = parseInt(card.dataset.playlistId);

            card.querySelector('.view-playlist-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                this.viewPlaylist(playlistId);
            });

            card.querySelector('.edit-playlist-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                this.enterEditMode(playlistId);
            });

            card.querySelector('.download-playlist-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                this.downloadPlaylist(playlistId);
            });

            card.querySelector('.delete-playlist-btn').addEventListener('click', (e) => {
                e.stopPropagation();
                this.deletePlaylist(playlistId);
            });
        });
    }

    createPlaylistCardHTML(playlist) {
        const createdDate = new Date(playlist.created_at).toLocaleDateString();
        const fileCount = playlist.file_paths.length;

        return `
            <div class="playlist-card" data-playlist-id="${playlist.id}">
                <h3>${playlist.name}</h3>
                <p>${playlist.description || 'No description'}</p>
                <div class="playlist-card-meta">
                    ${fileCount} files • Created ${createdDate}
                </div>
                <div class="playlist-card-actions">
                    <button class="icon-btn view-playlist-btn" title="View">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="icon-btn primary edit-playlist-btn" title="Edit">
                        <i class="fas fa-pencil"></i>
                    </button>
                    <button class="icon-btn download-playlist-btn" title="Download .m3u">
                        <i class="fas fa-download"></i>
                    </button>
                    <span class="spacer"></span>
                    <button class="icon-btn danger delete-playlist-btn" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }

    renderSidebarPlaylists() {
        const container = document.getElementById('playlists-list');
        
        if (this.playlists.length === 0) {
            container.innerHTML = '<p style="color: #718096; font-size: 0.9rem; text-align: center; padding: 1rem;">No playlists yet</p>';
            return;
        }

        container.innerHTML = this.playlists.map(playlist => {
            const fileCount = playlist.file_paths.length;
            return `
                <div class="playlist-item" data-playlist-id="${playlist.id}">
                    <h4>${playlist.name}</h4>
                    <p>${fileCount} files</p>
                    <div class="playlist-item-actions">
                        <button class="icon-btn" title="View" onclick="app.viewPlaylist(${playlist.id})">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="icon-btn primary edit-playlist-sidebar-btn" title="Edit" onclick="app.enterEditMode(${playlist.id})">
                            <i class="fas fa-pencil"></i>
                        </button>
                        <button class="icon-btn" title="Download .m3u" onclick="app.downloadPlaylist(${playlist.id})">
                            <i class="fas fa-download"></i>
                        </button>
                        <span class="spacer"></span>
                        <button class="icon-btn danger" title="Delete" onclick="app.deletePlaylist(${playlist.id})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    renderSelectedItems() {
        const container = document.getElementById('selected-items');
        const saveBtn = document.getElementById('save-playlist-btn');
        
        if (this.selectedItems.size === 0) {
            container.innerHTML = '<p style="color: #718096; font-size: 0.9rem; text-align: center; padding: 1rem;">No items selected</p>';
            saveBtn.disabled = true;
            return;
        }

        saveBtn.disabled = false;
        
        const selectedFiles = this.mediaFiles.filter(file => this.selectedItems.has(file.id));
        container.innerHTML = selectedFiles.map(file => {
            const isVideo = ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'm4v'].includes(file.file_type);
            
            return `
                <div class="selected-item">
                    <div class="media-icon ${isVideo ? 'video' : 'audio'}">
                        <i class="fas fa-${isVideo ? 'video' : 'music'}"></i>
                    </div>
                    <div class="selected-item-info">
                        <h4>${file.name}</h4>
                        <p>${file.file_type.toUpperCase()} • ${this.formatFileSize(file.size)}</p>
                    </div>
                    <button class="remove-item-btn" onclick="app.toggleSelection(${file.id})">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        }).join('');
    }

    getFilteredMediaFiles() {
        return this.mediaFiles.filter(file => {
            const matchesSearch = !this.filters.search || 
                file.name.toLowerCase().includes(this.filters.search.toLowerCase());
            const matchesType = !this.filters.fileType || 
                file.file_type === this.filters.fileType;
            const matchesShare = !this.filters.share || 
                file.share_name === this.filters.share;
            
            return matchesSearch && matchesType && matchesShare;
        });
    }

    toggleSelection(fileId) {
        if (this.selectedItems.has(fileId)) {
            this.selectedItems.delete(fileId);
        } else {
            this.selectedItems.add(fileId);
        }
        
        this.renderMediaFiles();
        this.renderSelectedItems();
    }

    clearSelection() {
        this.selectedItems.clear();
        this.renderMediaFiles();
        this.renderSelectedItems();
    }

    switchTab(tab) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });
        
        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === `${tab}-tab`);
        });
    }

    setView(view) {
        this.currentView = view;
        
        // Update view buttons
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.view === view);
        });
        
        // Update grid class
        const grid = document.getElementById('media-grid');
        grid.classList.toggle('list-view', view === 'list');
        
        this.renderMediaFiles();
    }

    applyFilters() {
        this.renderMediaFiles();
    }

    async reconnectUPnP() {
        const btn = document.getElementById('reconnect-btn');
        const originalText = btn.innerHTML;
        
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Reconnecting...';
        btn.disabled = true;
        
        try {
            const response = await fetch(`${this.apiBase}/upnp/reconnect`, { method: 'POST' });
            if (!response.ok) throw new Error('Reconnect failed');
            
            const data = await response.json();
            this.showToast('UPnP server reconnected successfully', 'success');
            
            // Update connection status
            await this.checkConnection();
            
        } catch (error) {
            console.error('Reconnect error:', error);
            this.showToast('Failed to reconnect to UPnP server', 'error');
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }

    async triggerScan() {
        const btn = document.getElementById('scan-btn');
        const originalText = btn.innerHTML;
        
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Scanning...';
        btn.disabled = true;
        
        try {
            const response = await fetch(`${this.apiBase}/scan`, { method: 'POST' });
            if (!response.ok) throw new Error('Scan failed');
            
            this.showToast('Media scan started', 'success');
            
            // Reload media files after a delay
            setTimeout(() => {
                this.loadMediaFiles();
            }, 2000);
            
        } catch (error) {
            console.error('Scan error:', error);
            this.showToast('Failed to start scan', 'error');
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }

    showPlaylistModal(withSelection = false) {
        const modal = document.getElementById('playlist-modal');
        const nameInput = document.getElementById('playlist-name');
        const descInput = document.getElementById('playlist-description');
        
        // Clear inputs
        nameInput.value = '';
        descInput.value = '';
        
        if (withSelection && this.selectedItems.size > 0) {
            nameInput.value = `Playlist ${new Date().toLocaleDateString()}`;
            descInput.value = `Playlist with ${this.selectedItems.size} selected items`;
        }
        
        modal.classList.add('show');
        nameInput.focus();
    }

    hidePlaylistModal() {
        const modal = document.getElementById('playlist-modal');
        modal.classList.remove('show');
    }

    async createPlaylist() {
        const name = document.getElementById('playlist-name').value.trim();
        const description = document.getElementById('playlist-description').value.trim();
        
        if (!name) {
            this.showToast('Please enter a playlist name', 'warning');
            return;
        }
        
        const selectedFiles = this.mediaFiles.filter(file => this.selectedItems.has(file.id));
        const filePaths = selectedFiles.map(file => file.path);
        
        if (filePaths.length === 0) {
            this.showToast('Please select some media files first', 'warning');
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBase}/playlists`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    description,
                    file_paths: filePaths
                })
            });
            
            if (!response.ok) throw new Error('Failed to create playlist');
            
            const playlist = await response.json();
            this.playlists.push(playlist);
            
            this.hidePlaylistModal();
            this.clearSelection();
            this.renderPlaylists();
            this.renderSidebarPlaylists();
            this.showToast('Playlist created successfully', 'success');
            
        } catch (error) {
            console.error('Create playlist error:', error);
            this.showToast('Failed to create playlist', 'error');
        }
    }

    async generateAutoPlaylists() {
        const btn = document.getElementById('auto-generate-btn');
        const originalText = btn.innerHTML;
        
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
        btn.disabled = true;
        
        try {
            const response = await fetch(`${this.apiBase}/playlists/auto/generate`);
            if (!response.ok) throw new Error('Auto-generation failed');
            
            const data = await response.json();
            this.showToast(`Generated ${data.total} automatic playlists`, 'success');
            
            // Reload playlists
            await this.loadPlaylists();
            
        } catch (error) {
            console.error('Auto-generate error:', error);
            this.showToast('Failed to generate playlists', 'error');
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }

    async viewPlaylist(playlistId) {
        const playlist = this.playlists.find(p => p.id === playlistId);
        if (!playlist) return;
        
        // Clear current selection and select playlist items
        this.clearSelection();
        
        const playlistFiles = this.mediaFiles.filter(file => 
            playlist.file_paths.includes(file.path)
        );
        
        playlistFiles.forEach(file => {
            this.selectedItems.add(file.id);
        });
        
        this.renderMediaFiles();
        this.renderSelectedItems();
        this.switchTab('media');
        
        this.showToast(`Viewing playlist: ${playlist.name}`, 'success');
    }

    async downloadPlaylist(playlistId) {
        try {
            const response = await fetch(`${this.apiBase}/playlists/${playlistId}/download`);
            if (!response.ok) throw new Error('Download failed');
            
            const blob = await response.blob();
            
            // Extract filename from Content-Disposition header, fallback to playlist name
            let filename = 'playlist.vlc.m3u';
            const contentDisposition = response.headers.get('Content-Disposition');
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                if (filenameMatch) {
                    filename = filenameMatch[1];
                }
            } else {
                // Fallback: use playlist name with .vlc.m3u extension
                const playlist = this.playlists.find(p => p.id === playlistId);
                if (playlist) {
                    const safeName = playlist.name.replace(/[^a-zA-Z0-9 \-_]/g, '_');
                    filename = `${safeName}.vlc.m3u`;
                }
            }
            
            // Create download link
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            this.showToast('Playlist downloaded', 'success');
            
        } catch (error) {
            console.error('Download error:', error);
            this.showToast('Failed to download playlist', 'error');
        }
    }

    setMode(mode) {
        this.mode = mode;
        const panel = document.getElementById('current-playlist');
        panel.dataset.mode = mode;

        const isEditing = mode === 'editing';
        document.getElementById('panel-title-build').hidden = isEditing;
        document.getElementById('panel-title-edit').hidden = !isEditing;
        document.querySelector('.build-actions').hidden = isEditing;
        document.querySelector('.edit-actions').hidden = !isEditing;

        const banner = document.getElementById('edit-mode-banner');
        banner.hidden = !isEditing;
    }

    enterEditMode(playlistId) {
        const playlist = this.playlists.find(p => p.id === playlistId);
        if (!playlist) {
            this.showToast('Playlist not found', 'error');
            return;
        }

        // If we're already editing a different playlist with unsaved changes, confirm first
        if (this.mode === 'editing' && this.editingPlaylistId !== playlistId && this.hasUnsavedEdits()) {
            if (!confirm('You have unsaved changes to another playlist. Discard them?')) {
                return;
            }
        }

        this.editingPlaylistId = playlistId;
        this.editSnapshot = {
            name: playlist.name,
            description: playlist.description || '',
            file_paths: [...playlist.file_paths],
        };

        // Populate selection from playlist contents (match by file.path)
        this.selectedItems.clear();
        for (const file of this.mediaFiles) {
            if (playlist.file_paths.includes(file.path)) {
                this.selectedItems.add(file.id);
            }
        }

        // Populate inputs and banner
        document.getElementById('edit-playlist-name').value = playlist.name;
        document.getElementById('edit-playlist-description').value = playlist.description || '';
        document.getElementById('edit-mode-banner-name').textContent = playlist.name;

        this.setMode('editing');
        this.switchTab('media');
        this.renderMediaFiles();
        this.renderSelectedItems();
    }

    exitEditMode({ clearSelection = true } = {}) {
        this.editingPlaylistId = null;
        this.editSnapshot = null;
        if (clearSelection) {
            this.selectedItems.clear();
        }
        document.getElementById('edit-playlist-name').value = '';
        document.getElementById('edit-playlist-description').value = '';
        document.getElementById('edit-mode-banner-name').textContent = '';
        this.setMode('building');
        this.renderMediaFiles();
        this.renderSelectedItems();
    }

    hasUnsavedEdits() {
        if (this.mode !== 'editing' || !this.editSnapshot) return false;
        const name = document.getElementById('edit-playlist-name').value.trim();
        const description = document.getElementById('edit-playlist-description').value.trim();
        if (name !== this.editSnapshot.name) return true;
        if (description !== (this.editSnapshot.description || '')) return true;
        const current = this.currentEditedPaths().sort();
        const original = [...this.editSnapshot.file_paths].sort();
        return JSON.stringify(current) !== JSON.stringify(original);
    }

    currentEditedPaths() {
        return this.mediaFiles
            .filter(file => this.selectedItems.has(file.id))
            .map(file => file.path);
    }

    async saveEditedPlaylist() {
        if (this.mode !== 'editing' || this.editingPlaylistId == null) return;

        const name = document.getElementById('edit-playlist-name').value.trim();
        const description = document.getElementById('edit-playlist-description').value.trim();
        const file_paths = this.currentEditedPaths();

        if (!name) {
            this.showToast('Name is required', 'warning');
            return;
        }
        if (file_paths.length === 0) {
            this.showToast('Cannot save an empty playlist', 'warning');
            return;
        }

        try {
            const response = await fetch(`${this.apiBase}/playlists/${this.editingPlaylistId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, description, file_paths }),
            });

            if (response.status === 404) {
                this.showToast('Playlist no longer exists', 'error');
                this.exitEditMode();
                await this.loadPlaylists();
                return;
            }
            if (response.status === 409) {
                this.showToast(`A playlist named "${name}" already exists`, 'error');
                return;
            }
            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw new Error(data.detail || 'Save failed');
            }

            await this.loadPlaylists();
            this.showToast(`Saved "${name}"`, 'success');
            this.exitEditMode();
        } catch (error) {
            console.error('Save edit error:', error);
            this.showToast(`Save failed: ${error.message}`, 'error');
        }
    }

    cancelEdit() {
        if (this.hasUnsavedEdits()) {
            if (!confirm('Discard unsaved changes?')) return;
        }
        this.exitEditMode();
    }

    saveAsNew() {
        if (this.mode !== 'editing') return;
        const name = document.getElementById('edit-playlist-name').value.trim();
        const description = document.getElementById('edit-playlist-description').value.trim();
        // Reuse the create modal but pre-fill from edit mode
        this.showPlaylistModal(true);
        if (name) document.getElementById('playlist-name').value = name + ' (copy)';
        if (description) document.getElementById('playlist-description').value = description;
    }

    async uploadM3U(file) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${this.apiBase}/playlists/import`, {
                method: 'POST',
                body: formData,
            });
            const data = await response.json();

            if (!response.ok) {
                const detail = data?.details?.detail || data?.error || 'Import failed';
                this.showToast(`Import failed: ${detail}`, 'error');
                return;
            }

            await this.loadPlaylists();
            this.showToast(`Imported "${data.playlist.name}" (${data.matched} items)`, 'success');
            if (data.unmatched && data.unmatched.length > 0) {
                this.showToast(
                    `${data.unmatched.length} item(s) not found in catalog — re-scan to add them`,
                    'warning'
                );
            }
            this.enterEditMode(data.playlist.id);
        } catch (error) {
            console.error('Upload error:', error);
            this.showToast(`Import failed: ${error.message}`, 'error');
        }
    }

    async deletePlaylist(playlistId) {
        const playlist = this.playlists.find(p => p.id === playlistId);
        if (!playlist) return;
        
        if (!confirm(`Are you sure you want to delete "${playlist.name}"?`)) {
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBase}/playlists/${playlistId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) throw new Error('Delete failed');
            
            this.playlists = this.playlists.filter(p => p.id !== playlistId);
            this.renderPlaylists();
            this.renderSidebarPlaylists();
            this.showToast('Playlist deleted', 'success');
            
        } catch (error) {
            console.error('Delete error:', error);
            this.showToast('Failed to delete playlist', 'error');
        }
    }

    showLoading(show) {
        const loading = document.getElementById('loading');
        loading.classList.toggle('hidden', !show);
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }

    getEmptyState(title, description) {
        return `
            <div class="empty-state">
                <i class="fas fa-folder-open"></i>
                <h3>${title}</h3>
                <p>${description}</p>
            </div>
        `;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new MediaCatalogApp();
});
