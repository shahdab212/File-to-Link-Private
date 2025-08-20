/**
 * Advanced Media Player JavaScript
 * Handles all player functionality and interactions
 */

class AdvancedMediaPlayer {
    constructor() {
        this.mediaElement = null;
        this.isPlaying = false;
        this.currentTime = 0;
        this.duration = 0;
        this.volume = 1;
        this.playbackRate = 1;
        this.isFullscreen = false;
        this.playlist = [];
        this.currentTrack = 0;
        this.settings = {
            autoplay: false,
            loop: false,
            shuffle: false,
            quality: 'auto'
        };
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadSettings();
        this.detectMediaType();
        this.setupKeyboardShortcuts();
        this.setupProgressTracking();
    }
    
    setupEventListeners() {
        // Play/Pause button
        document.addEventListener('click', (e) => {
            if (e.target.matches('.play-pause-btn')) {
                this.togglePlayPause();
            }
            
            if (e.target.matches('.volume-btn')) {
                this.toggleMute();
            }
            
            if (e.target.matches('.fullscreen-btn')) {
                this.toggleFullscreen();
            }
            
            if (e.target.matches('.speed-btn')) {
                this.toggleSpeedMenu();
            }
            
            if (e.target.matches('.speed-option')) {
                this.setPlaybackRate(parseFloat(e.target.dataset.speed));
            }
            
            if (e.target.matches('.pip-btn')) {
                this.togglePictureInPicture();
            }
            
            if (e.target.matches('.download-btn')) {
                this.downloadFile();
            }
            
            if (e.target.matches('.share-btn')) {
                this.shareFile();
            }
            
            if (e.target.matches('.playlist-item')) {
                this.playTrack(parseInt(e.target.dataset.index));
            }
        });
        
        // Progress bar interaction
        document.addEventListener('click', (e) => {
            if (e.target.matches('.progress-container')) {
                this.seekTo(e);
            }
        });
        
        // Volume slider interaction
        document.addEventListener('click', (e) => {
            if (e.target.matches('.volume-slider')) {
                this.setVolume(e);
            }
        });
        
        // Media element events
        document.addEventListener('DOMContentLoaded', () => {
            this.mediaElement = document.querySelector('video, audio');
            if (this.mediaElement) {
                this.setupMediaEvents();
            }
        });
    }
    
    setupMediaEvents() {
        this.mediaElement.addEventListener('loadedmetadata', () => {
            this.duration = this.mediaElement.duration;
            this.updateTimeDisplay();
            this.updateProgress();
        });
        
        this.mediaElement.addEventListener('timeupdate', () => {
            this.currentTime = this.mediaElement.currentTime;
            this.updateProgress();
            this.updateTimeDisplay();
            this.saveProgress();
        });
        
        this.mediaElement.addEventListener('play', () => {
            this.isPlaying = true;
            this.updatePlayButton();
        });
        
        this.mediaElement.addEventListener('pause', () => {
            this.isPlaying = false;
            this.updatePlayButton();
        });
        
        this.mediaElement.addEventListener('ended', () => {
            this.onMediaEnded();
        });
        
        this.mediaElement.addEventListener('volumechange', () => {
            this.volume = this.mediaElement.volume;
            this.updateVolumeDisplay();
        });
        
        this.mediaElement.addEventListener('ratechange', () => {
            this.playbackRate = this.mediaElement.playbackRate;
            this.updateSpeedDisplay();
        });
        
        this.mediaElement.addEventListener('error', (e) => {
            this.handleMediaError(e);
        });
        
        // Load saved progress
        this.loadProgress();
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Prevent shortcuts when typing in input fields
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }
            
