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
// INITIALIZE APP STATE
// ============================================================================

const appState = new AppState();

// ============================================================================
// DOM READY - SINGLE INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// ============================================================================
// APP INITIALIZATION
// ============================================================================

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
    
    console.log('✅ Main app initialized');
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

    // ✅ Resume upload completely handled by resume-uploader.js
    // ✅ Matching completely handled by matcher.js
    
    console.log('✅ Main.js event listeners initialized');
}

// ============================================================================
// JD PROCESSING FUNCTIONS
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
        
        const serverUrl = 'http://localhost:8000';
        const response = await fetch(`${serverUrl}/api/jd/upload`, {
            method: 'POST',
            body: formData,
            headers: {}
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
        
        appState.setSessionId(result.session_id);
        appState.jdData = result;
        
        displayStructuredJD(result.structured_data);
        appState.nextStep();
        
        Utils.showToast('Job description processed successfully!', 'success');
        
    } catch (error) {
        console.error('Error processing JD:', error);
        
        if (error.message.includes('Failed to fetch')) {
            Utils.showToast('Cannot connect to server. Is the backend running on port 8000?', 'error');
        } else if (error.message.includes('404')) {
            Utils.showToast('Upload endpoint not found. Check your backend API routes.', 'error');
        } else {
            Utils.showToast(`Error: ${error.message}`, 'error');
        }
    } finally {
        Utils.hideLoading();
    }
}

function displayStructuredJD(structuredData) {
    const container = document.getElementById('structured-jd-display');
    if (!container) {
        console.log('Structured JD display container not found');
        return;
    }
    
    let html = '<div class="structured-jd">';
    html += '<h3>Structured Job Description</h3>';
    
    if (structuredData.job_title) {
        html += `<div class="jd-field"><strong>Job Title:</strong> ${structuredData.job_title}</div>`;
    }
    
    if (structuredData.company) {
        html += `<div class="jd-field"><strong>Company:</strong> ${structuredData.company}</div>`;
    }
    
    if (structuredData.location) {
        html += `<div class="jd-field"><strong>Location:</strong> ${structuredData.location}</div>`;
    }
    
    if (structuredData.experience_required) {
        html += `<div class="jd-field"><strong>Experience Required:</strong> ${structuredData.experience_required}</div>`;
    }
    
    if (structuredData.primary_skills && structuredData.primary_skills.length > 0) {
        html += '<div class="jd-field"><strong>Primary Skills:</strong><ul>';
        structuredData.primary_skills.forEach(skill => {
            html += `<li>${skill}</li>`;
        });
        html += '</ul></div>';
    }
    
    if (structuredData.secondary_skills && structuredData.secondary_skills.length > 0) {
        html += '<div class="jd-field"><strong>Secondary Skills:</strong><ul>';
        structuredData.secondary_skills.forEach(skill => {
            html += `<li>${skill}</li>`;
        });
        html += '</ul></div>';
    }
    
    if (structuredData.responsibilities && structuredData.responsibilities.length > 0) {
        html += '<div class="jd-field"><strong>Key Responsibilities:</strong><ul>';
        structuredData.responsibilities.forEach(resp => {
            html += `<li>${resp}</li>`;
        });
        html += '</ul></div>';
    }
    
    if (structuredData.qualifications && structuredData.qualifications.length > 0) {
        html += '<div class="jd-field"><strong>Qualifications:</strong><ul>';
        structuredData.qualifications.forEach(qual => {
            html += `<li>${qual}</li>`;
        });
        html += '</ul></div>';
    }
    
    html += '</div>';
    container.innerHTML = html;
    displaySkillsWeightageForm(structuredData);
}

// ============================================================================
// STRUCTURE APPROVAL FUNCTIONS
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
// SKILLS WEIGHTAGE FUNCTION
// ============================================================================

// ============================================================================
// SKILLS WEIGHTAGE FUNCTION - Collects user input from form
// ============================================================================

