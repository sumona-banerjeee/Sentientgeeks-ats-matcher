// ============================================================================
// GLOBAL STATE MANAGEMENT
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
        this.updateUI();
    }
    
    // 🔥 UPDATED: Added home button visibility update
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
        
        // 🔥 NEW: Update home button visibility (for routing.js integration)
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
            console.log(`Making request to: ${url}`);
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



// 🔥 UPDATED: Let routing.js handle state restoration
function initializeApp() {
    // Check if there's an existing session
    const existingSessionId = appState.getSessionId();
    
    if (existingSessionId) {
        console.log('📦 Existing session found:', existingSessionId);
        // Note: routing.js will restore state if it was a completed Step 5 session
    }
    
    // Initialize event listeners
    initializeEventListeners();
    
    // Show first step (will be overridden by routing.js if state is restored)
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
            if (textInput) textInput.value = ''; // Clear text input
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
        if (fileInput) fileInput.value = ''; // Clear file input
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
            console.log('Uploading file:', fileInput.files[0].name);
        } else if (textInput.value.trim()) {
            formData.append('text', textInput.value.trim());
            console.log('Uploading text, length:', textInput.value.trim().length);
        } else {
            throw new Error('Please provide either a JD file or text');
        }
        
        const response = await fetch('/api/jd/upload', {
            method: 'POST',
            body: formData
        });
        
        console.log('Response status:', response.status);
        
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
        console.log('JD processing result:', result);
        
        // Store session data
        appState.setSessionId(result.session_id);
        appState.jdData = result;
        
        // Display structured JD
        displayStructuredJD(result.structured_data);
        
        // Move to next step
        appState.nextStep();
        
        Utils.showToast('Job description processed successfully!', 'success');
        
    } catch (error) {
        console.error('Error processing JD:', error);
        
        if (error.message.includes('Failed to fetch')) {
            Utils.showToast('Cannot connect to server. Is the backend running?', 'error');
        } else if (error.message.includes('404')) {
            Utils.showToast('Upload endpoint not found. Check your backend API routes.', 'error');
        } else {
            Utils.showToast(`Error: ${error.message}`, 'error');
        }
    } finally {
        Utils.hideLoading();
    }
}



// ============================================================================
// DISPLAY STRUCTURED JD
// ============================================================================
function displayStructuredJD(structuredData) {
    const container = document.getElementById('structured-jd-display');
    if (!container) {
        console.log('Structured JD display container not found');
        return;
    }
    
    let html = '<div class="structured-jd">';
    html += '<h3>Structured Job Description</h3>';
    
    // Job Title
    if (structuredData.job_title) {
        html += `<div class="jd-field"><strong>Job Title:</strong> ${structuredData.job_title}</div>`;
    }
    
    // Company
    if (structuredData.company) {
        html += `<div class="jd-field"><strong>Company:</strong> ${structuredData.company}</div>`;
    }
    
    // Location
    if (structuredData.location) {
        html += `<div class="jd-field"><strong>Location:</strong> ${structuredData.location}</div>`;
    }
    
    // Experience Required
    if (structuredData.experience_required) {
        html += `<div class="jd-field"><strong>Experience Required:</strong> ${structuredData.experience_required}</div>`;
    }
    
    // Primary Skills
    if (structuredData.primary_skills && structuredData.primary_skills.length > 0) {
        html += '<div class="jd-field"><strong>Primary Skills:</strong><ul>';
        structuredData.primary_skills.forEach(skill => {
            html += `<li>${skill}</li>`;
        });
        html += '</ul></div>';
    }
    
    // Secondary Skills
    if (structuredData.secondary_skills && structuredData.secondary_skills.length > 0) {
        html += '<div class="jd-field"><strong>Secondary Skills:</strong><ul>';
        structuredData.secondary_skills.forEach(skill => {
            html += `<li>${skill}</li>`;
        });
        html += '</ul></div>';
    }
    
    // Responsibilities
    if (structuredData.responsibilities && structuredData.responsibilities.length > 0) {
        html += '<div class="jd-field"><strong>Key Responsibilities:</strong><ul>';
        structuredData.responsibilities.forEach(resp => {
            html += `<li>${resp}</li>`;
        });
        html += '</ul></div>';
    }
    
    // Qualifications
    if (structuredData.qualifications && structuredData.qualifications.length > 0) {
        html += '<div class="jd-field"><strong>Qualifications:</strong><ul>';
        structuredData.qualifications.forEach(qual => {
            html += `<li>${qual}</li>`;
        });
        html += '</ul></div>';
    }
    
    html += '</div>';
    
    container.innerHTML = html;
}



