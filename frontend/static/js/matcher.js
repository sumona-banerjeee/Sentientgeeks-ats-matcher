async function startMatching() {
    try {
        Utils.showLoading('Starting ATS matching process...');
        
        const response = await Utils.makeRequest(`/api/matching/start/${appState.getSessionId()}`, {
            method: 'POST'
        });
        
        // Store matching results
        appState.matchingResults = response.ranking;
        
        // Display results
        await displayMatchingResults();

        await saveMatchingToHistory(appState.getSessionId());
        Utils.showToast(`Matching completed! Ranked ${response.successfully_matched} resumes.`, 'success');
        
    } catch (error) {
        console.error('Error starting matching:', error);
        Utils.showToast(error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

async function displayMatchingResults() {
    try {
        const sessionId = appState.getSessionId();
        const response = await Utils.makeRequest(`/api/matching/results/${sessionId}`);
        const results = response.results;

        const container = document.getElementById('results-content');

        if (!results || results.length === 0) {
            container.innerHTML = '<p>No matching results found.</p>';
            return;
        }

        // Build results HTML
        let html = `
            <div class="results-summary">
                <h3>ATS Matching Results</h3>
                <p>Total Candidates Processed: <strong>${results.length}</strong></p>
                <p>Session ID: <code>${sessionId}</code></p>
            </div>

            <div class="results-table-container">
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Candidate Name</th>
                            <th>Filename</th>
                            <th>Overall Score</th>
                            <th>Skill Match</th>
                            <th>Experience</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        results.forEach(result => {
            const overallScore = Utils.formatScore(result.overall_score);
            const skillScore = Utils.formatScore(result.skill_match_score);
            const expScore = Utils.formatScore(result.experience_score);

            html += `
                <tr class="result-row" data-resume-id="${result.resume_id}">
                    <td><strong>#${result.rank}</strong></td>
                    <td>${result.candidate_name || 'Unknown'}</td>
                    <td>${result.filename}</td>
                    <td><span class="score-badge ${overallScore.class}">${overallScore.text}</span></td>
                    <td><span class="score-badge ${skillScore.class}">${skillScore.text}</span></td>
                    <td><span class="score-badge ${expScore.class}">${expScore.text}</span></td>
                    <td>
                        <button class="btn btn-sm btn-primary" 
                                data-resume-id="${result.resume_id}" 
                                data-session-id="${sessionId}"
                                onclick="showCandidateDetails('${sessionId}', ${result.resume_id})">
                            View Details
                        </button>
                    </td>
                </tr>
            `;
        });

        html += `
            <!-- Updated Export Interview Buttons -->
            <div class="export-buttons" style="margin-top: 20px; text-align: center;">
                <button id="generate-questions-btn" class="btn btn-success" onclick="generateInterviewQuestions(false)" style="margin-right: 10px;">
                    <i class="fas fa-question-circle"></i> Interview Questions
                </button>
                <button class="btn btn-secondary" onclick="exportResultsAsCSV()" style="margin-right: 10px;">
                    <i class="fas fa-download"></i> Export as CSV
                </button>
                <button class="btn btn-info" onclick="exportResultsAsJSON()" style="margin-right: 10px;">
                    <i class="fas fa-download"></i> Export as JSON
                </button>
                <button class="btn btn-warning" onclick="showHistory()" style="margin-right: 10px;">
                    <i class="fas fa-history"></i> History
                </button>
                <button class="btn btn-primary" onclick="startNewMatching()" style="margin-right: 10px;">
                    <i class="fas fa-redo"></i> Start New Matching
                </button>
            </div>
        `;

        container.innerHTML = html;

        // Add click handlers for row selection
        document.querySelectorAll('.result-row').forEach(row => {
            row.addEventListener('click', function () {
                document.querySelectorAll('.result-row.selected').forEach(r => r.classList.remove('selected'));
                this.classList.add('selected');
            });
        });

        // Add click handlers for "View Details" buttons
        container.querySelectorAll('button.btn-primary').forEach(button => {
            button.addEventListener('click', (event) => {
                event.stopPropagation(); // Prevent row selection on button click
                const resumeId = button.getAttribute('data-resume-id');
                const sessionId = button.getAttribute('data-session-id');
                showCandidateDetails(sessionId, resumeId);
            });
        });

    } catch (error) {
        console.error('Error displaying results:', error);
        Utils.showToast('Error displaying results: ' + error.message, 'error');
    }
}


// Function to show detailed candidate view
async function showCandidateDetails(sessionId, resumeId) {
    try {
        Utils.showLoading('Loading candidate details...');
        
        console.log('🔍 Debug: Fetching details for session:', sessionId, 'resume:', resumeId);
        
        const response = await Utils.makeRequest(`/api/matching/detailed/${sessionId}/${resumeId}`);
        
        // DEBUG: Log the entire response structure
        console.log('🔍 Debug: Full API response:', response);
        
        if (response) {
            displayCandidateModal(response);
        } else {
            Utils.showToast('No candidate details found', 'warning');
        }
        
    } catch (error) {
        console.error('❌ Error loading candidate details:', error);
        Utils.showToast('Error loading candidate details: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

function displayCandidateModal(data) {
    const modal = document.createElement('div');
    modal.className = 'candidate-modal-overlay';
    
    console.log('🔍 Full API Response:', JSON.stringify(data, null, 2));
    
    // Extract data safely - handle any possible structure
    let candidateName = 'Unknown Candidate';
    let candidateEmail = 'Not provided';
    let candidatePhone = 'Not provided';
    let candidateLinkedIn = 'Not provided';
    let candidateGitHub = 'Not provided';
    let currentRole = 'Not specified';
    let totalExperience = 0;
    let skills = [];
    let education = [];
    let certifications = [];
    let overallScore = 0;
    let skillScore = 0;
    let experienceScore = 0;
    let candidateRank = 'N/A';
    
    // Try multiple paths to extract candidate info
    try {
        // Try to get from structured_data first
        if (data?.resume_info?.structured_data) {
            const structured = data.resume_info.structured_data;
            candidateName = structured.name || candidateName;
            candidateEmail = structured.email || candidateEmail;
            candidatePhone = structured.phone || candidatePhone;
            candidateLinkedIn = structured.linkedin || candidateLinkedIn;
            candidateGitHub = structured.github || candidateGitHub;
            currentRole = structured.current_role || currentRole;
            totalExperience = structured.total_experience || totalExperience;
            skills = structured.skills || skills;
            education = structured.education || education;
            certifications = structured.certifications || certifications;
        }
        
        // Try to get from personal_info if it exists
        if (data?.resume_info?.personal_info) {
            const personal = data.resume_info.personal_info;
            candidateName = personal.name || candidateName;
            candidateEmail = personal.email || candidateEmail;
            candidatePhone = personal.phone || candidatePhone;
            candidateLinkedIn = personal.linkedin || candidateLinkedIn;
            candidateGitHub = personal.github || candidateGitHub;
        }
        
        // Try to get from professional_info if it exists
        if (data?.resume_info?.professional_info) {
            const professional = data.resume_info.professional_info;
            currentRole = professional.current_role || currentRole;
            totalExperience = professional.total_experience || totalExperience;
            skills = professional.skills || skills;
            education = professional.education || education;
            certifications = professional.certifications || certifications;
        }
        
        // Get matching scores
        if (data?.matching_analysis) {
            const matching = data.matching_analysis;
            overallScore = matching.overall_score || 0;
            skillScore = matching.skill_match_score || 0;
            experienceScore = matching.experience_score || 0;
            candidateRank = matching.rank || matching.rank_position || 'N/A';
        }
        
        // Fallback to filename if name is still unknown
        if (candidateName === 'Unknown Candidate' && data?.resume_info?.filename) {
            candidateName = data.resume_info.filename.replace('.pdf', '').replace(/_/g, ' ');
        }
        
    } catch (error) {
        console.error('Error extracting candidate data:', error);
    }
    
    modal.innerHTML = `
        <div class="candidate-modal">
            <div class="modal-header">
                <h2>Candidate Details</h2>
                <button class="modal-close" onclick="closeCandidateModal()">&times;</button>
            </div>
            
            <div class="modal-content">
                <!-- Personal Information -->
                <div class="info-section">
                    <h3>👤 Personal Information</h3>
                    <div class="info-grid">
                        <div class="info-item">
                            <strong>Name:</strong> ${candidateName}
                        </div>
                        <div class="info-item">
                            <strong>Email:</strong> 
                            ${candidateEmail !== 'Not provided' 
                                ? `<a href="mailto:${candidateEmail}">${candidateEmail}</a>`
                                : candidateEmail}
                        </div>
                        <div class="info-item">
                            <strong>Phone:</strong> 
                            ${candidatePhone !== 'Not provided' 
                                ? `<a href="tel:${candidatePhone}">${candidatePhone}</a>`
                                : candidatePhone}
                        </div>
                        <div class="info-item">
                            <strong>LinkedIn:</strong> 
                            ${candidateLinkedIn !== 'Not provided' 
                                ? `<a href="${candidateLinkedIn}" target="_blank">View Profile</a>`
                                : candidateLinkedIn}
                        </div>
                        <div class="info-item">
                            <strong>GitHub:</strong> 
                            ${candidateGitHub !== 'Not provided' 
                                ? `<a href="${candidateGitHub}" target="_blank">View Profile</a>`
                                : candidateGitHub}
                        </div>
                    </div>
                </div>

                <!-- Professional Information -->
                <div class="info-section">
                    <h3>💼 Professional Information</h3>
                    <div class="info-grid">
                        <div class="info-item">
                            <strong>Current Role:</strong> ${currentRole}
                        </div>
                        <div class="info-item">
                            <strong>Total Experience:</strong> ${totalExperience} years
                        </div>
                        <div class="info-item full-width">
                            <strong>Skills:</strong>
                            <div class="skills-list">
                                ${Array.isArray(skills) && skills.length > 0 ? 
                                    skills.map(skill => `<span class="skill-tag">${skill}</span>`).join('') : 
                                    '<span class="no-data">No skills information available</span>'}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Matching Analysis -->
                <div class="info-section">
                    <h3>📊 ATS Matching Analysis</h3>
                    <div class="matching-scores">
                        <div class="score-item">
                            <div class="score-label">Overall Score</div>
                            <div class="score-value overall">${overallScore}%</div>
                        </div>
                        <div class="score-item">
                            <div class="score-label">Skill Match</div>
                            <div class="score-value skill">${skillScore}%</div>
                        </div>
                        <div class="score-item">
                            <div class="score-label">Experience</div>
                            <div class="score-value experience">${experienceScore}%</div>
                        </div>
                        <div class="score-item">
                            <div class="score-label">Rank</div>
                            <div class="score-value rank">#${candidateRank}</div>
                        </div>
                    </div>
                </div>

                <!-- Education & Certifications -->
                <div class="info-section">
                    <h3>🎓 Education & Certifications</h3>
                    <div class="education-section">
                        <div class="education-item">
                            <strong>Education:</strong>
                            <ul>
                                ${Array.isArray(education) && education.length > 0 ? 
                                    education.map(edu => `<li>${edu}</li>`).join('') : 
                                    '<li>No education information available</li>'}
                            </ul>
                        </div>
                        <div class="education-item">
                            <strong>Certifications:</strong>
                            <ul>
                                ${Array.isArray(certifications) && certifications.length > 0 ? 
                                    certifications.map(cert => `<li>${cert}</li>`).join('') : 
                                    '<li>No certifications available</li>'}
                            </ul>
                        </div>
                    </div>
                </div>
                
                <!-- Debug Info -->
                <div class="info-section" style="background: #f5f5f5; padding: 10px; margin-top: 20px; font-size: 12px;">
                    <h4>Debug Information</h4>
                    <small>
                        <strong>API Response Structure:</strong><br>
                        Has resume_info: ${!!data?.resume_info}<br>
                        Has structured_data: ${!!data?.resume_info?.structured_data}<br>
                        Has personal_info: ${!!data?.resume_info?.personal_info}<br>
                        Has matching_analysis: ${!!data?.matching_analysis}<br>
                        <details>
                            <summary>Full Response (click to expand)</summary>
                            <pre style="font-size: 10px; max-height: 200px; overflow-y: auto;">${JSON.stringify(data, null, 2)}</pre>
                        </details>
                    </small>
                </div>
            </div>
            
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeCandidateModal()">Close</button>
                <button class="btn btn-primary" onclick="contactCandidate('${candidateEmail}')">Contact Candidate</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
} 

function closeCandidateModal() {
    const modal = document.querySelector('.candidate-modal-overlay');
    if (modal) {
        modal.remove();
        document.body.style.overflow = 'auto'; // Restore scrolling
    }
}

function contactCandidate(email) {
    if (email && email !== 'Not provided') {
        window.location.href = `mailto:${email}?subject=Job Opportunity - Software Engineer Position`;
    } else {
        Utils.showToast('Email not available for this candidate', 'warning');
    }
}

// FIXED: Legacy detailed analysis function - the main culprit
async function showDetailedAnalysis(resumeId) {
    try {
        Utils.showLoading('Loading detailed analysis...');
        
        const response = await Utils.makeRequest(`/api/matching/detailed/${appState.getSessionId()}/${resumeId}`);
        
        // Create modal for detailed analysis
        createDetailedAnalysisModal(response);
        
    } catch (error) {
        console.error('Error loading detailed analysis:', error);
        Utils.showToast(error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

// FIXED: This function was causing the error
function createDetailedAnalysisModal(data) {
    // Remove existing modal if any
    const existingModal = document.getElementById('detailed-modal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Create modal
    const modal = document.createElement('div');
    modal.id = 'detailed-modal';
    modal.className = 'modal-overlay';
    
    // SAFE data extraction with proper null checks
    const resumeInfo = data?.resume_info || {};
    const analysis = data?.matching_analysis || {};
    const detailedAnalysis = analysis?.detailed_analysis || {};
    
    const candidateName = resumeInfo?.structured_data?.name || resumeInfo?.filename || 'Unknown Candidate';
    const candidateEmail = resumeInfo?.structured_data?.email || 'Not detected';
    const totalExperience = resumeInfo?.structured_data?.total_experience || 0;
    
    // Safe skill breakdown extraction
    const skillBreakdown = detailedAnalysis?.skill_breakdown || {};
    const matchedSkills = skillBreakdown?.matched_skills || [];
    const missingSkills = skillBreakdown?.missing_skills || [];
    
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>Detailed Analysis - ${candidateName}</h3>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            
            <div class="modal-body">
                <div class="analysis-section">
                    <h4>Candidate Information</h4>
                    <div class="candidate-info">
                        <p><strong>File:</strong> ${resumeInfo?.filename || 'N/A'}</p>
                        <p><strong>Name:</strong> ${candidateName}</p>
                        <p><strong>Email:</strong> ${candidateEmail}</p>
                        <p><strong>Total Experience:</strong> ${totalExperience} years</p>
                    </div>
                </div>
                
                <div class="analysis-section">
                    <h4>Scoring Breakdown</h4>
                    <div class="score-breakdown">
                        <div class="score-item">
                            <span>Overall Score:</span>
                            <span class="score-badge">${analysis?.overall_score || 0}%</span>
                        </div>
                        <div class="score-item">
                            <span>Skill Match Score:</span>
                            <span class="score-badge">${analysis?.skill_match_score || 0}%</span>
                        </div>
                        <div class="score-item">
                            <span>Experience Score:</span>
                            <span class="score-badge">${analysis?.experience_score || 0}%</span>
                        </div>
                        <div class="score-item">
                            <span>Rank Position:</span>
                            <span class="rank-badge">#${analysis?.rank || analysis?.rank_position || 'N/A'}</span>
                        </div>
                    </div>
                </div>
                
                <div class="analysis-section">
                    <h4>Skills Analysis</h4>
                    <div class="skills-analysis">
                        <div class="matched-skills">
                            <h5>✅ Matched Skills (${matchedSkills.length})</h5>
                            <div class="skills-list">
                                ${matchedSkills.length > 0 
                                    ? matchedSkills.map(skill => `<span class="skill-tag matched">${skill}</span>`).join('') 
                                    : '<span class="no-data">No matched skills data available</span>'}
                            </div>
                        </div>
                        
                        <div class="missing-skills">
                            <h5>❌ Missing Skills (${missingSkills.length})</h5>
                            <div class="skills-list">
                                ${missingSkills.length > 0 
                                    ? missingSkills.map(skill => `<span class="skill-tag missing">${skill}</span>`).join('') 
                                    : '<span class="no-data">No missing skills data available</span>'}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeModal()">Close</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.style.display = 'flex';
}

function closeModal() {
    const modal = document.getElementById('detailed-modal');
    if (modal) {
        modal.remove();
    }
}

// Export functions
async function exportResults(format) {
    try {
        Utils.showLoading(`Exporting results as ${format.toUpperCase()}...`);
        
        const response = await Utils.makeRequest(`/api/matching/results/${appState.getSessionId()}`);
        const results = response.results;
        
        let exportData;
        let filename;
        let mimeType;
        
        if (format === 'csv') {
            exportData = convertToCSV(results);
            filename = `ats_results_${appState.getSessionId()}.csv`;
            mimeType = 'text/csv';
        } else if (format === 'json') {
            exportData = JSON.stringify(results, null, 2);
            filename = `ats_results_${appState.getSessionId()}.json`;
            mimeType = 'application/json';
        }
        
        // Create and trigger download
        const blob = new Blob([exportData], { type: mimeType });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        Utils.showToast(`Results exported as ${filename}`, 'success');
        
    } catch (error) {
        console.error('Error exporting results:', error);
        Utils.showToast('Error exporting results: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

function convertToCSV(results) {
    const headers = ['Rank', 'Candidate Name', 'Filename', 'Overall Score', 'Skill Match Score', 'Experience Score'];
    
    const rows = results.map(result => [
        result.rank,
        result.candidate_name || 'Unknown',
        result.filename,
        result.overall_score,
        result.skill_match_score,
        result.experience_score
    ]);
    
    const csvContent = [headers, ...rows].map(row => 
        row.map(field => `"${String(field).replace(/"/g, '""')}"`).join(',')
    ).join('\n');
    
    return csvContent;
}

// Global click handler for modal
document.addEventListener('click', function(event) {
    const modal = document.getElementById('detailed-modal');
    if (modal && event.target === modal) {
        closeModal();
    }
});

// Global click handler for candidate modal
document.addEventListener('click', function(event) {
    const modal = document.querySelector('.candidate-modal-overlay');
    if (modal && event.target === modal) {
        closeCandidateModal();
    }
});


// Add to the end of matcher.js file

// Interview Questions functionality
let currentInterviewQuestions = [];
let isGeneratingQuestions = false;

async function generateInterviewQuestions(regenerate = false) {
    if (isGeneratingQuestions) return;
    
    const sessionId = appState.getSessionId();
    if (!sessionId) {
        Utils.showToast('Please complete the matching process first', 'error');
        return;
    }
    
    try {
        isGeneratingQuestions = true;
        
        // Show loading state
        const loadingText = regenerate ? 'Regenerating interview questions...' : 'Generating interview questions...';
        Utils.showLoading(loadingText);
        
        // Update button states
        updateInterviewButtonStates(true);
        
        const response = await Utils.makeRequest(`/api/interview/generate-questions/${sessionId}?regenerate=${regenerate}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });


        
        currentInterviewQuestions = response.questions;
        displayInterviewQuestions(response);
        
        const action = regenerate ? 'regenerated' : 'generated';
        Utils.showToast(`Successfully ${action} ${response.total_questions} interview questions!`, 'success');
        
    } catch (error) {
        console.error('Error generating interview questions:', error);
        Utils.showToast(`Failed to generate interview questions: ${error.message}`, 'error');
    } finally {
        isGeneratingQuestions = false;
        updateInterviewButtonStates(false);
        Utils.hideLoading();
    }
}

function updateInterviewButtonStates(loading) {
    const generateBtn = document.getElementById('generate-questions-btn');
    const regenerateBtn = document.getElementById('regenerate-questions-btn');
    
    if (generateBtn) {
        generateBtn.disabled = loading;
        generateBtn.innerHTML = loading ? 
            '<i class="fas fa-spinner fa-spin"></i> Generating...' : 
            '<i class="fas fa-question-circle"></i> Interview Questions';
    }
    
    if (regenerateBtn) {
        regenerateBtn.disabled = loading;
        regenerateBtn.innerHTML = loading ? 
            '<i class="fas fa-spinner fa-spin"></i> Regenerating...' : 
            '<i class="fas fa-sync-alt"></i> Regenerate Questions';
    }
}

function displayInterviewQuestions(data) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('interview-questions-modal');
    if (!modal) {
        modal = createInterviewQuestionsModal();
        document.body.appendChild(modal);
    }
    
    // Update modal content
    const jobTitle = data.job_info.job_title || 'Unknown Position';
    const company = data.job_info.company || 'Company';
    const skillsList = [...(data.job_info.primary_skills || []), ...(data.job_info.secondary_skills || [])];
    
    // Update modal header
    document.getElementById('interview-modal-title').innerHTML = 
        `Interview Questions for ${jobTitle}`;
    
    document.getElementById('interview-job-info').innerHTML = `
        <div class="interview-job-details">
            <p><strong>Company:</strong> ${company}</p>
            <p><strong>Experience Required:</strong> ${data.job_info.experience_required}</p>
            <p><strong>Key Skills:</strong> ${skillsList.slice(0, 8).join(', ')}</p>
            <p><strong>Difficulty Level:</strong> ${data.difficulty_level}</p>
        </div>
    `;
    
    // Update questions list
    const questionsList = document.getElementById('interview-questions-list');
    questionsList.innerHTML = data.questions.map((question, index) => `
        <div class="interview-question-item">
            <div class="question-number">Q${index + 1}</div>
            <div class="question-text">${question}</div>
        </div>
    `).join('');
    
    // Update footer info
    document.getElementById('interview-questions-count').textContent = 
        `${data.total_questions} Questions Generated`;
    
    // Show modal
    modal.style.display = 'block';
}

function createInterviewQuestionsModal() {
    const modal = document.createElement('div');
    modal.id = 'interview-questions-modal';
    modal.className = 'modal interview-modal';
    
    modal.innerHTML = `
        <div class="modal-content interview-modal-content">
            <div class="modal-header">
                <h2 id="interview-modal-title">Interview Questions</h2>
                <span class="close" onclick="closeInterviewModal()">&times;</span>
            </div>
            
            <div class="modal-body">
                <div id="interview-job-info" class="interview-job-info"></div>
                
                <div class="interview-questions-container">
                    <div id="interview-questions-list" class="interview-questions-list"></div>
                </div>
                
                <div class="interview-actions">
                    <button id="regenerate-questions-btn" class="btn btn-secondary" onclick="generateInterviewQuestions(true)">
                        <i class="fas fa-sync-alt"></i> Regenerate Questions
                    </button>
                    <button class="btn btn-primary" onclick="exportInterviewQuestions()">
                        <i class="fas fa-download"></i> Export Questions
                    </button>
                </div>
            </div>
            
            <div class="modal-footer">
                <span id="interview-questions-count" class="questions-count"></span>
                <small class="text-muted">Questions generated using AI based on job requirements</small>
            </div>
        </div>
    `;
    
    return modal;
}

function closeInterviewModal() {
    const modal = document.getElementById('interview-questions-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function exportInterviewQuestions() {
    if (!currentInterviewQuestions || currentInterviewQuestions.length === 0) {
        Utils.showToast('No questions to export', 'error');
        return;
    }
    
    const sessionId = appState.getSessionId();
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
    
    // Create content for export
    const content = `Interview Questions - Session: ${sessionId}\nGenerated: ${new Date().toLocaleString()}\n\n` +
        currentInterviewQuestions.map((question, index) => 
            `Q${index + 1}: ${question}\n`
        ).join('\n');
    
    // Create and download file
    const blob = new Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `interview-questions-${timestamp}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
    
    Utils.showToast('Interview questions exported successfully!', 'success');
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('interview-questions-modal');
    if (event.target === modal) {
        closeInterviewModal();
    }
}


// History functionality
async function showHistory() {
    try {
        Utils.showLoading("Loading match history...");
        
        const response = await Utils.makeRequest('api/history/list');
        
        if (response.status === 'success') {
            displayHistoryModal(response.history);
        } else {
            Utils.showToast("No history found", "info");
        }
        
    } catch (error) {
        console.error("Error loading history:", error);
        Utils.showToast("Error loading history: " + error.message, "error");
    } finally {
        Utils.hideLoading();
    }
}

function displayHistoryModal(historyRecords) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.id = 'history-modal';
    
    let historyHTML = `
        <div class="modal-content" style="max-width: 1000px;">
            <div class="modal-header">
                <h3>Matching History</h3>
                <button class="modal-close" onclick="closeHistoryModal()">&times;</button>
            </div>
            <div class="modal-body">
                <p><strong>Total Records:</strong> ${historyRecords.length}</p>
    `;
    
    if (historyRecords.length === 0) {
        historyHTML += `<p>No matching history found. Complete some matches to see history here.</p>`;
    } else {
        historyHTML += `
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Job Title</th>
                        <th>Company</th>
                        <th>Total Resumes</th>
                        <th>Top Candidate</th>
                        <th>Top Score</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        historyRecords.forEach(record => {
            const date = new Date(record.completed_at).toLocaleDateString();
            historyHTML += `
                <tr>
                    <td>${date}</td>
                    <td>${record.job_title || 'Unknown Position'}</td>
                    <td>${record.company_name || 'Unknown Company'}</td>
                    <td>${record.total_resumes}</td>
                    <td>${record.top_candidate_name || 'Unknown'}</td>
                    <td><span class="score-badge">${record.top_candidate_score ? record.top_candidate_score.toFixed(1) : 'N/A'}</span></td>
                    <td>
                        <button class="btn btn-sm btn-primary" onclick="viewHistoryDetails('${record.session_id}')">
                            View Details
                        </button>
                    </td>
                </tr>
            `;
        });
        
        historyHTML += `
                </tbody>
            </table>
        `;
    }
    
    historyHTML += `
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeHistoryModal()">Close</button>
            </div>
        </div>
    `;
    
    modal.innerHTML = historyHTML;
    document.body.appendChild(modal);
    modal.style.display = 'flex';
}

async function viewHistoryDetails(sessionId) {
    try {
        Utils.showLoading("Loading session details...");
        
        const response = await Utils.makeRequest(`api/history/details/${sessionId}`);
        
        if (response.status === 'success') {
            // Store current session info for proper back navigation
            const currentSessionId = appState.getSessionId();
            
            // Close history modal first
            closeHistoryModal();
            
            // Display detailed results with proper back navigation
            const container = document.getElementById('results-content');
            displayHistoryResultsView(response.history_info, response.detailed_results, container, currentSessionId);
            
            // Switch to results section
            appState.currentStep = 5;
            appState.updateUI();
            
            Utils.showToast("Historical session loaded successfully!", "success");
        }
        
    } catch (error) {
        console.error("Error loading history details:", error);
        Utils.showToast("Error loading details: " + error.message, "error");
    } finally {
        Utils.hideLoading();
    }
}


function displayDetailedHistory(historyInfo, detailedResults, container) {
    let html = `
        <div class="results-summary">
            <h3>Historical Match Results</h3>
            <p><strong>Job:</strong> ${historyInfo.job_title} at ${historyInfo.company_name}</p>
            <p><strong>Date:</strong> ${new Date(historyInfo.completed_at).toLocaleString()}</p>
            <p><strong>Total Candidates:</strong> ${historyInfo.total_resumes}</p>
            <p><strong>Session ID:</strong> <code>${historyInfo.session_id}</code></p>
        </div>
        
        <div class="results-table-container">
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Candidate Name</th>
                        <th>Filename</th>
                        <th>Overall Score</th>
                        <th>Skill Match</th>
                        <th>Experience</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    detailedResults.forEach(result => {
        const overallScore = Utils.formatScore(result.overall_score);
        const skillScore = Utils.formatScore(result.skill_match_score);
        const expScore = Utils.formatScore(result.experience_score);
        
        html += `
            <tr class="result-row">
                <td><strong>${result.rank}</strong></td>
                <td>${result.candidate_name}</td>
                <td>${result.filename}</td>
                <td><span class="score-badge ${overallScore.class}">${overallScore.text}</span></td>
                <td><span class="score-badge ${skillScore.class}">${skillScore.text}</span></td>
                <td><span class="score-badge ${expScore.class}">${expScore.text}</span></td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
        
        <div class="export-buttons" style="margin-top: 20px; text-align: center;">
            <button class="btn btn-secondary" onclick="showHistory()">
                <i class="fas fa-arrow-left"></i> Back to History
            </button>
        </div>
    `;
    
    container.innerHTML = html;
}

function closeHistoryModal() {
    const modal = document.getElementById('history-modal');
    if (modal) {
        modal.remove();
    }
}



function displayHistoryResultsView(historyInfo, detailedResults, container, currentSessionId) {
    let html = `
        <div class="results-summary">
            <h3><i class="fas fa-history"></i> Historical Match Results</h3>
            <div class="history-info" style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <div class="history-details">
                    <div style="display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 15px;">
                        <div><strong>Job:</strong> ${historyInfo.job_title}</div>
                        <div><strong>Company:</strong> ${historyInfo.company_name}</div>
                        <div><strong>Date:</strong> ${new Date(historyInfo.completed_at).toLocaleString()}</div>
                        <div><strong>Total Candidates:</strong> ${historyInfo.total_resumes}</div>
                    </div>
                    <div><strong>Session ID:</strong> <code>${historyInfo.session_id}</code></div>
                </div>
            </div>
        </div>
        
        <div class="results-table-container">
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Candidate Name</th>
                        <th>Filename</th>
                        <th>Overall Score</th>
                        <th>Skill Match</th>
                        <th>Experience</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    detailedResults.forEach((result, index) => {
        // Fix ranking - use actual rank or index + 1
        const rank = result.rank_position || result.rank || (index + 1);
        
        // Format scores properly
        const overallScore = result.overall_score || 0;
        const skillScore = result.skill_match_score || 0;
        const expScore = result.experience_score || 0;
        
        // Format with proper percentage
        const formatScore = (score) => {
            if (score === null || score === undefined || isNaN(score)) {
                return { text: 'N/A', class: 'poor' };
            }
            const numScore = parseFloat(score);
            const text = numScore.toFixed(1) + '%';
            let className = 'poor';
            if (numScore >= 80) className = 'excellent';
            else if (numScore >= 60) className = 'good';
            else if (numScore >= 40) className = 'average';
            
            return { text, class: className };
        };
        
        const overallFormatted = formatScore(overallScore);
        const skillFormatted = formatScore(skillScore);
        const expFormatted = formatScore(expScore);
        
        // Status badge
        let statusClass = 'badge-danger';
        let statusText = 'Weak Match';
        if (overallScore >= 70) {
            statusClass = 'badge-success';
            statusText = 'Strong Match';
        } else if (overallScore >= 50) {
            statusClass = 'badge-warning';
            statusText = 'Good Match';
        }
        
        html += `
            <tr class="result-row">
                <td><strong>${rank}</strong></td>
                <td>${result.candidate_name || 'Unknown'}</td>
                <td>${result.filename}</td>
                <td><span class="score-badge ${overallFormatted.class}">${overallFormatted.text}</span></td>
                <td><span class="score-badge ${skillFormatted.class}">${skillFormatted.text}</span></td>
                <td><span class="score-badge ${expFormatted.class}">${expFormatted.text}</span></td>
                <td><span class="badge ${statusClass}">${statusText}</span></td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
        
        <div class="export-buttons" style="margin-top: 20px; text-align: center;">
            <button class="btn btn-warning" onclick="backToCurrentResults('${currentSessionId}')" style="margin-right: 10px;">
                <i class="fas fa-arrow-left"></i> Back to Current Results
            </button>
            <button class="btn btn-secondary" onclick="showHistory()" style="margin-right: 10px;">
                <i class="fas fa-history"></i> View All History
            </button>
            <button class="btn btn-info" onclick="exportHistoryResultsAsCSV('${historyInfo.session_id}')" style="margin-right: 10px;">
                <i class="fas fa-download"></i> Export as CSV
            </button>
            <button class="btn btn-primary" onclick="exportHistoryResultsAsJSON('${historyInfo.session_id}')">
                <i class="fas fa-download"></i> Export as JSON
            </button>
        </div>
    `;
    
    container.innerHTML = html;
}




// Auto-save to history when matching completes
async function saveMatchingToHistory(sessionId) {
    try {
        await Utils.makeRequest(`api/history/save/${sessionId}`, {
            method: 'POST'
        });
        console.log("Matching results saved to history");
    } catch (error) {
        console.error("Failed to save to history:", error);
        // Don't show error to user as this is background operation
    }
}


// Fix for Export Button Console Errors
function exportResultsAsCSV() {
    exportResults('csv');
}

function exportResultsAsJSON() {
    exportResults('json');
}

// Missing utility function for history
function getScoreClass(score) {
    if (!score) return 'poor';
    if (score >= 80) return 'excellent';
    if (score >= 60) return 'good'; 
    if (score >= 40) return 'average';
    return 'poor';
}



async function backToCurrentResults(currentSessionId) {
    if (!currentSessionId) {
        Utils.showToast("No current session found. Please start a new matching process.", "info");
        // Reset to first step
        appState.currentStep = 1;
        appState.updateUI();
        return;
    }
    
    try {
        Utils.showLoading("Loading current results...");
        
        // Load current session results
        const response = await Utils.makeRequest(`api/matching/results/${currentSessionId}`);
        
        if (response.results && response.results.length > 0) {
            // Display current results
            const container = document.getElementById('results-content');
            displayCurrentMatchingResults(response.results, currentSessionId, container);
            
            // Switch to results section
            appState.currentStep = 5;
            appState.updateUI();
            
            Utils.showToast("Returned to current matching results!", "success");
        } else {
            Utils.showToast("No current results found. Please start a new matching process.", "info");
            appState.currentStep = 1;
            appState.updateUI();
        }
        
    } catch (error) {
        console.error("Error loading current results:", error);
        Utils.showToast("Error loading current results. Starting fresh.", "warning");
        appState.currentStep = 1;
        appState.updateUI();
    } finally {
        Utils.hideLoading();
    }
}



function displayCurrentMatchingResults(results, sessionId, container) {
    let html = `
        <div class="results-summary">
            <h3>Current ATS Matching Results</h3>
            <p><strong>Total Candidates Processed:</strong> ${results.length}</p>
            <p><strong>Session ID:</strong> <code>${sessionId}</code></p>
        </div>
        
        <div class="results-table-container">
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Candidate Name</th>
                        <th>Filename</th>
                        <th>Overall Score</th>
                        <th>Skill Match</th>
                        <th>Experience</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    results.forEach((result) => {
        const overallScore = Utils.formatScore(result.overall_score);
        const skillScore = Utils.formatScore(result.skill_match_score);
        const expScore = Utils.formatScore(result.experience_score);
        
        html += `
            <tr class="result-row" data-resume-id="${result.resume_id}">
                <td><strong>${result.rank}</strong></td>
                <td>${result.candidate_name || 'Unknown'}</td>
                <td>${result.filename}</td>
                <td><span class="score-badge ${overallScore.class}">${overallScore.text}</span></td>
                <td><span class="score-badge ${skillScore.class}">${skillScore.text}</span></td>
                <td><span class="score-badge ${expScore.class}">${expScore.text}</span></td>
                <td>
                    <button class="btn btn-sm btn-primary" 
                            data-resume-id="${result.resume_id}" 
                            data-session-id="${sessionId}"
                            onclick="showCandidateDetails('${sessionId}', '${result.resume_id}')">
                        View Details
                    </button>
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
        
        <!-- Current session export buttons -->
        <div class="export-buttons" style="margin-top: 20px; text-align: center;">
            <button id="generate-questions-btn" class="btn btn-success" onclick="generateInterviewQuestions(false)" style="margin-right: 10px;">
                <i class="fas fa-question-circle"></i> Interview Questions
            </button>
            <button class="btn btn-secondary" onclick="exportResultsAsCSV()" style="margin-right: 10px;">
                <i class="fas fa-download"></i> Export as CSV
            </button>
            <button class="btn btn-info" onclick="exportResultsAsJSON()" style="margin-right: 10px;">
                <i class="fas fa-download"></i> Export as JSON
            </button>
            <button class="btn btn-warning" onclick="showHistory()" style="margin-right: 10px;">
                <i class="fas fa-history"></i> History
            </button>
            <button class="btn btn-primary" onclick="startNewMatching()">
                <i class="fas fa-redo"></i> Start New Matching
            </button>
        </div>
    `;
    
    container.innerHTML = html;
}



async function exportHistoryResultsAsCSV(sessionId) {
    try {
        Utils.showLoading("Exporting historical results as CSV...");
        
        const response = await Utils.makeRequest(`api/history/details/${sessionId}`);
        const results = response.detailed_results;
        
        const headers = ['Rank', 'Candidate Name', 'Filename', 'Overall Score', 'Skill Match Score', 'Experience Score'];
        const rows = results.map(result => [
            result.rank_position || result.rank || 'N/A',
            result.candidate_name || 'Unknown',
            result.filename,
            result.overall_score || 0,
            result.skill_match_score || 0,
            result.experience_score || 0
        ]);
        
        const csvContent = [headers, ...rows.map(row => 
            row.map(field => String(field).replace(/"/g, '""')).join(',')
        )].join('\n');
        
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ats-history-results-${sessionId}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        Utils.showToast(`Historical results exported as CSV!`, "success");
        
    } catch (error) {
        console.error("Error exporting historical results:", error);
        Utils.showToast("Error exporting historical results: " + error.message, "error");
    } finally {
        Utils.hideLoading();
    }
}

async function exportHistoryResultsAsJSON(sessionId) {
    try {
        Utils.showLoading("Exporting historical results as JSON...");
        
        const response = await Utils.makeRequest(`api/history/details/${sessionId}`);
        
        const exportData = {
            session_info: response.history_info,
            detailed_results: response.detailed_results,
            exported_at: new Date().toISOString()
        };
        
        const jsonContent = JSON.stringify(exportData, null, 2);
        
        const blob = new Blob([jsonContent], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ats-history-results-${sessionId}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        Utils.showToast(`Historical results exported as JSON!`, "success");
        
    } catch (error) {
        console.error("Error exporting historical results:", error);
        Utils.showToast("Error exporting historical results: " + error.message, "error");
    } finally {
        Utils.hideLoading();
    }
}


/**
 * Reset the application state and start a new matching session
 */
async function startNewMatching() {
    // Confirm with user before resetting
    const confirmed = confirm(
        'Are you sure you want to start a new matching session? This will reset the current workflow.'
    );
    
    if (!confirmed) {
        return;
    }
    
    try {
        Utils.showLoading('Preparing new matching session...');
        
        // Clear current session data
        appState.currentStep = 1;
        appState.sessionId = null;
        appState.jdData = null;
        appState.matchingResults = null;
        
        // Clear UI elements
        document.getElementById('jd-file').value = '';
        document.getElementById('jd-text').value = '';
        document.getElementById('resume-files').value = '';
        document.getElementById('results-content').innerHTML = '';
        document.getElementById('selected-files-list').innerHTML = '';
        
        // Reset buttons
        document.getElementById('process-jd-btn').disabled = true;
        document.getElementById('upload-resumes-btn').disabled = true;
        document.getElementById('start-matching-btn').disabled = false;
        
        // Update UI to show step 1
        appState.updateUI();
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        Utils.showToast('Ready to start a new matching session!', 'success');
        
    } catch (error) {
        console.error('Error starting new matching:', error);
        Utils.showToast('Error resetting session: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

// Make function globally available
window.startNewMatching = startNewMatching;
