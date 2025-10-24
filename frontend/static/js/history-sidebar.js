// history-sidebar.js - Handles the history sidebar in Step 1

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

    recentRecords.forEach((record, index) => {
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

        // Fixed: Use underscore format (job_title, company_name, etc.)
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
            <div class="history-item" onclick="viewHistoryFromSidebar('${record.session_id}')">
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
                <button class="btn btn-sm btn-secondary" onclick="showFullHistory()">
                    View All (${historyRecords.length}) →
                </button>
            </div>
        `;
    }

    container.innerHTML = html;
}

/**
 * View history details from sidebar
 */
async function viewHistoryFromSidebar(sessionId) {
    try {
        Utils.showLoading('Loading session details...');
        
        const response = await Utils.makeRequest(`/api/history/details/${sessionId}`);
        
        if (response.status === 'success') {
            // Store current session info
            const currentSessionId = appState.getSessionId();
            
            // Display historical results
            const container = document.getElementById('results-content');
            displayHistoryResultsView(response.history_info, response.detailed_results, container, currentSessionId);
            
            // Switch to results section
            appState.currentStep = 5;
            appState.updateUI();
            
            Utils.showToast('Historical session loaded successfully!', 'success');
        }
    } catch (error) {
        console.error('Error loading history details:', error);
        Utils.showToast(`Error loading details: ${error.message}`, 'error');
    } finally {
        Utils.hideLoading();
    }
}

/**
 * Show full history modal (reuses existing function from matcher.js)
 */
function showFullHistory() {
    if (typeof showHistory === 'function') {
        showHistory();
    } else {
        Utils.showToast('History modal function not found', 'error');
    }
}

/**
 * Refresh history sidebar
 */
window.refreshHistorySidebar = function() {
    loadHistorySidebar();
};
