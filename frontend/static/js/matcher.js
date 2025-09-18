// Matching and results functions

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
                    </tbody>
                </table>
            </div>

            <div class="export-options">
                <button class="btn btn-secondary" onclick="exportResults('csv')">Export as CSV</button>
                <button class="btn btn-secondary" onclick="exportResults('json')">Export as JSON</button>
            </div>
        `;

        container.innerHTML = html;

        // Add click handlers for row selection
        document.querySelectorAll('.result-row').forEach(row => {
            row.addEventListener('click', function () {
                // Remove previous selection
                document.querySelectorAll('.result-row.selected').forEach(r => r.classList.remove('selected'));
                // Add selection to clicked row
                this.classList.add('selected');
            });
        });

        // Add click handlers for "View Details" buttons
        container.querySelectorAll('button.btn-primary').forEach(button => {
            button.addEventListener('click', (event) => {
                event.stopPropagation(); // Prevent row selection on button click
                const resumeId = button.getAttribute('data-resume-id');
                const sessionId = button.getAttribute('data-session-id');
                
                // Call showCandidateDetails
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
