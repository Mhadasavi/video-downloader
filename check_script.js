
        // DOM Elements
        const videoUrlInput = document.getElementById('videoUrl');
        const previewCard = document.getElementById('previewCard');
        const thumbImg = document.getElementById('thumbImg');
        const previewTitle = document.getElementById('previewTitle');
        const previewAuthor = document.getElementById('previewAuthor');
        const previewDuration = document.getElementById('previewDuration');
        const previewFormatLabel = document.getElementById('previewFormatLabel');
        
        const downloadFormat = document.getElementById('downloadFormat');
        const qualityWrapper = document.getElementById('qualityWrapper');
        const videoQuality = document.getElementById('videoQuality');
        
        const saveToggleContainer = document.getElementById('saveToggleContainer');
        const askSaveEnabled = document.getElementById('askSaveEnabled');
        
        const trimToggleContainer = document.getElementById('trimToggleContainer');
        const trimEnabled = document.getElementById('trimEnabled');
        const trimInputs = document.getElementById('trimInputs');
        const trimStart = document.getElementById('trimStart');
        const trimEnd = document.getElementById('trimEnd');
        
        const downloadBtn = document.getElementById('downloadBtn');
        const progressCard = document.getElementById('progressCard');
        const progressStatusText = document.getElementById('progressStatusText');
        const progressPercent = document.getElementById('progressPercent');
        const progressBar = document.getElementById('progressBar');
        const downloadSpeed = document.getElementById('downloadSpeed');
        const downloadEta = document.getElementById('downloadEta');
        const downloadFormatLabel = document.getElementById('downloadFormatLabel');
        const statusVisualContainer = document.getElementById('statusVisualContainer');
        
        const openSettings = document.getElementById('openSettings');
        const closeSettings = document.getElementById('closeSettings');
        const settingsModal = document.getElementById('settingsModal');
        const settingsDownloadFolder = document.getElementById('settingsDownloadFolder');
        const settingsFfmpegFolder = document.getElementById('settingsFfmpegFolder');
        const browseFolderBtn = document.getElementById('browseFolderBtn');
        const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');
        const saveSettingsBtn = document.getElementById('saveSettingsBtn');
        
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toastMessage');
        const toastIcon = document.getElementById('toastIcon');

        let appSettings = {};
        let activeDownloadState = 'idle';

        // Load Settings on Start
        async function fetchSettings() {
            try {
                const res = await fetch('/api/settings');
                appSettings = await res.json();
                settingsDownloadFolder.value = appSettings.download_path || '';
                settingsFfmpegFolder.value = appSettings.ffmpeg_path || '';
            } catch (err) {
                showToast("Failed to load settings.", "error");
            }
        }
        fetchSettings();

        // Toast Helper
        function showToast(message, type = 'success') {
            toastMessage.textContent = message;
            toast.className = `toast ${type}`;
            
            // Set Icon
            if (type === 'success') {
                toastIcon.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${window.getComputedStyle(document.documentElement).getPropertyValue('--success-color')}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>`;
            } else if (type === 'error') {
                toastIcon.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${window.getComputedStyle(document.documentElement).getPropertyValue('--danger-color')}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>`;
            } else {
                toastIcon.innerHTML = '';
            }
            
            toast.classList.add('active');
            setTimeout(() => {
                toast.classList.remove('active');
            }, 4000);
        }

        // Toggle Save Location Option
        saveToggleContainer.addEventListener('click', (e) => {
            if (e.target.id === 'askSaveEnabled' || e.target.closest('.slider')) return;
            askSaveEnabled.checked = !askSaveEnabled.checked;
        });

        // Toggle Trim Panel Visibility
        trimToggleContainer.addEventListener('click', (e) => {
            // Prevent double triggers due to nested elements
            if (e.target.id === 'trimEnabled' || e.target.closest('.slider')) return;
            trimEnabled.checked = !trimEnabled.checked;
            trimEnabled.dispatchEvent(new Event('change'));
        });

        trimEnabled.addEventListener('change', () => {
            if (trimEnabled.checked) {
                trimInputs.style.display = 'grid';
            } else {
                trimInputs.style.display = 'none';
            }
        });

        // Toggle Quality dropdown based on MP4/MP3 format
        downloadFormat.addEventListener('change', () => {
            if (downloadFormat.value === 'mp3') {
                qualityWrapper.style.opacity = '0.4';
                videoQuality.disabled = true;
                trimToggleContainer.style.opacity = '0.4';
                trimEnabled.disabled = true;
                trimEnabled.checked = false;
                trimInputs.style.display = 'none';
            } else {
                qualityWrapper.style.opacity = '1';
                videoQuality.disabled = false;
                trimToggleContainer.style.opacity = '1';
                trimEnabled.disabled = false;
            }
        });

        // Fetch Metadata on URL Paste/Blur
        let fetchTimeout;
        videoUrlInput.addEventListener('input', () => {
            clearTimeout(fetchTimeout);
            const url = videoUrlInput.value.trim();
            if (url.startsWith('http://') || url.startsWith('https://')) {
                fetchTimeout = setTimeout(fetchMetadata, 800);
            }
        });

        async function fetchMetadata() {
            const url = videoUrlInput.value.trim();
            if (!url) return;
            
            previewCard.style.display = 'block';
            previewCard.classList.add('loading');
            
            previewTitle.innerHTML = '<div class="skeleton" style="height: 18px; width: 80%; margin-bottom: 8px;"></div><div class="skeleton" style="height: 18px; width: 50%;"></div>';
            previewAuthor.innerHTML = '<div class="skeleton" style="height: 12px; width: 30%;"></div>';
            previewDuration.innerHTML = '<div class="skeleton" style="height: 12px; width: 40px;"></div>';
            
            const thumbPlaceholder = document.getElementById('thumbPlaceholder');
            thumbImg.style.display = 'none';
            if (thumbPlaceholder) thumbPlaceholder.style.display = 'flex';
            
            // Disable button locally to show analyzing progress
            downloadBtn.disabled = true;
            downloadBtn.innerHTML = `
                <svg class="spinner" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="12" y1="2" x2="12" y2="6"></line>
                    <line x1="12" y1="18" x2="12" y2="22"></line>
                    <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
                    <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
                    <line x1="2" y1="12" x2="6" y2="12"></line>
                    <line x1="18" y1="12" x2="22" y2="12"></line>
                    <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
                    <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
                </svg>
                <span>Analyzing Link...</span>
            `;
            
            try {
                const res = await fetch('/api/info', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });
                
                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.error || "Failed to fetch metadata.");
                }
                
                const meta = await res.json();
                previewTitle.textContent = meta.title;
                previewAuthor.textContent = meta.uploader;
                previewDuration.textContent = meta.duration;
                
                if (meta.thumbnail) {
                    thumbImg.src = meta.thumbnail;
                    thumbImg.style.display = 'block';
                    if (thumbPlaceholder) thumbPlaceholder.style.display = 'none';
                }
                
                previewCard.classList.remove('loading');
                
                // Fetch related videos in parallel
                fetchRelatedVideos(meta.title, meta.uploader);
                
                // Only enable download button if the backend is idle
                if (['idle', 'completed', 'error'].includes(activeDownloadState)) {
                    downloadBtn.disabled = false;
                    downloadBtn.innerHTML = `
                        <svg class="download-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        <span>Download Media</span>
                    `;
                }
                
            } catch (err) {
                previewTitle.textContent = "Invalid video link or extraction error.";
                previewAuthor.textContent = "Error";
                previewCard.classList.remove('loading');
                if (thumbPlaceholder) thumbPlaceholder.style.display = 'none';
                showToast(err.message, "error");
                
                if (['idle', 'completed', 'error'].includes(activeDownloadState)) {
                    downloadBtn.disabled = false;
                    downloadBtn.innerHTML = `
                        <svg class="download-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                        <span>Download Media</span>
                    `;
                }
            }
        }

        // Trigger Download
        downloadBtn.addEventListener('click', async () => {
            const url = videoUrlInput.value.trim();
            if (!url) {
                showToast("Please enter a video URL first.", "error");
                return;
            }

            let customPath = null;
            if (askSaveEnabled.checked) {
                try {
                    downloadBtn.disabled = true;
                    downloadBtn.innerHTML = `
                        <svg class="spinner" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="12" y1="2" x2="12" y2="6"></line>
                            <line x1="12" y1="18" x2="12" y2="22"></line>
                            <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
                            <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
                            <line x1="2" y1="12" x2="6" y2="12"></line>
                            <line x1="18" y1="12" x2="22" y2="12"></line>
                            <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
                            <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
                        </svg>
                        <span>Choosing folder...</span>
                    `;
                    const res = await fetch('/api/select-folder', { method: 'POST' });
                    const data = await res.json();
                    
                    if (data.selected) {
                        customPath = data.selected;
                    } else {
                        showToast("Download cancelled (no folder chosen).", "error");
                        resetDownloadButtonState();
                        return;
                    }
                } catch (err) {
                    showToast("Failed to select folder.", "error");
                    resetDownloadButtonState();
                    return;
                }
            }

            const body = {
                url,
                format: downloadFormat.value,
                quality: videoQuality.value,
                trim_enabled: trimEnabled.checked,
                trim_start: trimStart.value,
                trim_end: trimEnd.value,
                download_path: customPath
            };

            try {
                const res = await fetch('/api/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });
                
                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.error || "Download could not be initiated.");
                }
                
                statusVisualContainer.innerHTML = '';
                progressCard.style.display = 'block';
                downloadBtn.disabled = true;
                videoUrlInput.disabled = true;
                
            } catch (err) {
                showToast(err.message, "error");
            }
        });

        // SSE Real-time Updates Setup
        const evtSource = new EventSource("/api/progress");
        
        evtSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (!data) return;
            
            activeDownloadState = data.status;
            
            // Format format text
            downloadFormatLabel.textContent = downloadFormat.value.toUpperCase();
            
            // Update inputs and buttons depending on status
            if (['downloading', 'fetching', 'processing', 'trimming'].includes(data.status)) {
                downloadBtn.disabled = true;
                downloadBtn.classList.add('downloading-btn');
                downloadBtn.innerHTML = `
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="12" y1="2" x2="12" y2="6"></line>
                        <line x1="12" y1="18" x2="12" y2="22"></line>
                        <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
                        <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
                        <line x1="2" y1="12" x2="6" y2="12"></line>
                        <line x1="18" y1="12" x2="22" y2="12"></line>
                        <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
                        <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
                    </svg>
                    <span>${data.status.charAt(0).toUpperCase() + data.status.slice(1)}...</span>
                `;
                progressCard.style.display = 'block';
                videoUrlInput.disabled = true;
            } else {
                downloadBtn.disabled = false;
                downloadBtn.classList.remove('downloading-btn');
                downloadBtn.innerHTML = `
                    <svg class="download-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    <span>Download Media</span>
                `;
                videoUrlInput.disabled = false;
            }

            // Sync visual metadata in preview card if fetched on back-end
            if (data.title && data.title !== 'Fetching metadata...') {
                previewCard.style.display = 'block';
                previewTitle.textContent = data.title;
                previewAuthor.textContent = data.uploader;
                previewDuration.textContent = data.duration;
                if (data.thumbnail) thumbImg.src = data.thumbnail;
            }

            // Update Progress UI elements
            progressBar.style.width = `${data.percent}%`;
            progressPercent.textContent = `${data.percent}%`;
            
            // Format status labels
            let statusText = "Ready";
            let dotColor = "rgba(255,255,255,0.2)";
            let isPulse = false;

            if (data.status === 'fetching') {
                statusText = "Loading details...";
                dotColor = varColor('--warning-color');
                isPulse = true;
                downloadSpeed.textContent = "N/A";
                downloadEta.textContent = "N/A";
            } else if (data.status === 'downloading') {
                statusText = `Downloading (${data.percent}%)`;
                dotColor = "#6366f1";
                isPulse = true;
                downloadSpeed.textContent = data.speed || 'N/A';
                downloadEta.textContent = data.eta || 'N/A';
            } else if (data.status === 'processing') {
                const isAudio = downloadFormat.value === 'mp3';
                statusText = isAudio ? "Extracting audio..." : "Blending streams...";
                dotColor = varColor('--warning-color');
                isPulse = true;
                downloadSpeed.textContent = data.speed || (isAudio ? "Converting..." : "FFmpeg merging");
                downloadEta.textContent = data.eta || "Processing";
            } else if (data.status === 'trimming') {
                statusText = "Trimming clip...";
                dotColor = varColor('--danger-color');
                isPulse = true;
                downloadSpeed.textContent = "FFmpeg cutting";
                downloadEta.textContent = "Processing";
            } else if (data.status === 'completed') {
                statusText = "Success";
                dotColor = varColor('--success-color');
                downloadSpeed.textContent = "Done";
                downloadEta.textContent = "0s";
                
                // Show completion checkmark visual
                statusVisualContainer.innerHTML = `
                    <div class="status-visual">
                        <svg width="60" height="60" viewBox="0 0 52 52" fill="none">
                            <circle cx="26" cy="26" r="25" stroke="${varColor('--success-color')}" stroke-width="3"></circle>
                            <path class="success-path" d="M14 27l10 10 16-18" stroke="${varColor('--success-color')}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"></path>
                        </svg>
                        <div class="status-title" style="color: var(--success-color)">Download Successful</div>
                        <div class="status-desc">${data.filepath ? getFilename(data.filepath) : 'File downloaded successfully'}</div>
                        <button class="browse-btn" onclick="openFileDirectory('${escapeFilePath(data.filepath)}')">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <circle cx="11" cy="11" r="8"></circle>
                                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                            </svg>
                            Reveal in Explorer
                        </button>
                    </div>
                `;
                showToast("Download completed successfully!");
            } else if (data.status === 'error') {
                statusText = "Download Failed";
                dotColor = varColor('--danger-color');
                downloadSpeed.textContent = "Error";
                downloadEta.textContent = "N/A";
                
                // Show error visual
                statusVisualContainer.innerHTML = `
                    <div class="status-visual shake-element">
                        <svg width="60" height="60" viewBox="0 0 52 52" fill="none">
                            <circle cx="26" cy="26" r="25" stroke="${varColor('--danger-color')}" stroke-width="3"></circle>
                            <path class="cross-path1" d="M16 16l20 20" stroke="${varColor('--danger-color')}" stroke-width="4" stroke-linecap="round"></path>
                            <path class="cross-path2" d="M36 16L16 36" stroke="${varColor('--danger-color')}" stroke-width="4" stroke-linecap="round"></path>
                        </svg>
                        <div class="status-title" style="color: var(--danger-color)">Error Occurred</div>
                        <div class="status-desc" style="max-width: 80%; line-height: 1.4">${data.error || 'An error occurred during download'}</div>
                    </div>
                `;
                showToast(data.error || "An error occurred.", "error");
            }

            progressStatusText.innerHTML = `
                <span class="dot ${isPulse ? 'pulse' : ''}" style="background-color: ${dotColor}"></span>
                <span>${statusText}</span>
            `;
        };

        function varColor(variableName) {
            return window.getComputedStyle(document.documentElement).getPropertyValue(variableName).trim();
        }

        function getFilename(path) {
            return path.split(/[\\/]/).pop();
        }

        function escapeFilePath(path) {
            return path.replace(/\\/g, '\\\\');
        }

        // Settings Modal Handlers
        openSettings.addEventListener('click', () => {
            settingsModal.classList.add('active');
        });
        
        const closeModal = () => {
            settingsModal.classList.remove('active');
        };
        
        closeSettings.addEventListener('click', closeModal);
        cancelSettingsBtn.addEventListener('click', closeModal);
        
        settingsModal.addEventListener('click', (e) => {
            if (e.target === settingsModal) closeModal();
        });

        // Browse Folder Button (triggers native Dialog via Flask server)
        browseFolderBtn.addEventListener('click', async () => {
            browseFolderBtn.disabled = true;
            try {
                const res = await fetch('/api/select-folder', { method: 'POST' });
                const data = await res.json();
                if (data.selected) {
                    settingsDownloadFolder.value = data.selected;
                }
            } catch (err) {
                showToast("Failed to open folder chooser.", "error");
            } finally {
                browseFolderBtn.disabled = false;
            }
        });

        // Save Settings
        saveSettingsBtn.addEventListener('click', async () => {
            const body = {
                download_path: settingsDownloadFolder.value.trim(),
                ffmpeg_path: settingsFfmpegFolder.value.trim()
            };

            try {
                const res = await fetch('/api/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });
                
                if (!res.ok) throw new Error("Could not save settings.");
                
                const data = await res.json();
                appSettings = data.settings;
                showToast("Settings saved successfully.");
                closeModal();
            } catch (err) {
                showToast(err.message, "error");
            }
        });

        // Fallback placeholder/explorer reveal helper
        function openFileDirectory(filePath) {
            // Note: Since this runs in a local browser, we could add an API endpoint to openexplorer if we want.
            // Let's create an endpoint in app.py to reveal the folder, it is extremely premium!
            // Let's call the API endpoint /api/reveal
            fetch('/api/reveal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: filePath })
            }).then(res => {
                if (!res.ok) showToast("Could not open file location.", "error");
            }).catch(() => {
                showToast("Could not open file location.", "error");
            });
        }

        // Fetch Related Videos using ytsearch
        async function fetchRelatedVideos(title, uploader) {
            const sidebarPanel = document.getElementById('sidebarPanel');
            const relatedList = document.getElementById('relatedList');
            
            sidebarPanel.style.display = 'block';
            relatedList.innerHTML = `
                <div style="display: flex; justify-content: center; padding: 30px 0;">
                    <svg class="spinner" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-secondary)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="12" y1="2" x2="12" y2="6"></line>
                        <line x1="12" y1="18" x2="12" y2="22"></line>
                        <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
                        <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
                        <line x1="2" y1="12" x2="6" y2="12"></line>
                        <line x1="18" y1="12" x2="22" y2="12"></line>
                        <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
                        <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
                    </svg>
                </div>
            `;
            
            try {
                const res = await fetch('/api/related', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, uploader })
                });
                
                if (!res.ok) throw new Error("Failed to fetch related videos.");
                
                const videos = await res.json();
                
                if (videos.length === 0) {
                    relatedList.innerHTML = '<div style="color: var(--text-secondary); text-align: center; padding: 20px 0; font-size: 13px;">No related videos found.</div>';
                    return;
                }
                
                relatedList.innerHTML = '';
                videos.forEach(video => {
                    const card = document.createElement('div');
                    card.className = 'related-card';
                    card.innerHTML = `
                        <div class="related-thumb-wrapper">
                            <img class="related-thumb" src="${video.thumbnail}" alt="">
                            <span class="related-duration">${video.duration}</span>
                        </div>
                        <div class="related-info">
                            <div class="related-title" title="${video.title}">${video.title}</div>
                            <div class="related-uploader">${video.uploader}</div>
                        </div>
                    `;
                    
                    card.addEventListener('click', () => {
                        videoUrlInput.value = video.url;
                        fetchMetadata();
                    });
                    
                    relatedList.appendChild(card);
                });
                
            } catch (err) {
                relatedList.innerHTML = `<div style="color: var(--danger-color); text-align: center; padding: 20px 0; font-size: 13px;">Error loading related videos.</div>`;
            }
        }

        // Helper to reset download button UI
        function resetDownloadButtonState() {
            downloadBtn.disabled = false;
            downloadBtn.classList.remove('downloading-btn');
            downloadBtn.innerHTML = `
                <svg class="download-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                <span>Download Media</span>
            `;
            videoUrlInput.disabled = false;
        }
        
        // Hide sidebar when URL input is cleared
        videoUrlInput.addEventListener('input', () => {
            if (!videoUrlInput.value.trim()) {
                document.getElementById('sidebarPanel').style.display = 'none';
                previewCard.style.display = 'none';
            }
        });
        
        // Hide sidebar if error occurs during download
        evtSource.addEventListener('message', (e) => {
            const data = JSON.parse(e.data);
            if (data && data.status === 'error') {
                document.getElementById('sidebarPanel').style.display = 'none';
            }
        });
        
        // Close related sidebar when settings modal opens, to look cleaner on small screens
        openSettings.addEventListener('click', () => {
            if (window.innerWidth <= 1024) {
                document.getElementById('sidebarPanel').style.display = 'none';
            }
        });
        
        // When download starts, hide related videos sidebar to keep layout compact and clean
        downloadBtn.addEventListener('click', () => {
            if (videoUrlInput.value.trim() && !askSaveEnabled.checked) {
                document.getElementById('sidebarPanel').style.display = 'none';
            }
        });
        
        // Listen to events and hide sidebar if download starts
        evtSource.addEventListener('message', (e) => {
            const data = JSON.parse(e.data);
            if (data && ['downloading', 'processing', 'trimming'].includes(data.status)) {
                document.getElementById('sidebarPanel').style.display = 'none';
            }
        });
        
        // Show related sidebar again on completed/error if we still have url
        evtSource.addEventListener('message', (e) => {
            const data = JSON.parse(e.data);
            if (data && ['completed', 'error'].includes(data.status) && videoUrlInput.value.trim()) {
                const previewTitleVal = previewTitle.textContent;
                if (previewTitleVal && previewTitleVal !== 'Video Title Loading...' && previewTitleVal !== 'Analyzing link, please wait...') {
                    document.getElementById('sidebarPanel').style.display = 'block';
                }
            }
        });
        
        // Ensure settings are synced on modal open
        openSettings.addEventListener('click', () => {
            fetchSettings();
        });
        
        // Prevent toggle issue
        document.getElementById('saveToggleContainer').addEventListener('click', (e) => {
            if (e.target.id === 'askSaveEnabled' || e.target.closest('.slider')) return;
            askSaveEnabled.checked = !askSaveEnabled.checked;
        });
    