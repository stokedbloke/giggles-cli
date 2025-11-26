/**
 * Laughter Detector Frontend JavaScript
 * 
 * This module handles the frontend functionality including authentication,
 * API communication, and UI interactions for the laughter detection system.
 */

class LaughterDetectorApp {
    /**
     * Initialize the application - sets up base URL, auth token from localStorage,
     * and initializes user state. Called automatically when app loads.
     */
    constructor() {
        this.apiBase = '/api'; // Base URL for all API endpoints
        this.authToken = localStorage.getItem('auth_token'); // JWT token stored in browser
        this.currentUser = null; // Current logged-in user object (email, id, timezone)
        this.currentDate = null; // Currently selected date for day detail view
        this.userTimezone = null; // User's timezone (IANA format, e.g., "America/Los_Angeles")
        
        this.init(); // Start app initialization
    }
    
    /**
     * Detect user's timezone using browser API.
     * @returns {string} IANA timezone string (e.g., "America/Los_Angeles")
     */
    detectTimezone() {
        try {
            return Intl.DateTimeFormat().resolvedOptions().timeZone;
        } catch (error) {
            console.warn('Failed to detect timezone, defaulting to UTC:', error);
            return 'UTC';
        }
    }
    
    /**
     * Initialize the app - sets up all event listeners and checks if user is already logged in.
     * Called once when app first loads.
     */
    init() {
        this.setupEventListeners(); // Attach click handlers to all buttons/forms
        this.checkAuthStatus(); // Check if user has valid token, show login or main app
    }
    