            switch (e.code) {
                case 'Space':
                    e.preventDefault();
                    this.togglePlayPause();
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    this.seekRelative(-10);
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    this.seekRelative(10);
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    this.adjustVolume(0.1);
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    this.adjustVolume(-0.1);
                    break;
                case 'KeyM':
                    e.preventDefault();
                    this.toggleMute();
                    break;
                case 'KeyF':
                    e.preventDefault();
                    this.toggleFullscreen();
                    break;
                case 'KeyP':
                    e.preventDefault();
                    this.togglePictureInPicture();
                    break;
                case 'Comma':
                    e.preventDefault();
                    this.adjustSpeed(-0.25);
                    break;
                case 'Period':
                    e.preventDefault();
                    this.adjustSpeed(0.25);
                    break;
            }
        });
    }
    
    setupProgressTracking() {
        // Save progress every 5 seconds
        setInterval(() => {
            if (this.isPlaying) {
                this.saveProgress();
            }
        }, 5000);
    }
    
    detectMediaType() {
        const fileId = this.getFileIdFromUrl();
        if (!fileId) return;
        
        fetch(`/stream/${fileId}`, { method: 'HEAD' })
            .then(response => {
                const contentType = response.headers.get('content-type');
                const contentLength = response.headers.get('content-length');
                
                this.updateFileInfo(contentType, contentLength);
                this.createMediaPlayer(contentType, fileId);
            })
            .catch(error => {
                console.error('Error detecting media type:', error);
                this.showError('Failed to load media information');
            });
    }
    
    createMediaPlayer(contentType, fileId) {
        const mediaContainer = document.getElementById('mediaContainer');
        const streamUrl = `/stream/${fileId}`;
        
        if (contentType && contentType.startsWith('video/')) {
            this.createVideoPlayer(mediaContainer, streamUrl);
        } else if (contentType && contentType.startsWith('audio/')) {
            this.createAudioPlayer(mediaContainer, streamUrl);
        } else {
            this.showUnsupportedMedia(mediaContainer);
        }
    }
    
    createVideoPlayer(container, streamUrl) {
        const videoHTML = `
            <div class="media-player">
                <video id="mainVideo" preload="metadata" poster="/static/images/video-placeholder.jpg">
                    <source src="${streamUrl}" type="video/mp4">
                    <p>Your browser doesn't support HTML5 video.</p>
                </video>
                <div class="custom-controls">
                    <div class="controls-row">
                        <button class="control-btn primary play-pause-btn" data-tooltip="Play/Pause (Space)">
                            <i class="fas fa-play"></i>
                        </button>
                        <button class="control-btn volume-btn" data-tooltip="Mute (M)">
                            <i class="fas fa-volume-up"></i>
                        </button>
                        <div class="volume-container">
                            <div class="volume-slider">
                                <div class="volume-progress" style="width: 100%"></div>
                            </div>
                        </div>
                        <div class="time-display">
                            <span class="current-time">0:00</span> / <span class="total-time">0:00</span>
                        </div>
                        <div class="progress-container">
                            <div class="progress-bar" style="width: 0%"></div>
                            <div class="progress-handle" style="left: 0%"></div>
                        </div>
                        <div class="speed-control">
                            <button class="control-btn speed-btn" data-tooltip="Playback Speed">
                                <span class="speed-text">1x</span>
                            </button>
                            <div class="speed-menu">
                                <div class="speed-option" data-speed="0.25">0.25x</div>
                                <div class="speed-option" data-speed="0.5">0.5x</div>
                                <div class="speed-option" data-speed="0.75">0.75x</div>
                                <div class="speed-option active" data-speed="1">1x</div>
                                <div class="speed-option" data-speed="1.25">1.25x</div>
                                <div class="speed-option" data-speed="1.5">1.5x</div>
                                <div class="speed-option" data-speed="2">2x</div>
                            </div>
                        </div>
                        <button class="control-btn pip-btn" data-tooltip="Picture in Picture (P)">
                            <i class="fas fa-external-link-alt"></i>
                        </button>
                        <button class="control-btn fullscreen-btn" data-tooltip="Fullscreen (F)">
                            <i class="fas fa-expand"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = videoHTML;
        this.mediaElement = document.getElementById('mainVideo');
        this.setupMediaEvents();
    }
    
    createAudioPlayer(container, streamUrl) {
        const audioHTML = `
            <div class="media-player">
                <div class="audio-visualizer">
                    <div class="audio-info">
                        <div class="album-art">
                            <i class="fas fa-music"></i>
                        </div>
                        <div class="track-info">
                            <h3 class="track-title">Audio File</h3>
                            <p class="track-artist">Unknown Artist</p>
                        </div>
                    </div>
                </div>
                <audio id="mainAudio" preload="metadata">
                    <source src="${streamUrl}" type="audio/mpeg">
                    <p>Your browser doesn't support HTML5 audio.</p>
                </audio>
                <div class="custom-controls">
                    <div class="controls-row">
                        <button class="control-btn play-pause-btn" data-tooltip="Play/Pause (Space)">
                            <i class="fas fa-play"></i>
                        </button>
                        <button class="control-btn volume-btn" data-tooltip="Mute (M)">
                            <i class="fas fa-volume-up"></i>
                        </button>
                        <div class="volume-container">
                            <div class="volume-slider">
                                <div class="volume-progress" style="width: 100%"></div>
                            </div>
                        </div>
                        <div class="time-display">
                            <span class="current-time">0:00</span> / <span class="total-time">0:00</span>
                        </div>
                        <div class="progress-container">
                            <div class="progress-bar" style="width: 0%"></div>
                            <div class="progress-handle" style="left: 0%"></div>
                        </div>
                        <div class="speed-control">
                            <button class="control-btn speed-btn" data-tooltip="Playback Speed">
                                <span class="speed-text">1x</span>
                            </button>
                            <div class="speed-menu">
                                <div class="speed-option" data-speed="0.5">0.5x</div>
                                <div class="speed-option" data-speed="0.75">0.75x</div>
                                <div class="speed-option active" data-speed="1">1x</div>
                                <div class="speed-option" data-speed="1.25">1.25x</div>
                                <div class="speed-option" data-speed="1.5">1.5x</div>
                                <div class="speed-option" data-speed="2">2x</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = audioHTML;
        this.mediaElement = document.getElementById('mainAudio');
        this.setupMediaEvents();
    }
    
    showUnsupportedMedia(container) {
        const fileId = this.getFileIdFromUrl();
        const downloadUrl = `/download/${fileId}`;
        
        container.innerHTML = `
            <div class="error-container">
                <i class="fas fa-file-alt"></i>
                <h3>Preview Not Available</h3>
                <p>This file type cannot be played in the browser.</p>
                <p>You can download the file to view it locally.</p>
                <a href="${downloadUrl}" class="btn btn-primary">
                    <i class="fas fa-download"></i> Download File
                </a>
            </div>
        `;
    }
    
    showError(message) {
        const container = document.getElementById('mediaContainer');
        container.innerHTML = `
            <div class="error-container">
                <i class="fas fa-exclamation-triangle"></i>
                <h3>Error</h3>
                <p>${message}</p>
                <button class="btn btn-primary" onclick="location.reload()">
                    <i class="fas fa-refresh"></i> Retry
                </button>
            </div>
        `;
    }
    
    // Media Control Methods
    togglePlayPause() {
        if (!this.mediaElement) return;
        
        if (this.isPlaying) {
            this.mediaElement.pause();
        } else {
            this.mediaElement.play().catch(e => {
                console.error('Error playing media:', e);
                this.showError('Failed to play media. Please try again.');
            });
        }
    }
    
    toggleMute() {
        if (!this.mediaElement) return;
        
        this.mediaElement.muted = !this.mediaElement.muted;
        this.updateVolumeButton();
    }
    
    toggleFullscreen() {
        if (!this.mediaElement) return;
        
        if (!this.isFullscreen) {
            if (this.mediaElement.requestFullscreen) {
                this.mediaElement.requestFullscreen();
            } else if (this.mediaElement.webkitRequestFullscreen) {
                this.mediaElement.webkitRequestFullscreen();
            } else if (this.mediaElement.msRequestFullscreen) {
                this.mediaElement.msRequestFullscreen();
            }
        } else {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            } else if (document.webkitExitFullscreen) {
                document.webkitExitFullscreen();
            } else if (document.msExitFullscreen) {
                document.msExitFullscreen();
            }
        }
    }
    
    togglePictureInPicture() {
        if (!this.mediaElement || this.mediaElement.tagName !== 'VIDEO') return;
        
        if (document.pictureInPictureElement) {
            document.exitPictureInPicture();
        } else {
            this.mediaElement.requestPictureInPicture().catch(e => {
                console.error('Error entering PiP:', e);
            });
        }
    }
    
    toggleSpeedMenu() {
        const speedMenu = document.querySelector('.speed-menu');
        if (speedMenu) {
            speedMenu.classList.toggle('show');
        }
    }
    
    setPlaybackRate(rate) {
        if (!this.mediaElement) return;
        
        this.mediaElement.playbackRate = rate;
        this.playbackRate = rate;
        this.updateSpeedDisplay();
        
        // Close speed menu
        const speedMenu = document.querySelector('.speed-menu');
        if (speedMenu) {
            speedMenu.classList.remove('show');
        }
        
        // Update active speed option
        document.querySelectorAll('.speed-option').forEach(option => {
            option.classList.remove('active');
            if (parseFloat(option.dataset.speed) === rate) {
                option.classList.add('active');
            }
        });
    }
    
    seekTo(event) {
        if (!this.mediaElement || !this.duration) return;
        
        const progressContainer = event.currentTarget;
        const rect = progressContainer.getBoundingClientRect();
        const percent = (event.clientX - rect.left) / rect.width;
        const newTime = percent * this.duration;
        
        this.mediaElement.currentTime = newTime;
    }
    
    seekRelative(seconds) {
        if (!this.mediaElement) return;
        
        const newTime = Math.max(0, Math.min(this.duration, this.currentTime + seconds));
        this.mediaElement.currentTime = newTime;
    }
    
    setVolume(event) {
        if (!this.mediaElement) return;
        
        const volumeSlider = event.currentTarget;
        const rect = volumeSlider.getBoundingClientRect();
        const percent = (event.clientX - rect.left) / rect.width;
        const newVolume = Math.max(0, Math.min(1, percent));
        
        this.mediaElement.volume = newVolume;
        this.mediaElement.muted = false;
    }
    
    adjustVolume(delta) {
        if (!this.mediaElement) return;
        
        const newVolume = Math.max(0, Math.min(1, this.volume + delta));
        this.mediaElement.volume = newVolume;
        this.mediaElement.muted = false;
    }
    
    adjustSpeed(delta) {
        const newRate = Math.max(0.25, Math.min(4, this.playbackRate + delta));
        this.setPlaybackRate(newRate);
    }
    
    // UI Update Methods
    updatePlayButton() {
        const playBtn = document.querySelector('.play-pause-btn i');
        if (playBtn) {
            playBtn.className = this.isPlaying ? 'fas fa-pause' : 'fas fa-play';
        }
    }
    
    updateProgress() {
        if (!this.duration) return;
        
        const percent = (this.currentTime / this.duration) * 100;
        const progressBar = document.querySelector('.progress-bar');
        const progressHandle = document.querySelector('.progress-handle');
        
        if (progressBar) {
            progressBar.style.width = `${percent}%`;
        }
        
        if (progressHandle) {
            progressHandle.style.left = `${percent}%`;
        }
    }
    
    updateTimeDisplay() {
        const currentTimeEl = document.querySelector('.current-time');
        const totalTimeEl = document.querySelector('.total-time');
        
        if (currentTimeEl) {
            currentTimeEl.textContent = this.formatTime(this.currentTime);
        }
        
        if (totalTimeEl) {
            totalTimeEl.textContent = this.formatTime(this.duration);
        }
    }
    
    updateVolumeDisplay() {
        const volumeProgress = document.querySelector('.volume-progress');
        if (volumeProgress) {
            volumeProgress.style.width = `${this.volume * 100}%`;
        }
        
        this.updateVolumeButton();
    }
    
    updateVolumeButton() {
        const volumeBtn = document.querySelector('.volume-btn i');
        if (volumeBtn) {
            if (this.mediaElement.muted || this.volume === 0) {
                volumeBtn.className = 'fas fa-volume-mute';
            } else if (this.volume < 0.5) {
                volumeBtn.className = 'fas fa-volume-down';
            } else {
                volumeBtn.className = 'fas fa-volume-up';
            }
        }
    }
    
    updateSpeedDisplay() {
        const speedText = document.querySelector('.speed-text');
        if (speedText) {
            speedText.textContent = `${this.playbackRate}x`;
        }
    }
    
    updateFileInfo(contentType, contentLength) {
        const fileIcon = document.querySelector('.file-icon');
        const fileSizeEl = document.querySelector('.file-size');
        
        if (fileIcon) {
            if (contentType && contentType.startsWith('video/')) {
                fileIcon.innerHTML = '<i class="fas fa-video"></i>';
            } else if (contentType && contentType.startsWith('audio/')) {
                fileIcon.innerHTML = '<i class="fas fa-music"></i>';
            } else {
                fileIcon.innerHTML = '<i class="fas fa-file"></i>';
            }
        }
        
        if (fileSizeEl && contentLength) {
            const sizeMB = (parseInt(contentLength) / (1024 * 1024)).toFixed(2);
            fileSizeEl.textContent = `${sizeMB} MB`;
        }
    }
    
    // Utility Methods
    formatTime(seconds) {
        if (!seconds || isNaN(seconds)) return '0:00';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    }
    
    getFileIdFromUrl() {
        const pathParts = window.location.pathname.split('/');
        return pathParts[2] || null; // Assuming URL format: /play/{file_id}
    }
    
    // Progress Saving/Loading
    saveProgress() {
        if (!this.mediaElement || !this.duration) return;
        
        const fileId = this.getFileIdFromUrl();
        if (!fileId) return;
        
        const progress = {
            currentTime: this.currentTime,
            volume: this.volume,
            playbackRate: this.playbackRate,
            timestamp: Date.now()
        };
        
        localStorage.setItem(`player_progress_${fileId}`, JSON.stringify(progress));
    }
    
    loadProgress() {
        const fileId = this.getFileIdFromUrl();
        if (!fileId) return;
        
        const savedProgress = localStorage.getItem(`player_progress_${fileId}`);
        if (!savedProgress) return;
        
        try {
            const progress = JSON.parse(savedProgress);
            
            // Only restore if saved within last 24 hours
            if (Date.now() - progress.timestamp < 24 * 60 * 60 * 1000) {
                if (this.mediaElement && progress.currentTime > 10) {
                    this.mediaElement.currentTime = progress.currentTime;
                }
                
                if (progress.volume !== undefined) {
                    this.mediaElement.volume = progress.volume;
                }
                
                if (progress.playbackRate !== undefined) {
                    this.mediaElement.playbackRate = progress.playbackRate;
                }
            }
        } catch (e) {
            console.error('Error loading progress:', e);
        }
    }
    
    loadSettings() {
        const savedSettings = localStorage.getItem('player_settings');
        if (savedSettings) {
            try {
                this.settings = { ...this.settings, ...JSON.parse(savedSettings) };
            } catch (e) {
                console.error('Error loading settings:', e);
            }
        }
    }
    
    saveSettings() {
        localStorage.setItem('player_settings', JSON.stringify(this.settings));
    }
    
    // Event Handlers
    onMediaEnded() {
        if (this.settings.loop) {
            this.mediaElement.currentTime = 0;
            this.mediaElement.play();
        } else if (this.playlist.length > 1) {
            this.playNext();
        }
    }
    
    handleMediaError(error) {
        console.error('Media error:', error);
        let message = 'An error occurred while playing the media.';
        
        if (error.target && error.target.error) {
            switch (error.target.error.code) {
                case 1:
                    message = 'Media loading was aborted.';
                    break;
                case 2:
                    message = 'Network error occurred while loading media.';
                    break;
                case 3:
                    message = 'Media decoding failed.';
                    break;
                case 4:
                    message = 'Media format is not supported.';
                    break;
            }
        }
        
        this.showError(message);
    }
    
    // File Actions
    downloadFile() {
        const fileId = this.getFileIdFromUrl();
        if (fileId) {
            const downloadUrl = `/download/${fileId}`;
            window.open(downloadUrl, '_blank');
        }
    }
    
    shareFile() {
        const fileId = this.getFileIdFromUrl();
        if (fileId) {
            const shareUrl = window.location.href;
            
            if (navigator.share) {
                navigator.share({
                    title: 'Shared Media File',
                    url: shareUrl
                }).catch(e => console.error('Error sharing:', e));
            } else {
                // Fallback: copy to clipboard
                navigator.clipboard.writeText(shareUrl).then(() => {
                    this.showNotification('Link copied to clipboard!');
                }).catch(e => {
                    console.error('Error copying to clipboard:', e);
                });
            }
        }
    }
    
    showNotification(message) {
        // Create and show a temporary notification
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--success-color);
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }
}

// Initialize player when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mediaPlayer = new AdvancedMediaPlayer();
});

// Add notification animation styles
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
`;
document.head.appendChild(style);