// ============================================================================
// STRUCTURE APPROVAL
// ============================================================================
async function approveStructure() {
    if (!appState.getSessionId()) {
        Utils.showToast('No active session found', 'error');
        return;
    }
    
    try {
        Utils.showLoading('Approving structure...');
        
        const response = await Utils.makeRequest(`/api/jd/approve-structure/${appState.getSessionId()}`, {
            method: 'POST',
            body: { approved: true }
        });
        
        if (response.ready_for_skills_weightage) {
            appState.nextStep();
            Utils.showToast('Structure approved! Please set skills weightage.', 'success');
        }
        
    } catch (error) {
        Utils.showToast(`Error approving structure: ${error.message}`, 'error');
    } finally {
        Utils.hideLoading();
    }
}



async function requestStructureChanges() {
    const feedback = prompt('Please provide feedback for structure changes:');
    if (!feedback) return;
    
    try {
        Utils.showLoading('Processing feedback...');
        
        const response = await Utils.makeRequest(`/api/jd/approve-structure/${appState.getSessionId()}`, {
            method: 'POST',
            body: { approved: false, feedback: feedback }
        });
        
        if (response.revised_structure) {
            displayStructuredJD(response.revised_structure);
            Utils.showToast('Structure updated based on feedback', 'success');
        }
        
    } catch (error) {
        Utils.showToast(`Error processing feedback: ${error.message}`, 'error');
    } finally {
        Utils.hideLoading();
    }
}



// ============================================================================
// SKILLS WEIGHTAGE
// ============================================================================
async function setSkillsWeightage() {
    // This would typically involve collecting skill weights from a form
    // For now, setting default weights
    const defaultWeights = {
        'python': 30,
        'javascript': 25,
        'react': 20,
        'sql': 15,
        'git': 10
    };
    
    try {
        Utils.showLoading('Setting skills weightage...');
        
        await Utils.makeRequest(`/api/jd/set-skills-weightage/${appState.getSessionId()}`, {
            method: 'POST',
            body: defaultWeights
        });
        
        appState.nextStep();
        Utils.showToast('Skills weightage set successfully!', 'success');
        
    } catch (error) {
        Utils.showToast(`Error setting skills weightage: ${error.message}`, 'error');
    } finally {
        Utils.hideLoading();
    }
}



// ============================================================================
// RESUME UPLOAD
// ============================================================================
function handleResumeFilesSelect(event) {
    const files = event.target.files;
    if (files && files.length > 0) {
        Utils.showToast(`${files.length} resume(s) selected`, 'success');
        
        // Enable upload button
        const uploadBtn = document.getElementById('upload-resumes-btn');
        if (uploadBtn) {
            uploadBtn.disabled = false;
        }
    }
}




// ============================================================================
// MATCHING
// ============================================================================
function goToResumeUpload() {
    appState.currentStep = 4;
    appState.updateUI();
    Utils.showToast('Please upload resumes before matching', 'info');
}



async function startMatching() {
    try {
        // First check if resumes exist
        const sessionResponse = await Utils.makeRequest(`/api/resumes/session/${appState.getSessionId()}`);
        
        if (!sessionResponse.resumes || sessionResponse.resumes.length === 0) {
            Utils.showToast('Please upload resumes first before starting matching', 'warning');
            goToResumeUpload();
            return;
        }
        
        Utils.showLoading('Starting ATS matching process...');
        
        const response = await Utils.makeRequest(`/api/matching/start/${appState.getSessionId()}`, {
            method: 'POST'
        });
        
        appState.matchingResults = response.ranking;
        await displayMatchingResults();
        
        // ✅ NEW: Explicitly save state after Step 5 completion
        if (typeof appRouter !== 'undefined' && appRouter.saveState) {
            appRouter.saveState();
            console.log('💾 State saved after Step 5 completion');
        }
        
        Utils.showToast(`Matching completed! Ranked ${response.successfully_matched} resumes.`, 'success');
        
    } catch (error) {
        console.error('Error starting matching:', error);
        if (error.message.includes('404') && error.message.includes('No matching results found')) {
            Utils.showToast('No resumes found. Please upload resumes first.', 'warning');
            goToResumeUpload();
        } else {
            Utils.showToast(error.message, 'error');
        }
    } finally {
        Utils.hideLoading();
    }
}



async function displayMatchingResults() {
    // Placeholder for displaying matching results
    // Your matcher.js file will handle the actual display
    console.log('Displaying matching results:', appState.matchingResults);
    appState.nextStep();
    
    // If you have displayMatchingResults function in matcher.js, call it here
    if (typeof window.displayMatchingResults === 'function') {
        await window.displayMatchingResults();
    }
}



// ============================================================================
// MAKE FUNCTIONS GLOBALLY AVAILABLE
// ============================================================================
window.appState = appState;
window.Utils = Utils;
window.displayStructuredJD = displayStructuredJD;
window.goToResumeUpload = goToResumeUpload;
