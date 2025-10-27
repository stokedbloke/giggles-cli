/**
 * Laughter Detector Frontend JavaScript
 * 
 * This module handles the frontend functionality including authentication,
 * API communication, and UI interactions for the laughter detection system.
 */

class LaughterDetectorApp {
    constructor() {
        this.apiBase = '/api';
        this.authToken = localStorage.getItem('auth_token');
        this.currentUser = null;
        this.currentDate = null;
        this.userTimezone = null; // User's timezone (IANA format)
        
        this.init();
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
    
    init() {
        this.setupEventListeners();
        this.checkAuthStatus();
    }
    
    setupEventListeners() {
        // Authentication form events
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
        
        // Day detail navigation
        document.getElementById('back-to-summary').addEventListener('click', () => {
            this.showSummaryView();
        });
        
        // Probability filter
        document.getElementById('probability-filter').addEventListener('input', (e) => {
            this.updateProbabilityFilter(e.target.value);
        });
        
        // Logout button
        document.getElementById('logout-btn').addEventListener('click', () => {
            this.handleLogout();
        });
    }
    
    async checkAuthStatus() {
        if (this.authToken) {
            try {
                const response = await this.makeRequest('/auth/me', 'GET');
                console.log('✅ Auth response:', response);
                
                this.currentUser = response.user;
                this.userTimezone = response.user?.timezone || 'UTC';
                
                console.log('✅ User timezone set to:', this.userTimezone);
                
                // If user has UTC timezone, update it with detected timezone
                if (this.userTimezone === 'UTC' && this.currentUser) {
                    await this.updateTimezoneOnLogin();
                }
                
                await this.checkUserStatus();
            } catch (error) {
                console.error('❌ Auth check failed:', error);
                this.clearAuth();
                this.showAuthSection();
            }
        } else {
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
    
    async checkUserStatus() {
        // Check if user has an API key
        try {
            const response = await this.makeRequest('/limitless-key/status', 'GET');
            if (response.has_key) {
                // User has API key, show daily summary
                this.showAppSection();
                this.showDailySummary();
            } else {
                // User doesn't have API key, show setup
                this.showAppSection();
                this.showLimitlessSetup();
            }
        } catch (error) {
            // If status check fails, assume no API key
            this.showAppSection();
            this.showLimitlessSetup();
        }
    }
    
    async handleLogin() {
        const email = document.getElementById('login-email').value;
        const password = document.getElementById('login-password').value;
        
        try {
            this.showLoading('Signing in...');
            const response = await this.makeRequest('/auth/login', 'POST', {
                email, password
            });
            
            this.authToken = response.access_token;
            this.currentUser = response.user;
            localStorage.setItem('auth_token', this.authToken);
            
            this.hideLoading();
            this.showToast('Successfully signed in!', 'success');
            await this.checkUserStatus();
            
        } catch (error) {
            this.hideLoading();
            const errorMessage = error.detail || error.message || 'Login failed';
            this.showToast('Login failed: ' + errorMessage, 'error');
        }
    }
    
    async handleRegister() {
        const email = document.getElementById('register-email').value;
        const password = document.getElementById('register-password').value;
        const timezone = this.detectTimezone(); // Detect user's timezone
        
        try {
            this.showLoading('Creating account...');
            const response = await this.makeRequest('/auth/register', 'POST', {
                email, 
                password,
                timezone  // Send timezone to backend
            });
            
            this.hideLoading();
            this.showToast('Account created successfully! Please sign in.', 'success');
            this.showLoginForm();
            
        } catch (error) {
            this.hideLoading();
            this.showToast('Registration failed: ' + error.message, 'error');
        }
    }
    
    async handleLimitlessKey() {
        const apiKey = document.getElementById('limitless-key').value;
        
        try {
            this.showLoading('Validating and storing API key...');
            const response = await this.makeRequest('/limitless-key', 'POST', {
                api_key: apiKey
            });
            
            this.hideLoading();
            this.showToast('API key stored successfully!', 'success');
            this.showDailySummary();
            
        } catch (error) {
            this.hideLoading();
            this.showToast('Failed to store API key: ' + error.message, 'error');
        }
    }
    
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
            
            // Redirect to home page to reset all state
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
            
        } catch (error) {
            this.hideLoading();
            this.showToast('Failed to delete data: ' + error.message, 'error');
        }
    }
    
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
            
            // Simple solution: redirect to home page to reset all state
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
            
        } catch (error) {
            this.hideLoading();
            this.showToast('Failed to delete API key: ' + error.message, 'error');
        }
    }
    
    async handleUpdateTodayData() {
        try {
            this.showLoading('Updating today\'s laughter data...');
            const response = await this.makeRequest('/trigger-nightly-processing', 'POST');
            
            this.hideLoading();
            
            // Handle different response statuses
            if (response.status === 'timeout') {
                this.showToast('Processing timed out - Limitless API may be slow. Try again later.', 'warning');
            } else if (response.status === 'completed') {
                this.showToast('Processing completed successfully!', 'success');
            } else if (response.message && response.message.includes('triggered successfully')) {
                this.showToast('Processing triggered successfully!', 'success');
            } else {
                this.showToast('Processing completed!', 'success');
            }
            
            // Refresh the daily summary to show updated data
            await this.showDailySummary();
            
        } catch (error) {
            this.hideLoading();
            this.showToast('Failed to update today\'s data: ' + error.message, 'error');
        }
    }
    

    async loadDailySummary() {
        try {
            const response = await this.makeRequest('/daily-summary', 'GET');
            this.displayDailySummary(response);
        } catch (error) {
            this.showToast('Failed to load daily summary: ' + error.message, 'error');
        }
    }
    
    displayDailySummary(summary) {
        const container = document.getElementById('summary-cards');
        container.innerHTML = '';
        
        if (summary.length === 0) {
            container.innerHTML = '<p class="no-data">No laughter data available yet. Audio processing may still be in progress.</p>';
            return;
        }
        
        // Only show cards for days with laughter events
        const daysWithLaughter = summary.filter(day => day.total_laughter_events > 0);
        
        if (daysWithLaughter.length === 0) {
            container.innerHTML = '<p class="no-data">No laughter detected yet. Audio processing is working - laughter will appear here when detected.</p>';
            return;
        }
        
        daysWithLaughter.forEach(day => {
            const card = this.createDayCard(day);
            container.appendChild(card);
        });
    }
    
    createDayCard(day) {
        const card = document.createElement('div');
        card.className = 'day-card';
        card.onclick = () => this.showDayDetail(day.date);
        
        // Parse date string correctly to avoid timezone issues
        const date = new Date(day.date + 'T12:00:00'); // Add noon to avoid timezone issues
        const dayName = date.toLocaleDateString('en-US', { weekday: 'long' });
        const monthDay = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        
        card.innerHTML = `
            <h3>${day.total_laughter_events}</h3>
            <p>${dayName}</p>
            <p class="date">${monthDay}</p>
        `;
        
        return card;
    }
    
    async showDayDetail(date) {
        this.currentDate = date;
        this.showDayDetailView();
        
        try {
            this.showLoading('Loading day details...');
            const response = await this.makeRequest(`/laughter-detections/${date}`, 'GET');
            this.displayDayDetail(response);
            this.hideLoading();
        } catch (error) {
            this.hideLoading();
            this.showToast('Failed to load day details: ' + error.message, 'error');
        }
    }
    
    async displayDayDetail(detections) {
        const tbody = document.getElementById('detections-tbody');
        tbody.innerHTML = '';
        
        if (detections.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="no-data">No laughter detections for this day.</td></tr>';
            return;
        }
        
        for (const detection of detections) {
            const row = await this.createDetectionRow(detection);
            tbody.appendChild(row);
        }
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
    
    async createDetectionRow(detection) {
        const row = document.createElement('tr');
        
        // Format time in user's timezone
        const timezone = this.userTimezone || this.detectTimezone();
        const time = this.formatTimestampToTimezone(detection.timestamp, timezone);
        
        // Fetch audio with auth and create blob URL
        const audioUrl = await this.getAudioUrl(detection.id);
        
        row.innerHTML = `
            <td>
                <div class="audio-clip">
                    <audio controls preload="metadata">
                        <source src="${audioUrl}" type="audio/wav">
                        Your browser does not support the audio element.
                    </audio>
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
        
        return row;
    }
    
    async getAudioUrl(clipId) {
        try {
            const response = await fetch(`${this.apiBase}/audio-clips/${clipId}`, {
                headers: {
                    'Authorization': `Bearer ${this.authToken}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to fetch audio');
            }
            
            const blob = await response.blob();
            return URL.createObjectURL(blob);
        } catch (error) {
            console.error('Error fetching audio:', error);
            return '#';
        }
    }
    
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
            this.showDayDetail(this.currentDate); // Reload the day detail
            
        } catch (error) {
            console.error('🗑️ Delete error:', error);
            this.hideLoading();
            this.showToast('Failed to delete detection: ' + error.message, 'error');
        }
    }
    
    updateProbabilityFilter(value) {
        document.getElementById('filter-value').textContent = value;
        // Filter table rows based on probability
        const rows = document.querySelectorAll('#detections-tbody tr');
        rows.forEach(row => {
            const probabilityCell = row.querySelector('.probability');
            if (probabilityCell) {
                const probability = parseFloat(probabilityCell.textContent) / 100;
                if (probability >= parseFloat(value)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            }
        });
    }
    
    async makeRequest(endpoint, method = 'GET', data = null) {
        const url = this.apiBase + endpoint;
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        if (this.authToken) {
            options.headers['Authorization'] = `Bearer ${this.authToken}`;
        }
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        
        return await response.json();
    }
    
    showLoading(message = 'Loading...') {
        document.getElementById('loading-message').textContent = message;
        document.getElementById('loading-overlay').classList.remove('hidden');
    }
    
    hideLoading() {
        document.getElementById('loading-overlay').classList.add('hidden');
    }
    
    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
    
    showAuthSection() {
        document.getElementById('auth-section').classList.remove('hidden');
        document.getElementById('app-section').classList.add('hidden');
        document.getElementById('day-detail').classList.add('hidden');
    }
    
    showAppSection() {
        document.getElementById('auth-section').classList.add('hidden');
        document.getElementById('app-section').classList.remove('hidden');
        document.getElementById('day-detail').classList.add('hidden');
        
        // Check if user has Limitless key setup
        this.showLimitlessSetup();
    }
    
    showLimitlessSetup() {
        document.getElementById('limitless-setup').classList.remove('hidden');
        document.getElementById('daily-summary').classList.add('hidden');
    }
    
    showDailySummary() {
        document.getElementById('limitless-setup').classList.add('hidden');
        document.getElementById('daily-summary').classList.remove('hidden');
        this.loadDailySummary();
    }
    
    showDayDetailView() {
        document.getElementById('app-section').classList.add('hidden');
        document.getElementById('day-detail').classList.remove('hidden');
        
        const date = new Date(this.currentDate);
        document.getElementById('detail-date').textContent = 
            date.toLocaleDateString('en-US', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
    }
    
    showSummaryView() {
        document.getElementById('app-section').classList.remove('hidden');
        document.getElementById('day-detail').classList.add('hidden');
    }
    
    showLoginForm() {
        document.getElementById('login-form').classList.remove('hidden');
        document.getElementById('register-form').classList.add('hidden');
    }
    
    showRegisterForm() {
        document.getElementById('login-form').classList.add('hidden');
        document.getElementById('register-form').classList.remove('hidden');
    }
    
    handleLogout() {
        this.clearAuth();
        this.showAuthSection();
        this.showToast('Logged out successfully', 'success');
    }
    
    clearAuth() {
        this.authToken = null;
        this.currentUser = null;
        localStorage.removeItem('auth_token');
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new LaughterDetectorApp();
});
