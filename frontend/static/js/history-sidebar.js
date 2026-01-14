// ============================================================================
// HISTORY SIDEBAR - FIXED VERSION
// ============================================================================
// Shows history list in sidebar
// Opens modal to view details (NOT direct navigation to Step 5)
// ============================================================================

// Load history sidebar on page load
document.addEventListener('DOMContentLoaded', function() {
    loadHistorySidebar();
});

/**
 * Load and display history in the sidebar
 */
async function loadHistorySidebar() {
    const container = document.getElementById('history-sidebar-content');
    if (!container) return;

    try {
        container.innerHTML = '<p class="loading-text">Loading history...</p>';
        
        const response = await Utils.makeRequest('/api/history/list');
        
        if (response.status === 'success' && response.history && response.history.length > 0) {
            displayHistorySidebar(response.history);
        } else {
            container.innerHTML = `
                <div class="no-history">
                    <p>📋 No matching history found</p>
                    <small>Complete a matching session to see history here</small>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading history sidebar:', error);
        container.innerHTML = `
            <div class="error-message">
                <p>⚠️ Failed to load history</p>
                <button class="btn btn-sm btn-secondary" onclick="loadHistorySidebar()">Retry</button>
            </div>
        `;
    }
}

/**
 * Display history records in sidebar
 */
function displayHistorySidebar(historyRecords) {
    const container = document.getElementById('history-sidebar-content');
    if (!container) return;

    let html = '';

    // Sort by date (most recent first)
    const sortedRecords = historyRecords.sort((a, b) => {
        return new Date(b.completed_at) - new Date(a.completed_at);
    });

    // Display only the 10 most recent records
    const recentRecords = sortedRecords.slice(0, 10);

    recentRecords.forEach((record) => {
        const date = new Date(record.completed_at);
        const formattedDate = date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric',
            year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
        });
        const formattedTime = date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });

        const jobTitle = record.job_title || 'Unknown Position';
        const companyName = record.company_name || 'Unknown Company';
        const topScore = record.top_candidate_score ? record.top_candidate_score.toFixed(1) : 'N/A';
        const totalResumes = record.total_resumes || 0;

        // Determine score badge class
        let scoreBadgeClass = 'score-poor';
        if (topScore !== 'N/A') {
            const score = parseFloat(topScore);
            if (score >= 80) scoreBadgeClass = 'score-excellent';
            else if (score >= 60) scoreBadgeClass = 'score-good';
            else if (score >= 40) scoreBadgeClass = 'score-average';
        }

        html += `
            <div class="history-item" onclick="viewHistoryDetailsModal('${record.session_id}')">
                <div class="history-item-header">
                    <strong class="history-job-title">${jobTitle}</strong>
                    <span class="score-badge ${scoreBadgeClass}">${topScore}%</span>
                </div>
                <div class="history-item-details">
                    <span class="history-company">🏢 ${companyName}</span>
                    <span class="history-resumes">📄 ${totalResumes} resumes</span>
                </div>
                <div class="history-item-footer">
                    <span class="history-date">📅 ${formattedDate} at ${formattedTime}</span>
                </div>
            </div>
        `;
    });

    // Add "View All" button if there are more records
    if (historyRecords.length > 10) {
        html += `
            <div class="history-view-all">
                <button class="btn btn-sm btn-secondary" onclick="showFullHistoryModal()">
                    View All (${historyRecords.length}) →
                </button>
            </div>
        `;
    }

    container.innerHTML = html;
}

/**
 * 🔥 FIXED: View history details in MODAL (not direct Step 5 navigation)
 */
async function viewHistoryDetailsModal(sessionId) {
    try {
        Utils.showLoading('Loading session details...');
        
        const response = await Utils.makeRequest(`/api/history/details/${sessionId}`);
        
        if (response.status === 'success') {
            // Show details in modal instead of navigating
            displayHistoryDetailsModal(response.history_info, response.detailed_results);
            Utils.showToast('Historical session loaded!', 'success');
        }
    } catch (error) {
        console.error('Error loading history details:', error);
        Utils.showToast(`Error loading details: ${error.message}`, 'error');
    } finally {
        Utils.hideLoading();
    }
}

/**
 * 🔥 NEW: Display history details in modal popup
 */
function displayHistoryDetailsModal(historyInfo, detailedResults) {
    // Create modal
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.id = 'history-details-modal';
    
    let html = `
        <div class="modal-content" style="max-width: 1200px; width: 95%;">
            <div class="modal-header">
                <h3>📊 Historical Matching Session</h3>
                <button class="modal-close" onclick="closeHistoryDetailsModal()">&times;</button>
            </div>
            
            <div class="modal-body">
                <!-- Session Info -->
                <div class="history-session-info" style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 25px;">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px;">
                        <div>
                            <strong style="color: #666; font-size: 13px; display: block; margin-bottom: 5px;">Job Title</strong>
                            <span style="color: #333; font-size: 16px; font-weight: 600;">${historyInfo.job_title}</span>
                        </div>
                        <div>
                            <strong style="color: #666; font-size: 13px; display: block; margin-bottom: 5px;">Company</strong>
                            <span style="color: #333; font-size: 16px;">${historyInfo.company_name}</span>
                        </div>
                        <div>
                            <strong style="color: #666; font-size: 13px; display: block; margin-bottom: 5px;">Date</strong>
                            <span style="color: #333; font-size: 16px;">${new Date(historyInfo.completed_at).toLocaleDateString()}</span>
                        </div>
                        <div>
                            <strong style="color: #666; font-size: 13px; display: block; margin-bottom: 5px;">Total Candidates</strong>
                            <span style="color: #333; font-size: 16px; font-weight: 600;">${historyInfo.total_resumes}</span>
                        </div>
                    </div>
                    <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid #dee2e6;">
                        <strong style="color: #666; font-size: 12px;">Session ID:</strong>
                        <code style="background: #e9ecef; padding: 4px 8px; border-radius: 4px; font-size: 11px;">${historyInfo.session_id}</code>
                    </div>
                </div>
                
                <!-- Results Table -->
                <div class="results-table-container">
                    <h4 style="margin-bottom: 15px; color: #333;">Matching Results</h4>
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
        const rank = result.rank_position || result.rank || (index + 1);
        const overallScore = result.overall_score || 0;
        const skillScore = result.skill_match_score || 0;
        const expScore = result.experience_score || 0;
        
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
            <tr>
                <td><strong>#${rank}</strong></td>
                <td>${result.candidate_name || 'Unknown'}</td>
                <td>${result.filename}</td>
                <td><span class="score-badge score-${overallFormatted.class}">${overallFormatted.text}</span></td>
                <td><span class="score-badge score-${skillFormatted.class}">${skillFormatted.text}</span></td>
                <td><span class="score-badge score-${expFormatted.class}">${expFormatted.text}</span></td>
                <td><span style="padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; background: ${statusClass === 'badge-success' ? '#d4edda' : statusClass === 'badge-warning' ? '#fff3cd' : '#f8d7da'}; color: ${statusClass === 'badge-success' ? '#155724' : statusClass === 'badge-warning' ? '#856404' : '#721c24'};">${statusText}</span></td>
            </tr>
        `;
    });
    
    html += `
                        </tbody>
                    </table>
                </div>
            </div>
            
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeHistoryDetailsModal()">Close</button>
                <button class="btn btn-info" onclick="exportHistoryAsCSV('${historyInfo.session_id}')">
                    📥 Export as CSV
                </button>
                <button class="btn btn-primary" onclick="exportHistoryAsJSON('${historyInfo.session_id}')">
                    📥 Export as JSON
                </button>
            </div>
        </div>
    `;
    
    modal.innerHTML = html;
    document.body.appendChild(modal);
    modal.style.display = 'flex';
}

/**
 * Close history details modal
 */
function closeHistoryDetailsModal() {
    const modal = document.getElementById('history-details-modal');
    if (modal) {
        modal.remove();
    }
}

/**
 * Show full history modal (all records)
 */
function showFullHistoryModal() {
    if (typeof showHistory === 'function') {
        showHistory();
    } else {
        Utils.showToast('History modal function not found', 'error');
    }
}

/**
 * Export history as CSV
 */
async function exportHistoryAsCSV(sessionId) {
    try {
        Utils.showLoading("Exporting as CSV...");
        
        const response = await Utils.makeRequest(`/api/history/details/${sessionId}`);
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
            row.map(field => `"${String(field).replace(/"/g, '""')}"`).join(',')
        )].join('\n');
        
        const blob = new Blob([csvContent], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `history-${sessionId}-${Date.now()}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        Utils.showToast('Exported successfully!', 'success');
    } catch (error) {
        console.error("Error exporting:", error);
        Utils.showToast("Export failed: " + error.message, "error");
    } finally {
        Utils.hideLoading();
    }
}

/**
 * Export history as JSON
 */
async function exportHistoryAsJSON(sessionId) {
    try {
        Utils.showLoading("Exporting as JSON...");
        
        const response = await Utils.makeRequest(`/api/history/details/${sessionId}`);
        
        const exportData = {
            session_info: response.history_info,
            detailed_results: response.detailed_results,
            exported_at: new Date().toISOString()
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `history-${sessionId}-${Date.now()}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        Utils.showToast('Exported successfully!', 'success');
    } catch (error) {
        console.error("Error exporting:", error);
        Utils.showToast("Export failed: " + error.message, "error");
    } finally {
        Utils.hideLoading();
    }
}

/**
 * Refresh history sidebar
 */
window.refreshHistorySidebar = function() {
    loadHistorySidebar();
};

// Make functions globally available
window.loadHistorySidebar = loadHistorySidebar;
window.viewHistoryDetailsModal = viewHistoryDetailsModal;
window.closeHistoryDetailsModal = closeHistoryDetailsModal;
window.showFullHistoryModal = showFullHistoryModal;
window.exportHistoryAsCSV = exportHistoryAsCSV;
window.exportHistoryAsJSON = exportHistoryAsJSON;