// Global state management
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
    }
    
    getSectionId() {
        const sections = ['jd-section', 'structure-section', 'skills-section', 'resume-section', 'results-section'];
        return sections[this.currentStep - 1] || 'jd-section';
    }
}

// Utility functions
class Utils {
    static showLoading(message = 'Processing...') {
        const overlay = document.getElementById('loading-overlay');
        const messageEl = document.getElementById('loading-message');
        messageEl.textContent = message;
        overlay.classList.add('active');
    }
    
    static hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        overlay.classList.remove('active');
    }
    
    static showToast(message, type = 'info', duration = 5000) {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
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
                const errorData = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorData}`);
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

// Initialize app
const appState = new AppState();

// DOM ready
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Check if there's an existing session
    const existingSessionId = appState.getSessionId();
    if (existingSessionId) {
        Utils.showToast('Previous session found. Starting fresh.', 'info');
        localStorage.removeItem('ats_session_id');
        appState.sessionId = null;
    }
    
    // Initialize event listeners
    initializeEventListeners();
    
    // Show first step
    appState.updateUI();
}

function initializeEventListeners() {
    // JD file input
    document.getElementById('jd-file').addEventListener('change', handleJDFileSelect);
    
    // JD text input
    document.getElementById('jd-text').addEventListener('input', handleJDTextInput);
    
    // Process JD button
    document.getElementById('process-jd-btn').addEventListener('click', processJobDescription);
    
    // Structure approval buttons
    document.getElementById('approve-structure-btn').addEventListener('click', approveStructure);
    document.getElementById('request-changes-btn').addEventListener('click', requestStructureChanges);
    
    // Skills weightage button
    document.getElementById('set-weightage-btn').addEventListener('click', setSkillsWeightage);
    
    // Resume files input
    document.getElementById('resume-files').addEventListener('change', handleResumeFilesSelect);
    
    // Upload resumes button
    document.getElementById('upload-resumes-btn').addEventListener('click', uploadResumes);
    
    // Start matching button
    document.getElementById('start-matching-btn').addEventListener('click', startMatching);
}

function handleJDFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        try {
            Utils.validateFile(file);
            document.getElementById('jd-text').value = ''; // Clear text input
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
        document.getElementById('jd-file').value = ''; // Clear file input
    }
    updateProcessJDButton();
}

function updateProcessJDButton() {
    const fileInput = document.getElementById('jd-file');
    const textInput = document.getElementById('jd-text');
    const processBtn = document.getElementById('process-jd-btn');
    
    const hasFile = fileInput.files.length > 0;
    const hasText = textInput.value.trim().length > 0;
    
    processBtn.disabled = !(hasFile || hasText);
}

async function processJobDescription() {
    const fileInput = document.getElementById('jd-file');
    const textInput = document.getElementById('jd-text');
    
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
            throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }
        
        const result = await response.json();
        
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
        Utils.showToast(error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

function displayStructuredJD(structuredData) {
    const container = document.getElementById('structured-jd-display');
    
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



// Add navigation helper function
function goToResumeUpload() {
    appState.currentStep = 4;
    appState.updateUI();
    Utils.showToast('Please upload resumes before matching', 'info');
}

// Update the Start Matching button to check for resumes first
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