    /**
     * Attach event listeners to all interactive elements (buttons, forms, inputs).
     * Called once during app initialization. Uses event delegation for dynamically created elements.
     */
    setupEventListeners() {
        // Authentication form events - login and registration
        document.getElementById('login-form-element').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });
        
        document.getElementById('register-form-element').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleRegister();
        });
        
        // Auth form switching
        document.getElementById('show-register').addEventListener('click', (e) => {
            e.preventDefault();
            this.showRegisterForm();
        });
        
        document.getElementById('show-login').addEventListener('click', (e) => {
            e.preventDefault();
            this.showLoginForm();
        });
        
        // Limitless key form
        document.getElementById('limitless-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLimitlessKey();
        });
        
        // Management buttons
        document.getElementById('delete-all-data').addEventListener('click', () => {
            this.handleDeleteAllData();
        });
        
        document.getElementById('delete-limitless-key').addEventListener('click', () => {
            this.handleDeleteLimitlessKey();
        });
        
        document.getElementById('update-today-data').addEventListener('click', () => {
            this.handleUpdateTodayData();
        });
        
        // Use event delegation for reprocess button since it might be in hidden screen
        const settingsScreen = document.getElementById('settings-screen');
        if (settingsScreen) {
            console.log('✅ Settings screen found, using event delegation for reprocess button');
            settingsScreen.addEventListener('click', (e) => {
                if (e.target && e.target.id === 'reprocess-date-range') {
                    console.log('🔵 DELEGATED CLICK - Reprocess button clicked via delegation');
                    e.preventDefault();
                    e.stopPropagation();
                    this.handleReprocessDateRange();
                }
            });
        } else {
            console.error('🔴 Settings screen not found during setup!');
        }
        
        // Also try direct listener as backup
        const reprocessBtn = document.getElementById('reprocess-date-range');
        if (reprocessBtn) {
            console.log('✅ Reprocess button found, attaching direct listener');
            reprocessBtn.addEventListener('click', (e) => {
                console.log('🔵 DIRECT CLICK - Reprocess button clicked');
                e.preventDefault();
                e.stopPropagation();
                this.handleReprocessDateRange();
            });
        }
        
        // Day detail navigation
        document.getElementById('back-to-summary').addEventListener('click', () => {
            this.showSummaryView();
        });
        
        // Probability filter
        document.getElementById('probability-filter').addEventListener('input', (e) => {
            this.updateProbabilityFilter(e.target.value);
        });
        
        // Mobile navigation elements (stubbed - do nothing for now)
        document.getElementById('add-btn').addEventListener('click', () => {
            // Stubbed - do nothing for now
        });

        document.getElementById('smiley-btn').addEventListener('click', () => {
            this.showSummaryView();
        });
        
        document.getElementById('nav-program').addEventListener('click', () => {
            // Stubbed - do nothing for now
        });
        
        document.getElementById('nav-settings').addEventListener('click', () => {
            this.showSettingsScreen();
        });

        document.getElementById('nav-home').addEventListener('click', () => {
            this.showSummaryView();
        });
        
        // Logout button
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.handleLogout();
        });
    }
    
    /**
     * Check if user has a valid authentication token on app load.
     * If token exists, validates it with backend and loads user data.
     * If invalid/missing, shows login screen.
     */
    async checkAuthStatus() {
        if (this.authToken) {
            try {
                // Validate token by fetching current user info from backend
                const response = await this.makeRequest('/auth/me', 'GET');
                // SECURITY: Don't log full user object (contains email, user_id, etc.)
                // Only log non-sensitive info for debugging
                console.log('✅ Auth check successful');
                
                // Store user data and timezone
                this.currentUser = response.user;
                this.userTimezone = response.user?.timezone || 'UTC';
                
                console.log('✅ User timezone set to:', this.userTimezone);
                
                // Migration: If user has UTC timezone, attempt to update with detected timezone
                if (this.userTimezone === 'UTC' && this.currentUser) {
                    await this.updateTimezoneOnLogin();
                }
                
                // Check if user has Limitless API key configured
                await this.checkUserStatus();
            } catch (error) {
                // Token invalid or expired - clear auth and show login
                console.error('❌ Auth check failed:', error);
                this.clearAuth();
                this.showAuthSection();
            }
        } else {
            // No token - show login screen
            this.showAuthSection();
        }
    }
    
    /**
     * Update user's timezone if it's set to UTC (migration for existing users).
     */
    async updateTimezoneOnLogin() {
        const detectedTimezone = this.detectTimezone();
        
        try {
            // Note: This endpoint will be created in Phase 2
            // For now, just log for debugging
            console.log(`Detected timezone: ${detectedTimezone}, current: ${this.userTimezone}`);
            
            // TODO: Implement API call to update timezone
            // await this.makeRequest('/settings/timezone', 'PUT', { timezone: detectedTimezone });
            // this.userTimezone = detectedTimezone;
            // console.log(`Updated timezone to ${detectedTimezone}`);
        } catch (error) {
            console.warn('Failed to update timezone:', error);
        }
    }
    
    /**
     * Check if user has Limitless API key configured.
     * Shows daily summary if key exists, or setup screen if missing.
     * Called after successful authentication.
     */
    async checkUserStatus() {
        try {
            const response = await this.makeRequest('/limitless-key/status', 'GET');
            if (response.has_key) {
                // User has API key - show main app with daily summary
                this.showAppSection();
                this.showDailySummary();
            } else {
                // User needs to configure Limitless API key
                this.showAppSection();
                this.showLimitlessSetup();
            }
        } catch (error) {
            // If status check fails, assume no API key and show setup screen
            this.showAppSection();
            this.showLimitlessSetup();
        }
    }
    
    /**
     * Handle user login - validates credentials and stores auth token.
     * Called when login form is submitted.
     */
    async handleLogin() {
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        
        try {
            this.showLoading('Signing in...');
            // Authenticate with backend and get JWT token
            const response = await this.makeRequest('/auth/login', 'POST', {
                email, password
            });
            
            // Store token and user data
            this.authToken = response.access_token;
            this.currentUser = response.user;
            localStorage.setItem('auth_token', this.authToken); // Persist token across page reloads
            
            this.hideLoading();
            this.showToast('Successfully signed in!', 'success');
            // Check if user has Limitless API key configured
            await this.checkUserStatus();
            
        } catch (error) {
            this.hideLoading();
            const errorMessage = error.detail || error.message || 'Login failed';
            this.showToast('Login failed: ' + errorMessage, 'error');
        }
    }
    
    /**
     * Handle new user registration - creates account with email/password/timezone.
     * Automatically detects user's timezone from browser. Called when register form is submitted.
     */
    async handleRegister() {
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        const timezone = this.detectTimezone(); // Detect user's timezone from browser
        
        try {
            this.showLoading('Creating account...');
            // Create new user account with timezone
            const response = await this.makeRequest('/auth/register', 'POST', {
                email, 
                password,
                timezone  // Send timezone to backend for proper date handling
            });
            
            this.hideLoading();
            this.showToast('Account created successfully! Please sign in.', 'success');
            this.showLoginForm(); // Switch to login form after successful registration
            
        } catch (error) {
            this.hideLoading();
            this.showToast('Registration failed: ' + error.message, 'error');
        }
    }
    
    /**
     * Handle Limitless API key submission - validates and stores the key.
     * Called when Limitless setup form is submitted. After success, shows daily summary.
     */
    async handleLimitlessKey() {
        const apiKey = document.getElementById('limitless-key').value;
        
        try {
            this.showLoading('Validating and storing API key...');
            // Backend validates key with Limitless API before storing
            const response = await this.makeRequest('/limitless-key', 'POST', {
                api_key: apiKey
            });
            
            this.hideLoading();
            this.showToast('API key stored successfully!', 'success');
            this.showDailySummary(); // Navigate to main app view
            
        } catch (error) {
            this.hideLoading();
            this.showToast('Failed to store API key: ' + error.message, 'error');
        }
    }
    
    /**
     * Handle deletion of all user data (laughter detections, audio segments, etc.).
     * Requires confirmation before proceeding. Redirects to home page after success.
     * Called when "Delete All Data" button is clicked in settings.
     */
    async handleDeleteAllData() {
        console.log('DELETE ALL DATA CLICKED - FUNCTION CALLED');
        if (!confirm('Are you sure you want to delete all your data? This action cannot be undone.')) {
            return;
        }
        
        try {
            this.showLoading('Deleting all data...');
            await this.makeRequest('/user-data', 'DELETE');
            
            this.hideLoading();
            this.showToast('All data deleted successfully', 'success');
            
            // Redirect to home page to reset all state (clears all UI state)
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
            
        } catch (error) {
            this.hideLoading();
            this.showToast('Failed to delete data: ' + error.message, 'error');
        }
    }
    
    /**
     * Handle deletion of Limitless API key and all associated data.
     * Requires confirmation. Deletes both the API key and all user data.
     * Redirects to home page after success to reset state.
     */
    async handleDeleteLimitlessKey() {
        if (!confirm('Are you sure you want to delete your Limitless API key? This will also delete all your data.')) {
            return;
        }
        
        try {
            this.showLoading('Deleting API key and data...');
            await this.makeRequest('/limitless-key', 'DELETE');
            await this.makeRequest('/user-data', 'DELETE');
            
            this.hideLoading();
            this.showToast('API key and data deleted successfully', 'success');
            
            // Redirect to home page to reset all state (clears all UI state)
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
            
        } catch (error) {
            this.hideLoading();
            this.showToast('Failed to delete API key: ' + error.message, 'error');
        }
    }
    
    /**
     * Trigger processing of today's audio data - downloads from Limitless and detects laughter.
     * Called when "Update Today's Count" button is clicked. Shows appropriate status messages.
     */
    async handleUpdateTodayData() {
        try {
            this.showLoading('Updating today\'s laughter data...');
            // Trigger backend processing (downloads OGG files, runs YAMNet, extracts clips)
            const response = await this.makeRequest('/trigger-nightly-processing', 'POST');
            
            this.hideLoading();
            
            // Handle different response statuses from processing
            if (response.status === 'timeout') {
                this.showToast('Processing timed out - Limitless API may be slow. Try again later.', 'warning');
            } else if (response.status === 'completed') {
                this.showToast('Processing completed successfully!', 'success');
            } else if (response.message && response.message.includes('triggered successfully')) {
                this.showToast('Processing triggered successfully!', 'success');
            } else {
                this.showToast('Processing completed!', 'success');
            }
            
            // Refresh the daily summary to show newly detected laughter
            await this.showDailySummary();
            
        } catch (error) {
            this.hideLoading();
            this.showToast('Failed to update today\'s data: ' + error.message, 'error');
        }
    }
    
    /**
     * Handle reprocessing of a date range - deletes existing data and re-downloads/re-processes.
     * Validates date inputs, shows confirmation, disables form during processing to prevent double-clicks.
     * After completion, navigates back to summary view and refreshes data.
     * Called when "Reprocess Date Range" button is clicked in settings.
     */
    async handleReprocessDateRange() {
        console.log('🔵 ============================================');
        console.log('🔵 handleReprocessDateRange CALLED');
        console.log('🔵 ============================================');
        
        try {
            const startDate = document.getElementById('reprocess-start-date').value;
            const endDate = document.getElementById('reprocess-end-date').value;
            const reprocessBtn = document.getElementById('reprocess-date-range');
            const startDateInput = document.getElementById('reprocess-start-date');
            const endDateInput = document.getElementById('reprocess-end-date');
            const statusDiv = document.getElementById('reprocess-status');
            
            console.log('🔵 Dates:', { startDate, endDate });
            console.log('🔵 Elements found:', { 
                reprocessBtn: !!reprocessBtn, 
                startDateInput: !!startDateInput, 
                endDateInput: !!endDateInput, 
                statusDiv: !!statusDiv 
            });
            
            if (!reprocessBtn || !startDateInput || !endDateInput || !statusDiv) {
                console.error('🔴 Missing required elements!', { reprocessBtn, startDateInput, endDateInput, statusDiv });
                this.showToast('Error: Could not find form elements', 'error');
                return;
            }
            
            if (!startDate || !endDate) {
                console.log('🔴 Missing dates');
                this.showToast('Please select both start and end dates', 'error');
                return;
            }
            
            if (startDate > endDate) {
                console.log('🔴 Invalid date range');
                this.showToast('Start date must be before end date', 'error');
                return;
            }
            
            const confirmed = confirm(`Are you sure you want to reprocess data from ${startDate} to ${endDate}? This will delete existing data for these dates and redownload from Limitless API. This may take several minutes.`);
            if (!confirmed) {
                console.log('🔴 User cancelled');
                return;
            }
        
            // Disable button and inputs to prevent double-clicking during processing
            reprocessBtn.disabled = true;
            reprocessBtn.textContent = 'Processing...';
            startDateInput.disabled = true;
            endDateInput.disabled = true;
            
            // Show status message
            statusDiv.classList.remove('hidden');
            statusDiv.innerHTML = '<p class="status-message">🔄 Reprocessing in progress... This may take several minutes. Please wait.</p>';
            
            console.log('🔵 Making API request...');
            this.showLoading('Reprocessing date range...');
            // Backend deletes existing data and re-downloads/re-processes the date range
            const response = await this.makeRequest('/reprocess-date-range', 'POST', {
                start_date: startDate,
                end_date: endDate
            });
            
            console.log('🔵 API response:', response);
            this.hideLoading();
            this.showToast('Reprocessing completed successfully!', 'success');
            
            // Clear the form
            startDateInput.value = '';
            endDateInput.value = '';
            
            // Immediately return to summary view and refresh data
            // (Don't show success message in settings - it causes split screen)
            this.showSummaryView();
            await this.loadDailySummary();
            
        } catch (error) {
            console.error('🔴 Reprocess error:', error);
            this.hideLoading();
            const statusDiv = document.getElementById('reprocess-status');
            if (statusDiv) {
                statusDiv.innerHTML = `<p class="status-error">❌ Error: ${error.message}</p>`;
            }
            this.showToast('Failed to reprocess date range: ' + error.message, 'error');
            
            // Re-enable button and inputs on error (allows user to retry)
            const reprocessBtn = document.getElementById('reprocess-date-range');
            const startDateInput = document.getElementById('reprocess-start-date');
            const endDateInput = document.getElementById('reprocess-end-date');
            if (reprocessBtn) {
                reprocessBtn.disabled = false;
                reprocessBtn.textContent = 'Reprocess Date Range';
            }
            if (startDateInput) startDateInput.disabled = false;
            if (endDateInput) endDateInput.disabled = false;
        }
    }
    

    /**
     * Fetch daily laughter summary from backend and display it.
     * Returns list of days with laughter counts, grouped by date in user's timezone.
     */
    async loadDailySummary() {
        try {
            const response = await this.makeRequest('/daily-summary', 'GET');
            this.displayDailySummary(response); // Render the summary cards
        } catch (error) {
            this.showToast('Failed to load daily summary: ' + error.message, 'error');
        }
    }
    
    /**
     * Display daily summary cards - renders cards for each day with laughter events.
     * Filters out days with zero laughter and shows appropriate empty state messages.
     * @param {Array} summary - Array of day objects with date, total_laughter_events, etc.
     */
    displayDailySummary(summary) {
        const container = document.getElementById('summary-cards');
        container.innerHTML = '';
        
        if (summary.length === 0) {
            container.innerHTML = '<p class="no-data">No laughter data available yet. Audio processing may still be in progress.</p>';
            return;
        }
        
        // Only show cards for days with laughter events (filter out zero-count days)
        const daysWithLaughter = summary.filter(day => day.total_laughter_events > 0);
        
        if (daysWithLaughter.length === 0) {
            container.innerHTML = '<p class="no-data">No laughter detected yet. Audio processing is working - laughter will appear here when detected.</p>';
            return;
        }
        
        // Create and append a card for each day with laughter
        daysWithLaughter.forEach((day, index) => {
            const card = this.createDayCard(day, index);
            container.appendChild(card);
        });
    }
    
    /**
     * Create a single day card element showing day name, date, and laughter count.
     * Cards are clickable and cycle through 6 colors for visual variety.
     * @param {Object} day - Day object with date and total_laughter_events
     * @param {number} index - Index for color cycling (0-5)
     * @returns {HTMLElement} The created card element
     */
    createDayCard(day, index = 0) {
        const card = document.createElement('div');
        card.className = 'day-card clickable';
        
        // Color cycling: cycle through 6 colors for visual variety
        const colorIndex = index % 6;
        card.classList.add(`color-${colorIndex}`);
        
        // Parse date string correctly to avoid timezone issues
        // Adding noon (12:00) prevents date shifting due to UTC conversion
        const date = new Date(day.date + 'T12:00:00');
        const dayName = date.toLocaleDateString('en-US', { weekday: 'long' });
        const monthDay = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        
        card.innerHTML = `
            <div class="card-content">
                <div class="card-info">
                    <div class="card-day card-text">${dayName}</div>
                    <div class="card-date card-text">${monthDay}</div>
                    <div class="card-count card-text">${day.total_laughter_events}</div>
                    <div class="card-label card-text">giggles</div>
                </div>
                <div class="card-play card-text">▶</div>
            </div>
        `;
        
        // Add click handler to the count number specifically (for better UX)
        const countElement = card.querySelector('.card-count');
        countElement.onclick = (e) => {
            e.stopPropagation();
            this.showDayDetail(day.date);
        };
        
        // Also allow clicking anywhere on the card to view details
        card.onclick = () => this.showDayDetail(day.date);
        
        return card;
    }
    
    /**
     * Load and display all laughter detections for a specific date.
     * Shows individual laughter events with audio players, timestamps, and notes.
     * @param {string} date - Date string in YYYY-MM-DD format
     */
    async showDayDetail(date) {
        this.currentDate = date; // Store current date for navigation/deletion
        this.showDayDetailView(); // Show the day detail screen
        
        try {
            this.showLoading('Loading day details...');
            // Fetch all laughter detections for this date (in user's timezone)
            const response = await this.makeRequest(`/laughter-detections/${date}`, 'GET');
            this.displayDayDetail(response); // Render the detections table
            this.hideLoading();
        } catch (error) {
            this.hideLoading();
            this.showToast('Failed to load day details: ' + error.message, 'error');
        }
    }
    
    /**
     * Display laughter detections in a table - uses progressive rendering to avoid blank screen.
     * Creates placeholder rows immediately, then loads audio asynchronously to maintain order.
     * This prevents race conditions where faster-loading audio appears before slower-loading audio.
     * @param {Array} detections - Array of detection objects with timestamp, probability, clip_path, etc.
     */
    async displayDayDetail(detections) {
        console.log('🔵 displayDayDetail called with', detections.length, 'detections');
        const tbody = document.getElementById('detections-tbody');
        if (!tbody) {
            console.error('🔴 detections-tbody not found!');
            return;
        }
        tbody.innerHTML = '';
        
        if (!detections || detections.length === 0) {
            console.log('🔵 No detections, showing empty message');
            tbody.innerHTML = '<tr><td colspan="5" class="no-data">No laughter detections for this day.</td></tr>';
            return;
        }
        
        // PROGRESSIVE RENDERING FIX: Create all rows immediately (with loading placeholders),
        // then update them as audio loads. This maintains chronological order (no race condition)
        // while showing content immediately (no blank screen for 10-15 seconds).
        console.log('🔵 Processing', detections.length, 'detections');
        
        // Create all rows immediately with placeholder content to show something right away
        const rows = detections.map((detection, index) => {
            const row = document.createElement('tr');
            const timezone = this.userTimezone || this.detectTimezone();
            const time = this.formatTimestampToTimezone(detection.timestamp, timezone);
            row.innerHTML = `
                <td>
                    <div class="audio-clip">
                        <span class="loading-audio">Loading...</span>
                        <span>${time}</span>
                    </div>
                </td>
                <td><span class="laughter-class">${detection.class_name || 'Unknown'}</span></td>
                <td><span class="probability">${(detection.probability * 100).toFixed(1)}%</span></td>
                <td><input type="text" class="notes-input" value="${detection.notes || ''}" placeholder="Add notes..." onchange="app.updateDetectionNotes('${detection.id}', this.value)"></td>
                <td><button class="btn btn-danger" onclick="app.deleteDetection('${detection.id}')">Delete</button></td>
            `;
            row.dataset.detectionIndex = index;
            tbody.appendChild(row);
            
            // Load audio asynchronously and update the row when ready
            // This ensures rows appear in correct order even if audio loads at different speeds
            this.createDetectionRow(detection)
                .then(audioRow => {
                    // Replace placeholder row with actual audio row (maintains order)
                    const placeholderRow = tbody.querySelector(`tr[data-detection-index="${index}"]`);
                    if (placeholderRow && audioRow) {
                        placeholderRow.replaceWith(audioRow);
                    }
                })
                .catch(error => {
                    console.error('Error creating detection row:', error, detection);
                    // Update placeholder to show error/unavailable message
                    const placeholderRow = tbody.querySelector(`tr[data-detection-index="${index}"]`);
                    if (placeholderRow) {
                        const audioCell = placeholderRow.querySelector('.audio-clip');
                        if (audioCell) {
                            audioCell.innerHTML = `
                                <span class="no-audio">Audio unavailable</span>
                                <span>${time}</span>
                            `;
                        }
                    }
                });
            
            return row;
        });
        
        console.log('🔵 displayDayDetail completed, rows in tbody:', tbody.children.length);
    }
    
    /**
     * Format timestamp to user's local timezone.
     * @param {string} timestamp - ISO timestamp string
     * @param {string} timezone - User's IANA timezone
     * @returns {string} Formatted time string
     */
    formatTimestampToTimezone(timestamp, timezone) {
        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                timeZone: timezone  // Use user's timezone
            });
        } catch (error) {
            console.error('Error formatting timestamp:', error);
            return new Date(timestamp).toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            });
        }
    }
    
    /**
     * Create a table row for a single laughter detection with audio player, timestamp, and controls.
     * Fetches audio file and creates blob URL for playback. Handles missing audio files gracefully.
     * @param {Object} detection - Detection object with id, timestamp, probability, class_name, notes
     * @returns {HTMLElement} Table row element with all detection data
     */
    async createDetectionRow(detection) {
        const row = document.createElement('tr');
        
        // Format time in user's timezone (not UTC)
        const timezone = this.userTimezone || this.detectTimezone();
        const time = this.formatTimestampToTimezone(detection.timestamp, timezone);
        
        // Create abort controller for this row's audio fetch (allows cancellation if row is removed)
        const abortController = new AbortController();
        row._abortController = abortController; // Store for cleanup
        
        // Show loading state initially
        row.innerHTML = `
            <td>
                <div class="audio-clip">
                    <span class="loading-audio">Loading...</span>
                    <span>${time}</span>
                </div>
            </td>
            <td>
                <span class="laughter-class">${detection.class_name || 'Unknown'}</span>
            </td>
            <td>
                <span class="probability">${(detection.probability * 100).toFixed(1)}%</span>
            </td>
            <td>
                <input type="text" class="notes-input" 
                       value="${detection.notes || ''}" 
                       placeholder="Add notes..."
                       onchange="app.updateDetectionNotes('${detection.id}', this.value)">
            </td>
            <td>
                <button class="btn btn-danger" onclick="app.deleteDetection('${detection.id}')">
                    Delete
                </button>
            </td>
        `;
        
        // LAZY LOADING (2025-11-24): Fetch audio file asynchronously (non-blocking for row creation)
        // 
        // WHY THIS IS NEEDED:
        // - Previously, all audio clips were fetched synchronously when rows were created
        // - For days with 300+ detections, this meant 300+ simultaneous fetch requests
        // - Browser throttling caused requests to be aborted or fail
        // - Result: ERR_CONTENT_LENGTH_MISMATCH errors and "Audio file not available" messages
        // 
        // SOLUTION:
        // - Rows render immediately with "Loading..." state
        // - Audio is fetched asynchronously in background
        // - AbortController cancels fetches for rows removed from DOM
        // - Browser can throttle requests naturally without overwhelming the network
        // 
        // IMPACT:
        // - Fixes ERR_CONTENT_LENGTH_MISMATCH errors
        // - Prevents browser from being overwhelmed by simultaneous requests
        // - Better user experience (rows appear immediately, audio loads progressively)
        // - Reduces network congestion and improves reliability
        this.getAudioUrl(detection.id, abortController.signal).then(audioUrl => {
            // Only update if row still exists and hasn't been removed
            if (row.parentNode && !abortController.signal.aborted) {
                const audioClipDiv = row.querySelector('.audio-clip');
                if (audioClipDiv) {
                    const loadingSpan = audioClipDiv.querySelector('.loading-audio');
                    if (loadingSpan) {
                        loadingSpan.remove();
                    }
                    
                    // Only show audio player if we have a valid URL (file exists)
                    if (audioUrl) {
                        const audio = document.createElement('audio');
                        audio.controls = true;
                        audio.preload = 'metadata';
                        const source = document.createElement('source');
                        source.src = audioUrl;
                        source.type = 'audio/wav';
                        audio.appendChild(source);
                        audioClipDiv.insertBefore(audio, audioClipDiv.querySelector('span'));
                    } else {
                        const noAudioSpan = document.createElement('span');
                        noAudioSpan.className = 'no-audio';
                        noAudioSpan.textContent = 'Audio file not available';
                        audioClipDiv.insertBefore(noAudioSpan, audioClipDiv.querySelector('span'));
                    }
                }
            }
        }).catch(error => {
            // Silently handle errors (already logged in getAudioUrl)
            if (row.parentNode && !abortController.signal.aborted) {
                const audioClipDiv = row.querySelector('.audio-clip');
                if (audioClipDiv) {
                    const loadingSpan = audioClipDiv.querySelector('.loading-audio');
                    if (loadingSpan) {
                        loadingSpan.remove();
                        const noAudioSpan = document.createElement('span');
                        noAudioSpan.className = 'no-audio';
                        noAudioSpan.textContent = 'Audio file not available';
                        audioClipDiv.insertBefore(noAudioSpan, audioClipDiv.querySelector('span'));
                    }
                }
            }
        });
        
        return row;
    }
    
    /**
     * Fetch audio file from backend and create a blob URL for HTML5 audio player.
     * Returns null if file doesn't exist (404) or fetch fails. Uses authentication token.
     * @param {string} clipId - UUID of the laughter detection
     * @param {AbortSignal} signal - Optional abort signal to cancel the request
     * @returns {string|null} Blob URL for audio playback, or null if unavailable
     */
    async getAudioUrl(clipId, signal = null) {
        try {
            // Fetch audio file with authentication
            const response = await fetch(`${this.apiBase}/audio-clips/${clipId}`, {
                headers: {
                    'Authorization': `Bearer ${this.authToken}`
                },
                signal: signal // Allow cancellation if row is removed
            });
            
            if (!response.ok) {
                if (response.status === 404) {
                    // File doesn't exist - return null instead of throwing (graceful degradation)
                    console.warn(`Audio clip ${clipId} not found (404)`);
                    return null;
                }
                throw new Error(`Failed to fetch audio: ${response.status}`);
            }
            
            // Convert response to blob and create object URL for audio player
            const blob = await response.blob();
            return URL.createObjectURL(blob); // Creates temporary URL like blob:http://localhost:8000/abc123
        } catch (error) {
            // Don't log abort errors (expected when row is removed)
            if (error.name !== 'AbortError') {
                // SECURITY: Don't log full error objects (may contain sensitive paths)
                // Only log error type and status code
                const errorMsg = error.message || 'Unknown error';
                console.warn(`Audio fetch failed for clip ${clipId.substring(0, 8)}...: ${errorMsg}`);
            }
            return null; // Return null to indicate no audio available (not an error state)
        }
    }
    
    /**
     * Update notes for a specific laughter detection.
     * Called when user types in the notes input field and changes focus.
     * @param {string} detectionId - UUID of the laughter detection
     * @param {string} notes - New notes text
     */
    async updateDetectionNotes(detectionId, notes) {
        try {
            await this.makeRequest(`/laughter-detections/${detectionId}`, 'PUT', {
                notes: notes
            });
            this.showToast('Notes updated successfully', 'success');
        } catch (error) {
            this.showToast('Failed to update notes: ' + error.message, 'error');
        }
    }
    
    /**
     * Delete a single laughter detection - removes from database and deletes audio file.
     * Requires confirmation. After deletion, refreshes both day detail view and daily summary
     * to ensure counts are accurate.
     * @param {string} detectionId - UUID of the laughter detection to delete
     */
    async deleteDetection(detectionId) {
        console.log('🗑️ deleteDetection called with ID:', detectionId);
        
        if (!confirm('Are you sure you want to delete this laughter detection?')) {
            console.log('🗑️ User cancelled deletion');
            return;
        }
        
        try {
            console.log('🗑️ Making DELETE request to:', `/laughter-detections/${detectionId}`);
            this.showLoading('Deleting detection...');
            
            const response = await this.makeRequest(`/laughter-detections/${detectionId}`, 'DELETE');
            console.log('🗑️ Delete response:', response);
            
            this.hideLoading();
            this.showToast('Detection deleted successfully', 'success');
            
            // CRITICAL: Refresh both the day detail view AND the daily summary
            // The day detail view is already visible, so refresh it to remove deleted row
            this.showDayDetail(this.currentDate); // Reload the day detail
            
            // Also refresh the daily summary so when user navigates back, count is correct
            // This is in the background - doesn't change current view
            await this.loadDailySummary();
            
        } catch (error) {
            console.error('🗑️ Delete error:', error);
            this.hideLoading();
            this.showToast('Failed to delete detection: ' + error.message, 'error');
        }
    }
    
    /**
     * Filter laughter detections table by probability threshold.
     * Hides rows with probability below the threshold. Real-time filtering as user moves slider.
     * @param {string} value - Probability threshold (0.0 to 1.0) as string
     */
    updateProbabilityFilter(value) {
        document.getElementById('filter-value').textContent = value;
        // Filter table rows based on probability threshold
        const rows = document.querySelectorAll('#detections-tbody tr');
        rows.forEach(row => {
            const probabilityCell = row.querySelector('.probability');
            if (probabilityCell) {
                const probability = parseFloat(probabilityCell.textContent) / 100;
                // Show row if probability meets threshold, hide otherwise
                if (probability >= parseFloat(value)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            }
        });
    }
    
    /**
     * Central API request handler - makes authenticated HTTP requests to backend.
     * Automatically adds auth token to headers, handles 401 errors with auto-logout,
     * and parses JSON responses. Used by all API calls in the app.
     * 
     * @param {string} endpoint - API endpoint path (e.g., '/daily-summary', '/auth/login')
     * @param {string} method - HTTP method ('GET', 'POST', 'PUT', 'DELETE')
     * @param {Object|null} data - Request body data (will be JSON stringified)
     * @returns {Promise<Object>} Parsed JSON response from backend
     * @throws {Error} If request fails (non-2xx status) or network error
     */
    async makeRequest(endpoint, method = 'GET', data = null) {
        const url = this.apiBase + endpoint;
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        // Add authentication token if available (all requests except login/register)
        if (this.authToken) {
            options.headers['Authorization'] = `Bearer ${this.authToken}`;
        }
        
        // Add request body for POST/PUT requests
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            // AUTO-LOGOUT: Detect expired/invalid token (401) and automatically log user out
            // Skip auto-logout for auth endpoints (login/register) to avoid logout loops
            if (response.status === 401 && !endpoint.includes('/auth/')) {
                this.clearAuth();
                this.showAuthSection();
                this.showToast('Session expired. Please log in again.', 'error');
                // Throw error to prevent further processing in calling code
                throw new Error('Session expired');
            }
            
            // Parse error response and throw with backend error message
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        return await response.json();
    }
    
    /**
     * Show loading overlay with custom message. Blocks UI interaction during async operations.
     * @param {string} message - Loading message to display
     */
    showLoading(message = 'Loading...') {
        document.getElementById('loading-message').textContent = message;
        document.getElementById('loading-overlay').classList.remove('hidden');
    }
    
    /**
     * Hide loading overlay. Called after async operation completes.
     */
    hideLoading() {
        document.getElementById('loading-overlay').classList.add('hidden');
    }
    
    /**
     * Show temporary toast notification (success, error, warning, info).
     * Auto-dismisses after 5 seconds. Appended to toast container.
     * @param {string} message - Toast message text
     * @param {string} type - Toast type: 'success', 'error', 'warning', 'info'
     */
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        // Auto-remove toast after 5 seconds
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
    
    /**
     * Show login/registration screen. Hides all app screens.
     * Called when user is not authenticated or session expires.
     */
    showAuthSection() {
        // Hide ALL app screens first
        document.getElementById('app-section').classList.add('hidden');
        document.getElementById('daily-summary').classList.add('hidden');
        document.getElementById('day-detail').classList.add('hidden');
        document.getElementById('settings-screen').classList.add('hidden');
        document.getElementById('limitless-setup').classList.add('hidden');
        
        // Show auth section (login/register forms)
        document.getElementById('auth-section').classList.remove('hidden');
    }
    
    /**
     * Show main app container. Hides auth screen and shows appropriate app screen.
     * Automatically checks if user needs to set up Limitless API key.
     */
    showAppSection() {
        // Hide auth section first
        document.getElementById('auth-section').classList.add('hidden');
        
        // Hide all app screens to start fresh
        document.getElementById('daily-summary').classList.add('hidden');
        document.getElementById('day-detail').classList.add('hidden');
        document.getElementById('settings-screen').classList.add('hidden');
        document.getElementById('limitless-setup').classList.add('hidden');
        
        // Show app container
        document.getElementById('app-section').classList.remove('hidden');
        
        // Check if user has Limitless key setup (will show setup or summary)
        this.showLimitlessSetup();
    }
    
    /**
     * Show Limitless API key setup screen. Called when user doesn't have API key configured.
     */
    showLimitlessSetup() {
        // Hide ALL other screens first
        document.getElementById('daily-summary').classList.add('hidden');
        document.getElementById('day-detail').classList.add('hidden');
        document.getElementById('settings-screen').classList.add('hidden');
        
        // Show setup screen (prompts user to enter Limitless API key)
        document.getElementById('limitless-setup').classList.remove('hidden');
    }
    
    /**
     * Show daily summary screen with all days' laughter counts. Loads data from backend.
     */
    showDailySummary() {
        // Hide ALL other screens first
        document.getElementById('limitless-setup').classList.add('hidden');
        document.getElementById('day-detail').classList.add('hidden');
        document.getElementById('settings-screen').classList.add('hidden');
        
        // Show daily summary screen
        document.getElementById('daily-summary').classList.remove('hidden');
        this.loadDailySummary(); // Fetch and display summary data
    }
    
    /**
     * Show day detail view header. Called before loading detections.
     * Formats and displays the date in user-friendly format.
     */
    showDayDetailView() {
        // Hide ALL other screens first
        document.getElementById('daily-summary').classList.add('hidden');
        document.getElementById('settings-screen').classList.add('hidden');
        document.getElementById('limitless-setup').classList.add('hidden');
        
        // Show day detail screen
        document.getElementById('day-detail').classList.remove('hidden');
        
        // Parse the date correctly to avoid timezone issues (add noon to prevent shifting)
        const date = new Date(this.currentDate + 'T12:00:00');
        document.getElementById('detail-date').textContent = 
            date.toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
    }
    
    /**
     * Navigate back to daily summary view from day detail or settings.
     * Updates navigation state to show home as active.
     */
    showSummaryView() {
        // Hide ALL screens first
        document.getElementById('day-detail').classList.add('hidden');
        document.getElementById('settings-screen').classList.add('hidden');
        document.getElementById('limitless-setup').classList.add('hidden');
        
        // Show daily summary
        document.getElementById('daily-summary').classList.remove('hidden');
        
        // Update navigation (highlight home button)
        this.updateNavigation('nav-home');
    }

    /**
     * Show settings screen - displays data management options (delete data, reprocess, etc.).
     * Resets reprocess form state to prevent stuck "Processing..." button if user navigated away.
     * Updates navigation to highlight settings button.
     */
    showSettingsScreen() {
        // Hide ALL other screens first
        document.getElementById('daily-summary').classList.add('hidden');
        document.getElementById('day-detail').classList.add('hidden');
        document.getElementById('limitless-setup').classList.add('hidden');
        
        // Show settings screen
        document.getElementById('settings-screen').classList.remove('hidden');
        
        // FIX: Reset reprocess button state in case it was left in processing state
        // Prevents button showing "Processing..." and being disabled when screen loads
        // This can happen if user navigated away during processing
        const reprocessBtn = document.getElementById('reprocess-date-range');
        const startDateInput = document.getElementById('reprocess-start-date');
        const endDateInput = document.getElementById('reprocess-end-date');
        const statusDiv = document.getElementById('reprocess-status');
        if (reprocessBtn) {
            reprocessBtn.disabled = false;
            reprocessBtn.textContent = 'Reprocess Date Range';
        }
        if (startDateInput) startDateInput.disabled = false;
        if (endDateInput) endDateInput.disabled = false;
        if (statusDiv) statusDiv.classList.add('hidden');
        
        // Update navigation (highlight settings button)
        this.updateNavigation('nav-settings');
    }

    /**
     * Update navigation state - highlights the active nav button.
     * Called when switching between screens to show which section is active.
     * @param {string} activeNavId - ID of the nav button to highlight (e.g., 'nav-home', 'nav-settings')
     */
    updateNavigation(activeNavId) {
        // Remove active class from all nav items
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Add active class to the specified nav item
        document.getElementById(activeNavId).classList.add('active');
    }
    
    /**
     * Switch auth form to show login form. Hides registration form.
     * Called when user clicks "Sign in" link from registration form.
     */
    showLoginForm() {
        document.getElementById('login-form').classList.remove('hidden');
        document.getElementById('register-form').classList.add('hidden');
    }
    
    /**
     * Switch auth form to show registration form. Hides login form.
     * Called when user clicks "Create account" link from login form.
     */
    showRegisterForm() {
        document.getElementById('login-form').classList.add('hidden');
        document.getElementById('register-form').classList.remove('hidden');
    }
    
    /**
     * Handle user logout - clears auth state and shows login screen.
     * Called when logout button is clicked or session expires.
     */
    handleLogout() {
        this.clearAuth();
        this.showAuthSection();
        this.showToast('Logged out successfully', 'success');
    }
    
    /**
     * Clear all authentication data - token, user object, and localStorage.
     * Called on logout or when session expires (401 error).
     */
    clearAuth() {
        this.authToken = null;
        this.currentUser = null;
        localStorage.removeItem('auth_token'); // Remove token from browser storage
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new LaughterDetectorApp();
});
