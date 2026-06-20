/**
 * K5 Studio — YouTube Downloader Frontend
 * Handles video info fetching, format selection, download progress, and file saving.
 */

(() => {
    'use strict';

    // ─── Configuration ──────────────────────────────────────────────────────
    // Auto-detect API base URL based on current location
    const API_BASE = (() => {
        const loc = window.location;
        // If served from the Flask app itself (e.g. /YouTubeDownloaderApi/)
        if (loc.pathname.includes('/YouTubeDownloaderApi')) {
            return loc.pathname.replace(/\/$/, '') + '/api';
        }
        // If served from a custom domain (k5-studio.dev), point to Heroku backend
        return 'https://bot-launcher-discord-017f7d5f49d9.herokuapp.com/YouTubeDownloaderApi/api';
    })();

    const POLL_INTERVAL = 1000; // ms
    const HEARTBEAT_INTERVAL = 15000; // ms
    const STATS_REFRESH_INTERVAL = 30000; // ms
    const SESSION_ID = (() => {
        let sid = sessionStorage.getItem('ytdl-sid');
        if (!sid) {
            sid = Math.random().toString(36).substring(2, 10);
            sessionStorage.setItem('ytdl-sid', sid);
        }
        return sid;
    })();

    // ─── DOM Elements ───────────────────────────────────────────────────────
    const $ = (s) => document.querySelector(s);
    const urlInput = $('#url-input');
    const fetchBtn = $('#fetch-btn');
    const searchError = $('#search-error');
    const previewSection = $('#preview-section');
    const previewThumbnail = $('#preview-thumbnail');
    const previewDuration = $('#preview-duration');
    const previewTitle = $('#preview-title');
    const previewUploader = $('#preview-uploader');
    const previewDate = $('#preview-date');
    const previewViews = $('#preview-views');
    const previewLikes = $('#preview-likes');
    const previewCategories = $('#preview-categories');
    const previewDescWrapper = $('#preview-description-wrapper');
    const previewDesc = $('#preview-description');
    const toggleDescBtn = $('#toggle-description');
    const btnMp3 = $('#btn-mp3');
    const btnMp4 = $('#btn-mp4');
    const qualitySelector = $('#quality-selector');
    const qualityOptions = $('#quality-options');
    const downloadBtn = $('#download-btn');
    const downloadBtnText = $('.download-btn-text');
    const progressSection = $('#progress-section');
    const progressTitle = $('#progress-title');
    const progressStatus = $('#progress-status');
    const progressBar = $('#progress-bar');
    const progressPercent = $('#progress-percent');
    const doneSection = $('#done-section');
    const doneFilename = $('#done-filename');
    const doneDownloadLink = $('#done-download-link');
    const newDownloadBtn = $('#new-download-btn');
    const playlistSection = $('#playlist-section');
    const playlistThumbnail = $('#playlist-thumbnail');
    const playlistTitle = $('#playlist-title');
    const playlistUploader = $('#playlist-uploader');
    const playlistCount = $('#playlist-count');
    const playlistDuration = $('#playlist-duration');
    const playlistVideos = $('#playlist-videos');
    const playlistDownloadAll = $('#playlist-download-all');

    // ─── State ──────────────────────────────────────────────────────────────
    let currentVideoInfo = null;
    let selectedFormat = 'mp3';
    let selectedQuality = '720';
    let pollTimer = null;
    let playlistQueue = null; // { videos:[], current:0, cancelled:false }

    // ─── Stats Bar Toggle ───────────────────────────────────────────────────
    const statsToggle = document.getElementById('stats-toggle');
    const statsBar = document.getElementById('stats-bar');
    if (statsToggle && statsBar) {
        statsToggle.addEventListener('click', () => {
            statsBar.classList.toggle('expanded');
        });
    }

    // ─── Particles Background ───────────────────────────────────────────────
    function initParticles() {
        const canvas = document.getElementById('particles-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        let particles = [];
        const PARTICLE_COUNT = 40;

        function resize() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        resize();
        window.addEventListener('resize', resize);

        function createParticle() {
            return {
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                vx: (Math.random() - 0.5) * 0.3,
                vy: (Math.random() - 0.5) * 0.3,
                radius: Math.random() * 1.5 + 0.5,
                alpha: Math.random() * 0.3 + 0.05,
            };
        }

        for (let i = 0; i < PARTICLE_COUNT; i++) {
            particles.push(createParticle());
        }

        function draw() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            particles.forEach((p) => {
                p.x += p.vx;
                p.y += p.vy;

                // Wrap around
                if (p.x < 0) p.x = canvas.width;
                if (p.x > canvas.width) p.x = 0;
                if (p.y < 0) p.y = canvas.height;
                if (p.y > canvas.height) p.y = 0;

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(139, 92, 246, ${p.alpha})`;
                ctx.fill();
            });

            // Draw connections
            for (let i = 0; i < particles.length; i++) {
                for (let j = i + 1; j < particles.length; j++) {
                    const dx = particles[i].x - particles[j].x;
                    const dy = particles[i].y - particles[j].y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < 150) {
                        ctx.beginPath();
                        ctx.moveTo(particles[i].x, particles[i].y);
                        ctx.lineTo(particles[j].x, particles[j].y);
                        ctx.strokeStyle = `rgba(139, 92, 246, ${0.04 * (1 - dist / 150)})`;
                        ctx.lineWidth = 0.5;
                        ctx.stroke();
                    }
                }
            }

            requestAnimationFrame(draw);
        }
        draw();
    }

    // ─── Helpers ────────────────────────────────────────────────────────────
    function showError(msg) {
        searchError.textContent = msg;
        searchError.classList.remove('hidden');
    }

    function hideError() {
        searchError.classList.add('hidden');
    }

    function formatCount(n, suffix) {
        if (!n) return '0 ' + suffix;
        if (n >= 1_000_000_000) return (n / 1_000_000_000).toFixed(1) + 'B ' + suffix;
        if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M ' + suffix;
        if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K ' + suffix;
        return n.toLocaleString() + ' ' + suffix;
    }

    function formatViews(n) {
        return formatCount(n, 'views');
    }

    function formatLikes(n) {
        return formatCount(n, 'likes');
    }

    function setLoading(btn, loading) {
        if (loading) {
            btn.classList.add('loading');
            btn.disabled = true;
        } else {
            btn.classList.remove('loading');
            btn.disabled = false;
        }
    }

    // ─── Loading Status ────────────────────────────────────────────────────
    const loadingStatus = $('#loading-status');
    const loadingText = $('#loading-text');
    let loadingMsgTimer = null;

    function showLoading(text, messages) {
        loadingText.textContent = text;
        loadingStatus.classList.remove('hidden');
        if (loadingMsgTimer) clearInterval(loadingMsgTimer);
        if (messages && messages.length > 1) {
            let idx = 0;
            loadingMsgTimer = setInterval(() => {
                idx = (idx + 1) % messages.length;
                loadingText.textContent = messages[idx];
            }, 3000);
        }
    }

    function hideLoading() {
        loadingStatus.classList.add('hidden');
        if (loadingMsgTimer) { clearInterval(loadingMsgTimer); loadingMsgTimer = null; }
    }

    // ─── Fetch Video Info ───────────────────────────────────────────────────
    async function fetchVideoInfo() {
        const url = urlInput.value.trim();
        if (!url) {
            showError('Please paste a URL');
            return;
        }

        hideError();
        hideLoading();
        setLoading(fetchBtn, true);
        previewSection.classList.add('hidden');
        playlistSection.classList.add('hidden');
        progressSection.classList.add('hidden');
        doneSection.classList.add('hidden');

        // Show contextual loading messages
        const isPlaylist = url.includes('list=') || url.includes('/playlist');
        const isSpotify = url.includes('spotify.com');

        if (isSpotify) {
            showLoading('Connecting to Spotify...', [
                'Connecting to Spotify...',
                'Scraping track metadata...',
                'Resolving track names...',
                'Almost there...',
            ]);
        } else if (isPlaylist) {
            showLoading('Loading playlist...', [
                'Loading playlist...',
                'Extracting video metadata...',
                'This may take a moment for large playlists...',
                'Fetching thumbnails and durations...',
                'Still working — large playlists can take 10-30s...',
            ]);
        } else {
            showLoading('Fetching video info...', [
                'Fetching video info...',
                'Extracting available formats...',
                'Almost ready...',
            ]);
        }

        try {
            const res = await fetch(`${API_BASE}/info`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url }),
            });

            const data = await res.json();

            if (!res.ok) {
                showError(data.error || 'Failed to fetch video info');
                return;
            }

            currentVideoInfo = data;

            if (data.type === 'playlist') {
                renderPlaylist(data);
            } else {
                renderPreview(data);
            }

            // Track video fetch
            fetch(`${API_BASE}/track-fetch`, { method: 'POST', headers: { 'Content-Type': 'application/json' } }).catch(() => {});
        } catch (err) {
            showError('Network error. Please try again.');
            console.error(err);
        } finally {
            setLoading(fetchBtn, false);
            hideLoading();
        }
    }

    // ─── Render Preview Card ────────────────────────────────────────────────
    function renderPreview(info) {
        currentVideoInfo = info;
        previewThumbnail.src = info.thumbnail || '';
        previewDuration.textContent = info.duration_formatted || '0:00';
        previewTitle.textContent = info.title || 'Unknown Title';
        previewUploader.textContent = info.uploader || 'Unknown Channel';
        previewDate.textContent = info.upload_date || '';
        previewViews.querySelector('span').textContent = formatViews(info.view_count);
        previewLikes.querySelector('span').textContent = formatLikes(info.like_count);

        // Categories
        if (info.categories && info.categories.length > 0) {
            previewCategories.innerHTML = '';
            info.categories.forEach(cat => {
                const tag = document.createElement('span');
                tag.className = 'category-tag';
                tag.textContent = cat;
                previewCategories.appendChild(tag);
            });
            previewCategories.classList.remove('hidden');
        } else {
            previewCategories.classList.add('hidden');
        }

        // Description
        if (info.description && info.description.trim()) {
            previewDesc.textContent = info.description;
            previewDescWrapper.classList.remove('hidden');
            // Reset collapsed state
            previewDesc.classList.remove('expanded');
            toggleDescBtn.textContent = 'Show more';
        } else {
            previewDescWrapper.classList.add('hidden');
        }

        // Render quality options for MP4
        renderQualityOptions(info.formats || []);

        // Show preview
        previewSection.classList.remove('hidden');

        // Scroll into view
        previewSection.scrollIntoView({ behavior: 'smooth', block: 'center' });

        updateDownloadButtonText();
    }

    function renderQualityOptions(formats) {
        qualityOptions.innerHTML = '';

        // If no formats from API, provide defaults
        const qualities = formats.length > 0
            ? formats.map((f) => f.quality)
            : ['1080p', '720p', '480p', '360p'];

        // Deduplicate
        const unique = [...new Set(qualities)];

        unique.forEach((q) => {
            const chip = document.createElement('button');
            chip.className = 'quality-chip';
            chip.textContent = q;
            chip.dataset.quality = q.replace('p', '');

            if (q.replace('p', '') === selectedQuality) {
                chip.classList.add('active');
            }

            chip.addEventListener('click', () => {
                document.querySelectorAll('.quality-chip').forEach((c) => c.classList.remove('active'));
                chip.classList.add('active');
                selectedQuality = chip.dataset.quality;
                updateDownloadButtonText();
            });

            qualityOptions.appendChild(chip);
        });

        // Auto-select 720p if available, else first
        if (!unique.some((q) => q.replace('p', '') === selectedQuality) && unique.length > 0) {
            selectedQuality = unique[0].replace('p', '');
            qualityOptions.firstChild?.classList.add('active');
        }
    }

    function formatFileSize(bytes) {
        if (!bytes || bytes <= 0) return '';
        const mb = bytes / (1024 * 1024);
        if (mb >= 1024) return (mb / 1024).toFixed(1) + ' GB';
        return mb.toFixed(1) + ' MB';
    }

    function updateDownloadButtonText() {
        let sizeStr = '';
        if (selectedFormat === 'mp3') {
            if (currentVideoInfo && currentVideoInfo.mp3_size_approx) {
                sizeStr = ' · ~' + formatFileSize(currentVideoInfo.mp3_size_approx);
            }
            downloadBtnText.textContent = 'Download MP3' + sizeStr;
        } else {
            // Find size for selected quality
            if (currentVideoInfo && currentVideoInfo.formats) {
                const fmt = currentVideoInfo.formats.find(f => f.quality === selectedQuality + 'p');
                if (fmt && fmt.filesize_approx) {
                    sizeStr = ' · ~' + formatFileSize(fmt.filesize_approx);
                }
            }
            downloadBtnText.textContent = `Download MP4 (${selectedQuality}p)` + sizeStr;
        }
    }

    // ─── Render Playlist ────────────────────────────────────────────────────
    const K5_API_BASE = 'https://bot-launcher-discord-017f7d5f49d9.herokuapp.com/K5ApiManager/api';

    function renderPlaylist(info) {
        playlistThumbnail.src = info.thumbnail || '';
        playlistTitle.textContent = info.title || 'Unknown Playlist';
        playlistUploader.textContent = info.uploader || '';
        playlistCount.querySelector('span').textContent = `${info.video_count} videos`;
        playlistDuration.querySelector('span').textContent = info.total_duration_formatted || '0m';

        // Build video list
        playlistVideos.innerHTML = '';
        const thumbsToFetch = []; // items needing cover art

        (info.videos || []).forEach((video, i) => {
            const item = document.createElement('div');
            item.className = 'playlist-video-item';

            item.innerHTML = `
                <span class="pv-index">${i + 1}</span>
                <img class="pv-thumb" src="${video.thumbnail || ''}" alt="" loading="lazy">
                <div class="pv-info">
                    <div class="pv-title" title="${video.title || ''}">${video.title || 'Unknown'}</div>
                    <div class="pv-sub">${video.uploader || ''}</div>
                </div>
                <span class="pv-duration">${video.duration_formatted || ''}</span>
                <button class="pv-download-btn" title="Download MP3" data-url="${video.url}">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                </button>
            `;

            // Individual download button
            const dlBtn = item.querySelector('.pv-download-btn');
            dlBtn.addEventListener('click', () => {
                downloadPlaylistVideo(video.url, video.title);
            });

            playlistVideos.appendChild(item);

            // Queue cover fetch for items without thumbnails
            if (!video.thumbnail) {
                const thumbEl = item.querySelector('.pv-thumb');
                thumbsToFetch.push({ el: thumbEl, query: video.title || '' });
            }
        });

        playlistSection.classList.remove('hidden');
        playlistSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // Fetch cover art for items without thumbnails (Spotify tracks)
        if (thumbsToFetch.length > 0) {
            fetchCoversLazy(thumbsToFetch);

            // Also fetch playlist header thumbnail if empty
            if (!info.thumbnail && info.videos && info.videos[0]) {
                fetchCover(info.videos[0].title).then(coverUrl => {
                    if (coverUrl) playlistThumbnail.src = coverUrl;
                });
            }
        }
    }

    async function fetchCover(query) {
        try {
            const coverBase = window.location.hostname === 'localhost'
                ? '/K5ApiManager/music/cover'
                : 'https://bot-launcher-discord-017f7d5f49d9.herokuapp.com/K5ApiManager/music/cover';
            const res = await fetch(`${coverBase}?q=${encodeURIComponent(query)}`);
            if (!res.ok) return null;
            const data = await res.json();
            return data.url || null;
        } catch (_) {
            return null;
        }
    }

    async function fetchCoversLazy(items) {
        // Fetch covers in small batches to avoid hammering the API
        for (let i = 0; i < items.length; i++) {
            const { el, query } = items[i];
            if (!query) continue;
            fetchCover(query).then(coverUrl => {
                if (coverUrl) {
                    el.src = coverUrl;
                }
            });
            // Stagger requests: 150ms delay between each
            if (i < items.length - 1) {
                await new Promise(r => setTimeout(r, 150));
            }
        }
    }

    async function downloadPlaylistVideo(videoUrl, title) {
        // Single track download from playlist — uses progress UI
        playlistSection.classList.add('hidden');
        progressSection.classList.remove('hidden');
        progressTitle.textContent = title || 'Downloading...';
        progressStatus.textContent = 'Starting...';
        progressBar.style.width = '0%';
        progressPercent.textContent = '0%';
        progressSection.scrollIntoView({ behavior: 'smooth', block: 'center' });

        try {
            const res = await fetch(`${API_BASE}/download`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: videoUrl, format: 'mp3', quality: '720', title: title || '' }),
            });
            const data = await res.json();
            if (!res.ok) {
                progressSection.classList.add('hidden');
                playlistSection.classList.remove('hidden');
                showError(data.error || 'Failed to start download');
                return;
            }
            pollJobStatus(data.job_id);
        } catch (err) {
            progressSection.classList.add('hidden');
            playlistSection.classList.remove('hidden');
            showError('Network error.');
        }
    }

    // ─── Download All (Sequential) ──────────────────────────────────────────
    const completedDownloads = $('#completed-downloads');
    const completedList = $('#completed-list');

    if (playlistDownloadAll) {
        playlistDownloadAll.addEventListener('click', () => {
            if (!currentVideoInfo || !currentVideoInfo.videos) return;

            playlistQueue = {
                videos: currentVideoInfo.videos,
                current: 0,
                cancelled: false,
            };

            // Reset completed list
            completedList.innerHTML = '';
            completedDownloads.classList.add('hidden');

            playlistSection.classList.add('hidden');
            progressSection.classList.remove('hidden');
            progressSection.scrollIntoView({ behavior: 'smooth', block: 'center' });

            downloadNextInQueue();
        });
    }

    async function downloadNextInQueue() {
        if (!playlistQueue || playlistQueue.cancelled) {
            finishPlaylistQueue('Cancelled');
            return;
        }

        const { videos, current } = playlistQueue;
        if (current >= videos.length) {
            finishPlaylistQueue('Complete');
            return;
        }

        const video = videos[current];
        const queueLabel = `${current + 1}/${videos.length}`;

        progressTitle.textContent = `${queueLabel} · ${video.title || 'Unknown'}`;
        progressStatus.textContent = 'Starting download...';
        progressBar.style.width = '0%';
        progressPercent.textContent = '0%';

        try {
            const res = await fetch(`${API_BASE}/download`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: video.url, format: 'mp3', quality: '720', title: video.title || '' }),
            });
            const data = await res.json();

            if (!res.ok || !data.job_id) {
                progressStatus.textContent = `Failed: ${data.error || 'Unknown error'} — skipping...`;
                await new Promise(r => setTimeout(r, 1500));
                playlistQueue.current++;
                downloadNextInQueue();
                return;
            }

            // Poll this job, when done auto-download and continue
            pollJobForQueue(data.job_id);
        } catch (err) {
            progressStatus.textContent = 'Network error — skipping...';
            await new Promise(r => setTimeout(r, 1500));
            playlistQueue.current++;
            downloadNextInQueue();
        }
    }

    function pollJobForQueue(jobId) {
        if (pollTimer) clearInterval(pollTimer);

        pollTimer = setInterval(async () => {
            if (playlistQueue && playlistQueue.cancelled) {
                clearInterval(pollTimer);
                finishPlaylistQueue('Cancelled');
                return;
            }

            try {
                const res = await fetch(`${API_BASE}/status/${jobId}`);
                const data = await res.json();

                const progress = data.progress || 0;
                progressBar.style.width = `${progress}%`;
                progressPercent.textContent = `${progress}%`;

                const statusMap = {
                    starting: 'Initializing...',
                    downloading: 'Downloading...',
                    converting: 'Converting to MP3...',
                    done: 'Complete!',
                    error: 'Error',
                };
                let statusText = statusMap[data.status] || data.status;
                if (data.status === 'downloading' && data.total_bytes > 0) {
                    const dlMB = (data.downloaded_bytes / (1024 * 1024)).toFixed(1);
                    const totalMB = (data.total_bytes / (1024 * 1024)).toFixed(1);
                    statusText = `Downloading... ${dlMB} / ${totalMB} MB`;
                }
                progressStatus.textContent = statusText;

                if (data.status === 'done') {
                    clearInterval(pollTimer);

                    const fileUrl = `${API_BASE}/file/${jobId}`;
                    const trackTitle = playlistQueue ? playlistQueue.videos[playlistQueue.current]?.title || 'Unknown' : 'Unknown';
                    const trackNum = playlistQueue ? playlistQueue.current + 1 : 1;

                    // Trigger download via hidden iframe (works cross-origin)
                    const iframe = document.createElement('iframe');
                    iframe.style.display = 'none';
                    iframe.src = fileUrl;
                    document.body.appendChild(iframe);
                    setTimeout(() => iframe.remove(), 10000);

                    // Add to completed list
                    addCompletedItem(trackNum, trackTitle, fileUrl);

                    // Show brief done status
                    progressStatus.innerHTML = `<a href="${fileUrl}" class="queue-save-link" download>✓ Done — Click to save file</a>`;
                    progressBar.style.width = '100%';
                    progressPercent.textContent = '100%';

                    // Move to next track after 2s
                    await new Promise(r => setTimeout(r, 2000));
                    if (playlistQueue && !playlistQueue.cancelled) {
                        playlistQueue.current++;
                        downloadNextInQueue();
                    }

                } else if (data.status === 'error') {
                    clearInterval(pollTimer);
                    progressStatus.textContent = `Failed: ${data.error || 'Download error'} — skipping...`;
                    await new Promise(r => setTimeout(r, 2000));
                    playlistQueue.current++;
                    downloadNextInQueue();
                }
            } catch (_) { /* keep polling */ }
        }, POLL_INTERVAL);
    }

    function addCompletedItem(num, title, fileUrl) {
        completedDownloads.classList.remove('hidden');

        const item = document.createElement('div');
        item.className = 'completed-item';
        item.innerHTML = `
            <span class="ci-index">${num}</span>
            <span class="ci-title" title="${title}">${title}</span>
            <a href="${fileUrl}" class="ci-download" download>Save</a>
        `;
        completedList.appendChild(item);

        // Auto-scroll to latest
        completedList.scrollTop = completedList.scrollHeight;
    }

    function finishPlaylistQueue(reason) {
        if (pollTimer) clearInterval(pollTimer);
        playlistQueue = null;
        progressSection.classList.add('hidden');

        if (currentVideoInfo && currentVideoInfo.type === 'playlist') {
            playlistSection.classList.remove('hidden');
            playlistSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    // Cancel button for playlist queue
    function getCancelBtn() {
        let btn = document.getElementById('queue-cancel-btn');
        if (!btn) {
            btn = document.createElement('button');
            btn.id = 'queue-cancel-btn';
            btn.className = 'download-btn queue-cancel-btn';
            btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="18" height="18"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg><span>Cancel Queue</span>`;
            btn.addEventListener('click', () => {
                if (playlistQueue) playlistQueue.cancelled = true;
            });
            // Insert after progress bar
            const progressCard = document.querySelector('.progress-card');
            if (progressCard) progressCard.appendChild(btn);
        }
        return btn;
    }

    // Show/hide cancel btn based on queue state — hook into downloadNextInQueue
    const origDownloadNext = downloadNextInQueue;
    downloadNextInQueue = function() {
        const cancelBtn = getCancelBtn();
        if (playlistQueue && !playlistQueue.cancelled) {
            cancelBtn.style.display = 'flex';
        } else {
            cancelBtn.style.display = 'none';
        }
        return origDownloadNext();
    };

    // Hide cancel btn when not in queue mode
    const origFinish = finishPlaylistQueue;
    finishPlaylistQueue = function(reason) {
        const cancelBtn = document.getElementById('queue-cancel-btn');
        if (cancelBtn) cancelBtn.style.display = 'none';
        return origFinish(reason);
    };

    // ─── Format Toggle ─────────────────────────────────────────────────────
    btnMp3.addEventListener('click', () => {
        selectedFormat = 'mp3';
        btnMp3.classList.add('active');
        btnMp4.classList.remove('active');
        qualitySelector.classList.add('hidden');
        updateDownloadButtonText();
    });

    btnMp4.addEventListener('click', () => {
        selectedFormat = 'mp4';
        btnMp4.classList.add('active');
        btnMp3.classList.remove('active');
        qualitySelector.classList.remove('hidden');
        updateDownloadButtonText();
    });

    // ─── Start Download ─────────────────────────────────────────────────────
    async function startDownload() {
        if (!currentVideoInfo) return;

        hideError();
        downloadBtn.disabled = true;
        previewSection.classList.add('hidden');
        progressSection.classList.remove('hidden');
        doneSection.classList.add('hidden');

        progressTitle.textContent = currentVideoInfo.title || 'Preparing download...';
        progressStatus.textContent = 'Starting...';
        progressBar.style.width = '0%';
        progressPercent.textContent = '0%';

        // Scroll to progress
        progressSection.scrollIntoView({ behavior: 'smooth', block: 'center' });

        try {
            const res = await fetch(`${API_BASE}/download`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    url: currentVideoInfo.url,
                    format: selectedFormat,
                    quality: selectedQuality,
                }),
            });

            const data = await res.json();

            if (!res.ok) {
                showDownloadError(data.error || 'Failed to start download');
                return;
            }

            // Start polling for status
            pollJobStatus(data.job_id);
        } catch (err) {
            showDownloadError('Network error. Please try again.');
            console.error(err);
        }
    }

    function pollJobStatus(jobId) {
        if (pollTimer) clearInterval(pollTimer);

        pollTimer = setInterval(async () => {
            try {
                const res = await fetch(`${API_BASE}/status/${jobId}`);
                const data = await res.json();

                if (!res.ok) {
                    clearInterval(pollTimer);
                    showDownloadError(data.error || 'Job not found');
                    return;
                }

                // Update progress UI
                const progress = data.progress || 0;
                progressBar.style.width = `${progress}%`;
                progressPercent.textContent = `${progress}%`;

                const statusMap = {
                    starting: 'Initializing...',
                    downloading: 'Downloading from YouTube...',
                    converting: 'Converting file...',
                    done: 'Complete!',
                    error: 'Error occurred',
                };
                let statusText = statusMap[data.status] || data.status;

                // Show MB progress during download
                if (data.status === 'downloading' && data.total_bytes > 0) {
                    const dlMB = (data.downloaded_bytes / (1024 * 1024)).toFixed(1);
                    const totalMB = (data.total_bytes / (1024 * 1024)).toFixed(1);
                    statusText = `Downloading... ${dlMB} MB / ${totalMB} MB`;
                }

                progressStatus.textContent = statusText;

                if (data.status === 'done') {
                    clearInterval(pollTimer);
                    showDone(jobId, data);
                } else if (data.status === 'error') {
                    clearInterval(pollTimer);
                    showDownloadError(data.error || 'Download failed');
                }
            } catch (err) {
                // Network hiccup, keep polling
                console.warn('Poll error:', err);
            }
        }, POLL_INTERVAL);
    }

    function showDownloadError(msg) {
        progressSection.classList.add('hidden');
        previewSection.classList.remove('hidden');
        downloadBtn.disabled = false;
        showError(msg);
    }

    function showDone(jobId, data) {
        progressSection.classList.add('hidden');
        doneSection.classList.remove('hidden');

        let filename = data.filename || 'download';
        // Remove job_id prefix for display
        if (filename.startsWith(jobId + '_')) {
            filename = filename.substring(jobId.length + 1);
        }
        doneFilename.textContent = filename;

        // Set download link
        const fileUrl = `${API_BASE}/file/${jobId}`;
        doneDownloadLink.href = fileUrl;
        doneDownloadLink.setAttribute('download', filename);

        // Scroll to done section
        doneSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // ─── Reset / New Download ───────────────────────────────────────────────
    function resetAll() {
        if (pollTimer) clearInterval(pollTimer);
        currentVideoInfo = null;

        urlInput.value = '';
        hideError();
        previewSection.classList.add('hidden');
        progressSection.classList.add('hidden');
        doneSection.classList.add('hidden');
        downloadBtn.disabled = false;

        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
        urlInput.focus();
    }

    // ─── Event Listeners ────────────────────────────────────────────────────
    fetchBtn.addEventListener('click', fetchVideoInfo);

    urlInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') fetchVideoInfo();
    });

    // Auto-fetch on paste
    urlInput.addEventListener('paste', () => {
        setTimeout(() => {
            const val = urlInput.value.trim();
            if (val && (val.includes('youtube.com') || val.includes('youtu.be') || val.includes('music.youtube.com'))) {
                fetchVideoInfo();
            }
        }, 100);
    });

    downloadBtn.addEventListener('click', startDownload);
    newDownloadBtn.addEventListener('click', resetAll);

    // Description toggle
    if (toggleDescBtn) {
        toggleDescBtn.addEventListener('click', () => {
            const isExpanded = previewDesc.classList.toggle('expanded');
            toggleDescBtn.textContent = isExpanded ? 'Show less' : 'Show more';
        });
    }

    // ─── Ads Configuration ───────────────────────────────────────────────────
    // ✨ To add a new ad, just add an object to this array:
    //    { image: 'URL to image', link: 'URL to open on click', alt: 'Description' }
    const ADS_CONFIG = [
        {
            image: 'https://raw.githubusercontent.com/kubadoPL/Gaming-Radio/main/Assets/Ads/Radio%20Gaming%20ad.png',
            link: 'https://radio-gaming.stream',
            alt: 'Radio Gaming — Free 24/7 Music Stream',
        },
        // Add more ads here ↓
        // {
        //     image: 'https://example.com/ad-image.png',
        //     link: 'https://example.com',
        //     alt: 'Ad description',
        // },
    ];

    const AD_ROTATE_INTERVAL = 45000; // ms — rotate ads every 45s

    // ─── Initialize ─────────────────────────────────────────────────────────
    initParticles();
    urlInput.focus();
    initStats();
    initHeartbeat();
    trackVisit();
    initUptime();
    initAds();



    function initAds() {
        if (ADS_CONFIG.length === 0) return;

        const adLeft = document.getElementById('ad-left');
        const adRight = document.getElementById('ad-right');
        const adInline = document.getElementById('ad-inline');

        function renderAd(container, adData, classPrefix) {
            container.innerHTML = '';

            // Close (X) button
            const closeBtn = document.createElement('button');
            closeBtn.className = 'ad-close-btn';
            closeBtn.innerHTML = '&times;';
            closeBtn.title = 'Close ad';
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                container.style.opacity = '0';
                container.style.transform += ' scale(0.95)';
                setTimeout(() => {
                    container.style.display = 'none';
                }, 300);
            });
            container.appendChild(closeBtn);

            const link = document.createElement('a');
            link.className = classPrefix + '-link';
            link.href = adData.link;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.title = adData.alt;

            const img = document.createElement('img');
            img.className = classPrefix + '-img';
            img.src = adData.image;
            img.alt = adData.alt;
            img.loading = 'lazy';

            link.appendChild(img);
            container.appendChild(link);

            const label = document.createElement('span');
            label.className = classPrefix + '-label';
            label.textContent = 'Ad';
            container.appendChild(label);
        }

        function pickRandom(exclude) {
            if (ADS_CONFIG.length === 1) return ADS_CONFIG[0];
            let pick;
            do {
                pick = ADS_CONFIG[Math.floor(Math.random() * ADS_CONFIG.length)];
            } while (pick === exclude && ADS_CONFIG.length > 1);
            return pick;
        }

        function showAds() {
            const inlineAd = pickRandom(null);

            // Inline banner (always visible on narrow screens, hidden on wide via CSS)
            if (adInline) {
                renderAd(adInline, inlineAd, 'ad-inline');
            }

            // Side ads (visible only on wide screens via CSS)
            if (adLeft && adRight) {
                const leftAd = pickRandom(null);

                // Only show both sides if we have different ads to show
                if (ADS_CONFIG.length > 1) {
                    const rightAd = pickRandom(leftAd);
                    renderAd(adLeft, leftAd, 'side-ad');
                    renderAd(adRight, rightAd, 'side-ad');
                } else {
                    // Only 1 ad — show on left side only, hide right
                    renderAd(adLeft, leftAd, 'side-ad');
                    adRight.style.display = 'none';
                }
            }
        }

        showAds();

        // Rotate ads periodically if there are multiple
        if (ADS_CONFIG.length > 1) {
            setInterval(showAds, AD_ROTATE_INTERVAL);
        }
    }

    // ─── Stats, Heartbeat, Visit Tracking ───────────────────────────────────

    function formatNum(n) {
        if (!n && n !== 0) return '...';
        n = Math.floor(n);
        if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
        if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
        return n.toLocaleString();
    }

    function setStatEl(id, value) {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    async function fetchStats() {
        try {
            const res = await fetch(`${API_BASE}/stats`, { cache: 'no-store' });
            if (!res.ok) return;
            const data = await res.json();
            const g = data.global || {};

            setStatEl('stat-online', (data.online || 0).toLocaleString());
            setStatEl('stat-visits', formatNum(g.total_visits || 0));
            setStatEl('stat-unique', formatNum(g.unique_visitors || 0));
            setStatEl('stat-fetched', formatNum(g.videos_fetched || 0));
            setStatEl('stat-mp3', formatNum((g.mp3_converted || 0)));
            setStatEl('stat-mp4', formatNum((g.mp4_converted || 0)));
            setStatEl('stat-downloaded', formatNum((g.mp3_downloaded || 0) + (g.mp4_downloaded || 0)));
        } catch (_) { /* silent */ }
    }

    function initStats() {
        fetchStats();
        setInterval(fetchStats, STATS_REFRESH_INTERVAL);
    }

    function initHeartbeat() {
        function sendHeartbeat() {
            fetch(`${API_BASE}/heartbeat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sid: SESSION_ID }),
            }).then(res => {
                if (res.ok) return res.json();
            }).then(data => {
                if (data && data.online !== undefined) {
                    setStatEl('stat-online', data.online.toLocaleString());
                }
            }).catch(() => {});
        }
        sendHeartbeat();
        setInterval(sendHeartbeat, HEARTBEAT_INTERVAL);
    }

    function trackVisit() {
        const VISITED_KEY = 'ytdl-visited';
        const isNew = !localStorage.getItem(VISITED_KEY);
        fetch(`${API_BASE}/track-visit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_new: isNew }),
        }).catch(() => {});
        if (isNew) {
            localStorage.setItem(VISITED_KEY, '1');
        }
    }

    function initUptime() {
        const UPTIME_API = 'https://bot-launcher-discord-017f7d5f49d9.herokuapp.com/K5ApiManager/api/uptime';
        let uptimeStartedAt = null;
        let uptimeInterval = null;

        function updateDisplay() {
            if (!uptimeStartedAt) return;
            const diff = Date.now() - uptimeStartedAt;
            const totalSec = Math.floor(diff / 1000);
            const d = Math.floor(totalSec / 86400);
            const h = Math.floor((totalSec % 86400) / 3600);
            const m = Math.floor((totalSec % 3600) / 60);
            const s = totalSec % 60;
            let text = '';
            if (d > 0) text += d + 'd ';
            if (d > 0 || h > 0) text += h + 'h ';
            text += m + 'm ' + s + 's';
            setStatEl('stat-uptime', text);
        }

        async function fetchUptime() {
            try {
                const res = await fetch(UPTIME_API, { cache: 'no-store' });
                if (res.ok) {
                    const data = await res.json();
                    uptimeStartedAt = data.started_at * 1000;
                    if (!uptimeInterval) {
                        updateDisplay();
                        uptimeInterval = setInterval(updateDisplay, 1000);
                    }
                }
            } catch (_) { /* silent */ }
        }

        fetchUptime();
        // Re-fetch uptime every 5 min in case server restarted
        setInterval(fetchUptime, 300000);
    }

})();
