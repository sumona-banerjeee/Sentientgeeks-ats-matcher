class HistoryManager {
    constructor() {
        this.currentSession = null;
        this.historyData = [];
        this.isLoading = false;
    }

    async loadAllSessions() {
        try {
            this.showLoading();
            const response = await fetch('/api/history/sessions');
            const data = await response.json();
            
            this.displaySessionsList(data.sessions);
            return data;
        } catch (error) {
            console.error('Error loading sessions:', error);
            Utils.showToast('Error loading sessions', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async loadSessionDetails(sessionId) {
        try {
            this.showLoading();
            const response = await fetch(`/api/history/session/${sessionId}`);
            const data = await response.json();
            
            this.currentSession = data;
            this.displaySessionDetails(data);
            return data;
        } catch (error) {
            console.error('Error loading session details:', error);
            Utils.showToast('Error loading session details', 'error');
        } finally {
            this.hideLoading();
        }
    }

    displaySessionsList(sessions) {
        const container = document.getElementById('sessions-list');
        if (!container) return;

        let html = `
            <div class="sessions-header">
                <h3>ATS Matching History</h3>
                <div class="sessions-stats">
                    <span class="stat-item">Total Sessions: ${sessions.length}</span>
                </div>
            </div>
            <div class="sessions-grid">
        `;

        sessions.forEach(session => {
            const statusClass = session.status === 'completed' ? 'completed' : 'active';
            const formattedDate = new Date(session.created_at).toLocaleDateString();
            
            html += `
                <div class="session-card ${statusClass}" onclick="historyManager.loadSessionDetails('${session.session_id}')">
                    <div class="session-header">
                        <h4>${session.session_name || `Session ${session.session_id.substring(0, 8)}`}</h4>
                        <span class="session-status ${statusClass}">${session.status}</span>
                    </div>
                    <div class="session-info">
                        <p><strong>JD:</strong> ${session.jd_title || 'N/A'}</p>
                        <p><strong>Resumes:</strong> ${session.processed_resumes}/${session.total_resumes}</p>
                        <p><strong>Date:</strong> ${formattedDate}</p>
                    </div>
                    <div class="session-actions">
                        <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); historyManager.exportSession('${session.session_id}', 'json')">
                            Export JSON
                        </button>
                        <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); historyManager.exportSession('${session.session_id}', 'csv')">
                            Export CSV
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); historyManager.deleteSession('${session.session_id}')">
                            Delete
                        </button>
                    </div>
                </div>
            `;
        });

        html += '</div>';
        container.innerHTML = html;
    }

    displaySessionDetails(sessionData) {
        const container = document.getElementById('session-details');
        if (!container) return;

        const session = sessionData.session;
        const history = sessionData.history;
        const results = sessionData.results;

        let html = `
            <div class="session-detail-header">
                <button class="btn btn-secondary" onclick="historyManager.loadAllSessions()">← Back to Sessions</button>
                <h3>${session.session_name || `Session ${session.session_id.substring(0, 8)}`}</h3>
                <div class="session-actions">
                    <button class="btn btn-primary" onclick="historyManager.exportSession('${session.session_id}', 'json')">
                        Export JSON
                    </button>
                    <button class="btn btn-secondary" onclick="historyManager.exportSession('${session.session_id}', 'csv')">
                        Export CSV
                    </button>
                    <button class="btn btn-danger" onclick="historyManager.deleteSessionHistory('${session.session_id}')">
                        Clear History
                    </button>
                    <button class="btn btn-danger" onclick="historyManager.deleteSession('${session.session_id}')">
                        Delete Session
                    </button>
                </div>
            </div>

            <div class="session-overview">
                <div class="overview-card">
                    <h4>Session Overview</h4>
                    <div class="overview-stats">
                        <div class="stat">
                            <span class="stat-label">JD Title:</span>
                            <span class="stat-value">${session.jd_title || 'N/A'}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Total Resumes:</span>
                            <span class="stat-value">${session.total_resumes}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Processed:</span>
                            <span class="stat-value">${session.processed_resumes}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Status:</span>
                            <span class="stat-value status-${session.status}">${session.status}</span>
                        </div>
                        <div class="stat">
                            <span class="stat-label">Created:</span>
                            <span class="stat-value">${new Date(session.created_at).toLocaleString()}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="session-tabs">
                <button class="tab-button active" onclick="historyManager.showTab('results')">Results</button>
                <button class="tab-button" onclick="historyManager.showTab('history')">Activity History</button>
                <button class="tab-button" onclick="historyManager.showTab('analytics')">Analytics</button>
            </div>

            <div id="results-tab" class="tab-content active">
                ${this.generateResultsHTML(results)}
            </div>

            <div id="history-tab" class="tab-content">
                ${this.generateHistoryHTML(history)}
            </div>

            <div id="analytics-tab" class="tab-content">
                ${this.generateAnalyticsHTML(results)}
            </div>
        `;

        container.innerHTML = html;
        
        // Show session details and hide sessions list
        document.getElementById('sessions-list').style.display = 'none';
        container.style.display = 'block';
    }

    generateResultsHTML(results) {
        if (!results || results.length === 0) {
            return '<p class="no-data">No results found for this session.</p>';
        }

        let html = `
            <div class="results-header">
                <h4>Matching Results (${results.length} resumes)</h4>
            </div>
            <div class="results-table">
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Resume ID</th>
                            <th>Overall Score</th>
                            <th>Skill Match</th>
                            <th>Experience</th>
                            <th>Date</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        results.forEach(result => {
            html += `
                <tr>
                    <td><span class="rank-badge">#${result.rank_position}</span></td>
                    <td>Resume ${result.resume_id}</td>
                    <td><span class="score-badge overall">${(result.overall_score * 100).toFixed(1)}%</span></td>
                    <td><span class="score-badge skill">${(result.skill_match_score * 100).toFixed(1)}%</span></td>
                    <td><span class="score-badge experience">${(result.experience_score * 100).toFixed(1)}%</span></td>
                    <td>${new Date(result.created_at).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-info" onclick="historyManager.showResultDetails(${result.id})">
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
        `;

        return html;
    }

    generateHistoryHTML(history) {
        if (!history || history.length === 0) {
            return '<p class="no-data">No activity history found for this session.</p>';
        }

        let html = `
            <div class="history-header">
                <h4>Activity History (${history.length} actions)</h4>
            </div>
            <div class="history-timeline">
        `;

        history.forEach(action => {
            const iconClass = this.getActionIcon(action.action_type);
            const statusClass = action.success ? 'success' : 'error';

            html += `
                <div class="history-item ${statusClass}">
                    <div class="history-icon">
                        <i class="${iconClass}"></i>
                    </div>
                    <div class="history-content">
                        <div class="history-header">
                            <span class="action-type">${action.action_type.replace('_', ' ').toUpperCase()}</span>
                            <span class="timestamp">${new Date(action.timestamp).toLocaleString()}</span>
                        </div>
                        <p class="action-description">${action.action_description}</p>
                        ${action.execution_time ? `<small>Execution time: ${action.execution_time.toFixed(2)}s</small>` : ''}
                        ${action.error_message ? `<div class="error-message">${action.error_message}</div>` : ''}
                    </div>
                </div>
            `;
        });

        html += '</div>';
        return html;
    }

    generateAnalyticsHTML(results) {
        if (!results || results.length === 0) {
            return '<p class="no-data">No analytics data available.</p>';
        }

        // Calculate analytics
        const totalResults = results.length;
        const avgOverall = results.reduce((sum, r) => sum + r.overall_score, 0) / totalResults;
        const avgSkill = results.reduce((sum, r) => sum + r.skill_match_score, 0) / totalResults;
        const avgExperience = results.reduce((sum, r) => sum + r.experience_score, 0) / totalResults;

        const topScore = Math.max(...results.map(r => r.overall_score));
        const lowScore = Math.min(...results.map(r => r.overall_score));

        return `
            <div class="analytics-container">
                <div class="analytics-grid">
                    <div class="analytics-card">
                        <h5>Overall Performance</h5>
                        <div class="metric">
                            <span class="metric-label">Average Score:</span>
                            <span class="metric-value">${(avgOverall * 100).toFixed(1)}%</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Highest Score:</span>
                            <span class="metric-value">${(topScore * 100).toFixed(1)}%</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Lowest Score:</span>
                            <span class="metric-value">${(lowScore * 100).toFixed(1)}%</span>
                        </div>
                    </div>
                    
                    <div class="analytics-card">
                        <h5>Score Breakdown</h5>
                        <div class="metric">
                            <span class="metric-label">Avg Skill Match:</span>
                            <span class="metric-value">${(avgSkill * 100).toFixed(1)}%</span>
                        </div>
                        <div class="metric">
                            <span class="metric-label">Avg Experience:</span>
                            <span class="metric-value">${(avgExperience * 100).toFixed(1)}%</span>
                        </div>
                    </div>
                    
                    <div class="analytics-card">
                        <h5>Distribution</h5>
                        <div class="score-distribution">
                            ${this.generateScoreDistribution(results)}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    generateScoreDistribution(results) {
        const ranges = [
            { min: 0.9, max: 1.0, label: '90-100%', class: 'excellent' },
            { min: 0.8, max: 0.9, label: '80-89%', class: 'good' },
            { min: 0.7, max: 0.8, label: '70-79%', class: 'average' },
            { min: 0.6, max: 0.7, label: '60-69%', class: 'below' },
            { min: 0, max: 0.6, label: 'Below 60%', class: 'poor' }
        ];

        let html = '';
        ranges.forEach(range => {
            const count = results.filter(r => 
                r.overall_score >= range.min && r.overall_score < range.max
            ).length;
            const percentage = (count / results.length * 100).toFixed(1);

            html += `
                <div class="distribution-item ${range.class}">
                    <span class="range-label">${range.label}</span>
                    <div class="bar-container">
                        <div class="bar" style="width: ${percentage}%"></div>
                    </div>
                    <span class="count">${count} (${percentage}%)</span>
                </div>
            `;
        });

        return html;
    }

    getActionIcon(actionType) {
        const icons = {
            'jd_upload': 'fas fa-upload',
            'jd_structure': 'fas fa-cogs',
            'resume_upload': 'fas fa-file-upload',
            'matching_complete': 'fas fa-check-circle',
            'result_view': 'fas fa-eye',
            'export': 'fas fa-download'
        };
        return icons[actionType] || 'fas fa-info-circle';
    }

    showTab(tabName) {
        // Hide all tabs
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.remove('active');
        });
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
        });

        // Show selected tab
        document.getElementById(`${tabName}-tab`).classList.add('active');
        event.target.classList.add('active');
    }

    async exportSession(sessionId, format) {
        try {
            this.showLoading();
            const response = await fetch(`/api/history/session/${sessionId}/export/${format}`);
            
            if (!response.ok) {
                throw new Error('Export failed');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = `${sessionId}_results.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            Utils.showToast(`${format.toUpperCase()} exported successfully`, 'success');

            // Log the export action
            await this.logAction(sessionId, {
                action_type: 'export',
                description: `Exported session data as ${format.toUpperCase()}`,
                details: { format, timestamp: new Date().toISOString() }
            });

        } catch (error) {
            console.error('Export error:', error);
            Utils.showToast('Export failed', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async deleteSession(sessionId) {
        if (!confirm('Are you sure you want to delete this entire session? This action cannot be undone.')) {
            return;
        }

        try {
            this.showLoading();
            const response = await fetch(`/api/history/session/${sessionId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Delete failed');
            }

            Utils.showToast('Session deleted successfully', 'success');
            
            // Reload sessions list
            await this.loadAllSessions();
            
            // Hide session details if currently viewing this session
            if (this.currentSession && this.currentSession.session.session_id === sessionId) {
                document.getElementById('session-details').style.display = 'none';
                document.getElementById('sessions-list').style.display = 'block';
            }

        } catch (error) {
            console.error('Delete error:', error);
            Utils.showToast('Failed to delete session', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async deleteSessionHistory(sessionId) {
        if (!confirm('Are you sure you want to delete the activity history for this session? The results will remain.')) {
            return;
        }

        try {
            this.showLoading();
            const response = await fetch(`/api/history/session/${sessionId}/history`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Delete history failed');
            }

            Utils.showToast('Session history cleared successfully', 'success');
            
            // Reload session details
            await this.loadSessionDetails(sessionId);

        } catch (error) {
            console.error('Delete history error:', error);
            Utils.showToast('Failed to delete session history', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async logAction(sessionId, actionData) {
        try {
            await fetch(`/api/history/session/${sessionId}/log`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(actionData)
            });
        } catch (error) {
            console.error('Failed to log action:', error);
        }
    }

    showLoading() {
        this.isLoading = true;
        const loader = document.getElementById('history-loading');
        if (loader) loader.style.display = 'flex';
    }

    hideLoading() {
        this.isLoading = false;
        const loader = document.getElementById('history-loading');
        if (loader) loader.style.display = 'none';
    }

    showResultDetails(resultId) {
        // Implementation for showing detailed result analysis
        console.log('Show result details for:', resultId);
    }
}

// Initialize history manager
const historyManager = new HistoryManager();

// Auto-load sessions when history page is opened
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('sessions-list')) {
        historyManager.loadAllSessions();
    }
});