async function setSkillsWeightage() {
    try {
        // Collect skill weightage from user input fields
        const skillWeightageInputs = document.querySelectorAll('.skill-weightage-input');
        
        if (!skillWeightageInputs || skillWeightageInputs.length === 0) {
            Utils.showToast('No skill weightage fields found. Please process JD first.', 'warning');
            return;
        }
        
        // Build weightage object from form inputs
        const skillsWeightage = {};
        let hasValidInput = false;
        let totalWeight = 0;
        
        skillWeightageInputs.forEach(input => {
            const skillName = input.dataset.skill || input.name;
            const weightValue = parseInt(input.value) || 0;
            
            if (weightValue > 0 && weightValue <= 100) {
                skillsWeightage[skillName] = weightValue;
                totalWeight += weightValue;
                hasValidInput = true;
            }
        });
        
        // Validate that user entered at least some skills
        if (!hasValidInput) {
            Utils.showToast('Please enter weightage for at least one skill (1-100)', 'error');
            return;
        }
        
        // Optional: Validate total doesn't exceed 100
        if (totalWeight > 100) {
            const proceed = confirm(`Total weightage is ${totalWeight}%. This exceeds 100%. Continue anyway?`);
            if (!proceed) return;
        }
        
        console.log('Collected skills weightage:', skillsWeightage);
        
        Utils.showLoading('Setting skills weightage...');
        
        const response = await Utils.makeRequest(`/api/jd/set-skills-weightage/${appState.getSessionId()}`, {
            method: 'POST',
            body: skillsWeightage
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
// NAVIGATION HELPERS
// ============================================================================

function goToResumeUpload() {
    appState.currentStep = 4;
    appState.updateUI();
    Utils.showToast('Please upload resumes before matching', 'info');
}

// ============================================================================
// MATCHING FUNCTIONS (Keep only if matcher.js doesn't have them)
// ============================================================================

async function startMatching() {
    try {
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

async function displayMatchingResults() {
    console.log('Displaying matching results:', appState.matchingResults);
    appState.nextStep();
}

// ============================================================================
// DISPLAY SKILLS WEIGHTAGE FORM
// ============================================================================

function displaySkillsWeightageForm(structuredData) {
    const container = document.getElementById('skills-weightage-form');
    if (!container) {
        console.warn('Skills weightage form container not found');
        return;
    }
    
    // Collect all skills from structured data
    const allSkills = [];
    
    if (structuredData.primary_skills && structuredData.primary_skills.length > 0) {
        allSkills.push(...structuredData.primary_skills.map(skill => ({
            name: skill,
            type: 'primary',
            suggested: 30 // Suggested weightage for primary skills
        })));
    }
    
    if (structuredData.secondary_skills && structuredData.secondary_skills.length > 0) {
        allSkills.push(...structuredData.secondary_skills.map(skill => ({
            name: skill,
            type: 'secondary',
            suggested: 15 // Suggested weightage for secondary skills
        })));
    }
    
    if (allSkills.length === 0) {
        container.innerHTML = '<p style="color: #999;">No skills found in JD. Please review JD structure.</p>';
        return;
    }
    
    // Generate HTML for skills form
    let html = '<div class="skills-weightage-container">';
    html += '<p style="margin-bottom: 20px; color: #666;">Enter weightage for each skill (1-100). Higher values indicate more importance.</p>';
    
    // Primary Skills Section
    const primarySkills = allSkills.filter(s => s.type === 'primary');
    if (primarySkills.length > 0) {
        html += '<div class="skill-section">';
        html += '<h4 style="color: #667eea; margin-bottom: 15px;">Primary Skills</h4>';
        
        primarySkills.forEach((skill, index) => {
            const skillId = `skill-${skill.name.toLowerCase().replace(/\s+/g, '-')}`;
            html += `
                <div class="skill-item" style="display: flex; align-items: center; margin-bottom: 12px; padding: 10px; background: #f8f9fa; border-radius: 6px;">
                    <label for="${skillId}" style="flex: 1; font-weight: 500;">${skill.name}:</label>
                    <input type="number" 
                           id="${skillId}" 
                           class="skill-weightage-input" 
                           data-skill="${skill.name}"
                           name="${skill.name}"
                           min="1" 
                           max="100"
                           placeholder="${skill.suggested}"
                           style="width: 100px; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    <span style="margin-left: 10px; color: #999; font-size: 12px;">Suggested: ${skill.suggested}</span>
                </div>
            `;
        });
        
        html += '</div>';
    }
    
    // Secondary Skills Section
    const secondarySkills = allSkills.filter(s => s.type === 'secondary');
    if (secondarySkills.length > 0) {
        html += '<div class="skill-section" style="margin-top: 25px;">';
        html += '<h4 style="color: #764ba2; margin-bottom: 15px;">Secondary Skills</h4>';
        
        secondarySkills.forEach((skill, index) => {
            const skillId = `skill-${skill.name.toLowerCase().replace(/\s+/g, '-')}`;
            html += `
                <div class="skill-item" style="display: flex; align-items: center; margin-bottom: 12px; padding: 10px; background: #f8f9fa; border-radius: 6px;">
                    <label for="${skillId}" style="flex: 1; font-weight: 500;">${skill.name}:</label>
                    <input type="number" 
                           id="${skillId}" 
                           class="skill-weightage-input" 
                           data-skill="${skill.name}"
                           name="${skill.name}"
                           min="1" 
                           max="100"
                           placeholder="${skill.suggested}"
                           style="width: 100px; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                    <span style="margin-left: 10px; color: #999; font-size: 12px;">Suggested: ${skill.suggested}</span>
                </div>
            `;
        });
        
        html += '</div>';
    }
    
    html += '</div>';
    
    container.innerHTML = html;
    console.log(`✅ Skills weightage form generated for ${allSkills.length} skills`);
}
