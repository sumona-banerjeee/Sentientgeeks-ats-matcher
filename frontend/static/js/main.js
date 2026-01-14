// ============================================================================
// MAIN.JS - UPDATED WITH ROUTING INTEGRATION
// ============================================================================

class AppState {
    constructor() {
        this.sessionId = null;
        this.currentStep = 1;
        this.jdData = null;
        this.resumes = [];
        this.matchingResults = [];
    }
    
    setSessionId(sessionId) {
        this.sessionId = sessionId;
        localStorage.setItem('ats_session_id', sessionId);
    }
    
    getSessionId() {
        if (!this.sessionId) {
            this.sessionId = localStorage.getItem('ats_session_id');
        }
        return this.sessionId;
    }
    
    nextStep() {
        this.currentStep++;
        
        // Use router navigation if available
        if (typeof appRouter !== 'undefined' && appRouter.navigateToStep) {
            appRouter.navigateToStep(this.currentStep);
        } else {
            this.updateUI();
        }
    }
    
    updateUI() {
        // Hide all sections
        document.querySelectorAll('.section').forEach(section => {
            section.classList.remove('active');
        });
        
        // Show current step section
        const currentSection = document.querySelector(`#${this.getSectionId()}`);
        if (currentSection) {
            currentSection.classList.add('active');
        }
        
        // Update home button visibility
        if (typeof appRouter !== 'undefined' && appRouter.updateHomeButtonVisibility) {
            appRouter.updateHomeButtonVisibility();
        }
    }
    
    getSectionId() {
        const sections = ['jd-section', 'structure-section', 'skills-section', 'resume-section', 'results-section'];
        return sections[this.currentStep - 1] || 'jd-section';
    }
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================
class Utils {
    static showLoading(message = 'Processing...') {
        const overlay = document.getElementById('loading-overlay');
        const messageEl = document.getElementById('loading-message');
        if (messageEl) messageEl.textContent = message;
        if (overlay) overlay.classList.add('active');
    }
    
    static hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.classList.remove('active');
    }
    
    static showToast(message, type = 'info', duration = 5000) {
        const container = document.getElementById('toast-container');
        if (!container) {
            console.log(`Toast: [${type.toUpperCase()}] ${message}`);
            return;
        }
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            if (toast && toast.parentNode) {
                toast.remove();
            }
        }, duration);
    }
    
    static async makeRequest(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };
        
        const mergedOptions = { ...defaultOptions, ...options };
        
        if (mergedOptions.body && typeof mergedOptions.body === 'object' && !(mergedOptions.body instanceof FormData)) {
            mergedOptions.body = JSON.stringify(mergedOptions.body);
        }
        
        try {
            const response = await fetch(url, mergedOptions);
            
            if (!response.ok) {
                let errorData;
                try {
                    errorData = await response.json();
                } catch {
                    errorData = await response.text();
                }
                throw new Error(`HTTP ${response.status}: ${JSON.stringify(errorData)}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Request failed:', error);
            throw error;
        }
    }
    
    static formatScore(score) {
        const numScore = parseFloat(score);
        if (numScore >= 80) return { class: 'score-excellent', text: `${numScore.toFixed(1)}%` };
        if (numScore >= 60) return { class: 'score-good', text: `${numScore.toFixed(1)}%` };
        if (numScore >= 40) return { class: 'score-average', text: `${numScore.toFixed(1)}%` };
        return { class: 'score-poor', text: `${numScore.toFixed(1)}%` };
    }
    
    static validateFile(file, allowedTypes = ['application/pdf'], maxSize = 10 * 1024 * 1024) {
        if (!allowedTypes.includes(file.type)) {
            throw new Error(`Invalid file type. Allowed types: ${allowedTypes.join(', ')}`);
        }
        
        if (file.size > maxSize) {
            throw new Error(`File too large. Maximum size: ${maxSize / (1024 * 1024)}MB`);
        }
        
        return true;
    }
}

// ============================================================================
// INITIALIZE APP STATE (GLOBAL)
// ============================================================================
const appState = new AppState();

// ============================================================================
// DOM READY - INITIALIZE APPLICATION
// ============================================================================
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Check existing session
    const existingSessionId = appState.getSessionId();
    
    if (existingSessionId) {
        console.log('📦 Existing session found:', existingSessionId);
    }
    
    // Initialize event listeners
    initializeEventListeners();
    
    // Show first step
    appState.updateUI();
    
    console.log('✅ App initialized successfully');
}

// ============================================================================
// EVENT LISTENERS INITIALIZATION
// ============================================================================
function initializeEventListeners() {
    // JD file input
    const jdFileInput = document.getElementById('jd-file');
    if (jdFileInput) {
        jdFileInput.addEventListener('change', handleJDFileSelect);
    }
    
    // JD text input
    const jdTextInput = document.getElementById('jd-text');
    if (jdTextInput) {
        jdTextInput.addEventListener('input', handleJDTextInput);
    }
    
    // Process JD button
    const processBtn = document.getElementById('process-jd-btn');
    if (processBtn) {
        processBtn.addEventListener('click', processJobDescription);
    }
    
    // Structure approval buttons
    const approveBtn = document.getElementById('approve-structure-btn');
    if (approveBtn) {
        approveBtn.addEventListener('click', approveStructure);
    }
    
    const requestChangesBtn = document.getElementById('request-changes-btn');
    if (requestChangesBtn) {
        requestChangesBtn.addEventListener('click', requestStructureChanges);
    }
    
    // Skills weightage button
    const weightageBtn = document.getElementById('set-weightage-btn');
    if (weightageBtn) {
        weightageBtn.addEventListener('click', setSkillsWeightage);
    }
    
    // Resume files input
    const resumeFilesInput = document.getElementById('resume-files');
    if (resumeFilesInput) {
        resumeFilesInput.addEventListener('change', handleResumeFilesSelect);
    }
    
    // Start matching button
    const startMatchingBtn = document.getElementById('start-matching-btn');
    if (startMatchingBtn) {
        startMatchingBtn.addEventListener('click', startMatching);
    }
}

// ============================================================================
// JD UPLOAD HANDLERS
// ============================================================================
function handleJDFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        try {
            Utils.validateFile(file);
            const textInput = document.getElementById('jd-text');
            if (textInput) textInput.value = '';
            updateProcessJDButton();
            Utils.showToast('JD file selected successfully', 'success');
        } catch (error) {
            Utils.showToast(error.message, 'error');
            event.target.value = '';
        }
    }
}

function handleJDTextInput(event) {
    if (event.target.value.trim()) {
        const fileInput = document.getElementById('jd-file');
        if (fileInput) fileInput.value = '';
    }
    updateProcessJDButton();
}

function updateProcessJDButton() {
    const fileInput = document.getElementById('jd-file');
    const textInput = document.getElementById('jd-text');
    const processBtn = document.getElementById('process-jd-btn');
    
    if (!fileInput || !textInput || !processBtn) return;
    
    const hasFile = fileInput.files.length > 0;
    const hasText = textInput.value.trim().length > 0;
    
    processBtn.disabled = !(hasFile || hasText);
}

// ============================================================================
// PROCESS JOB DESCRIPTION
// ============================================================================
async function processJobDescription() {
    const fileInput = document.getElementById('jd-file');
    const textInput = document.getElementById('jd-text');
    
    if (!fileInput || !textInput) {
        Utils.showToast('Required form elements not found', 'error');
        return;
    }
    
    try {
        Utils.showLoading('Processing job description...');
        
        const formData = new FormData();
        
        if (fileInput.files.length > 0) {
            formData.append('file', fileInput.files[0]);
        } else if (textInput.value.trim()) {
            formData.append('text', textInput.value.trim());
        } else {
            throw new Error('Please provide either a JD file or text');
        }
        
        const response = await fetch('/api/jd/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            let errorText;
            try {
                const errorData = await response.json();
                errorText = errorData.detail || errorData.message || JSON.stringify(errorData);
            } catch {
                errorText = await response.text() || `HTTP ${response.status}`;
            }
            throw new Error(`Server Error ${response.status}: ${errorText}`);
        }
        
        const result = await response.json();
        
        // Store session data
        appState.setSessionId(result.session_id);
        appState.jdData = result;
        
        // Display structured JD
        displayStructuredJD(result.structured_data);
        
        // Move to next step using router
        appState.nextStep();
        
        Utils.showToast('Job description processed successfully!', 'success');
        
    } catch (error) {
        console.error('Error processing JD:', error);
        Utils.showToast(`Error: ${error.message}`, 'error');
    } finally {
        Utils.hideLoading();
    }
}

function goToResumeUpload() {
    if (typeof appRouter !== 'undefined' && appRouter.navigateToStep) {
        appRouter.navigateToStep(4);
    } else {
        appState.currentStep = 4;
        appState.updateUI();
    }
    Utils.showToast('Please upload resumes before matching', 'info');
}

// ============================================================================
// MAKE FUNCTIONS GLOBALLY AVAILABLE
// ============================================================================
window.appState = appState;
window.Utils = Utils;
window.goToResumeUpload = goToResumeUpload;