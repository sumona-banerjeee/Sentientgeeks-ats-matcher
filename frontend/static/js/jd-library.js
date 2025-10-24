// JD Library Management - Frontend

/**
 * Show JD Library Modal
 */
async function showJDLibrary() {
    try {
        Utils.showLoading('Loading JD Library...');
        
        const response = await Utils.makeRequest('/api/jd-library/list');
        
        if (response.status === 'success') {
            displayJDLibraryModal(response.jds, response.user_role);
        } else {
            Utils.showToast('No JDs found in library', 'info');
        }
        
    } catch (error) {
        console.error('Error loading JD library:', error);
        Utils.showToast('Error loading JD library: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

/**
 * Display JD Library Modal
 */
function displayJDLibraryModal(jds, userRole) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.id = 'jd-library-modal';
    
    let jdsHTML = '';
    
    if (jds.length === 0) {
        jdsHTML = `
            <div style="text-align: center; padding: 40px; color: #999;">
                <p style="font-size: 18px; margin-bottom: 10px;">📚 No JDs in library</p>
                <p>Save a processed JD to reuse it later</p>
            </div>
        `;
    } else {
        jdsHTML = `
            <div class="jd-library-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin-top: 20px;">
        `;
        
        jds.forEach(jd => {
            const lastUsed = jd.last_used_at 
                ? new Date(jd.last_used_at).toLocaleDateString() 
                : 'Never used';
            
            const primarySkills = jd.structured_data?.primary_skills || [];
            const skillsPreview = primarySkills.slice(0, 3).join(', ');
            const moreSkills = primarySkills.length > 3 ? ` +${primarySkills.length - 3} more` : '';
            
            jdsHTML += `
                <div class="jd-library-card" style="
                    background: white;
                    border: 2px solid #e0e0e0;
                    border-radius: 10px;
                    padding: 20px;
                    transition: all 0.3s;
                    cursor: pointer;
                    position: relative;
                " onmouseover="this.style.borderColor='#667eea'; this.style.boxShadow='0 4px 12px rgba(102,126,234,0.2)'" 
                   onmouseout="this.style.borderColor='#e0e0e0'; this.style.boxShadow='none'">
                    
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                        <h4 style="margin: 0; color: #333; font-size: 16px;">${jd.jd_name}</h4>
                        <span style="background: #e3f2fd; color: #1976d2; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">
                            ${jd.usage_count} uses
                        </span>
                    </div>
                    
                    <div style="margin-bottom: 15px;">
                        <p style="margin: 5px 0; color: #666; font-size: 14px;">
                            <strong>Position:</strong> ${jd.job_title || 'N/A'}
                        </p>
                        <p style="margin: 5px 0; color: #666; font-size: 14px;">
                            <strong>Company:</strong> ${jd.company_name || 'N/A'}
                        </p>
                        <p style="margin: 5px 0; color: #666; font-size: 13px;">
                            <strong>Skills:</strong> ${skillsPreview}${moreSkills}
                        </p>
                        <p style="margin: 5px 0; color: #999; font-size: 12px;">
                            <strong>Last Used:</strong> ${lastUsed}
                        </p>
                    </div>
                    
                    <div style="display: flex; gap: 8px; margin-top: 15px; padding-top: 15px; border-top: 1px solid #f0f0f0;">
                        <button onclick="useJDFromLibrary(${jd.id})" class="btn btn-sm btn-primary" style="flex: 1; padding: 8px; font-size: 13px;">
                            📂 Use This JD
                        </button>
                        <button onclick="viewJDDetails(${jd.id})" class="btn btn-sm btn-secondary" style="padding: 8px 12px; font-size: 13px;">
                            👁️
                        </button>
                        <button onclick="deleteJDFromLibrary(${jd.id})" class="btn btn-sm btn-danger" style="padding: 8px 12px; font-size: 13px;">
                            🗑️
                        </button>
                    </div>
                </div>
            `;
        });
        
        jdsHTML += '</div>';
    }
    
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 1200px; width: 95%;">
            <div class="modal-header">
                <h3>📚 JD Library (${jds.length} saved)</h3>
                <button class="modal-close" onclick="closeJDLibraryModal()">&times;</button>
            </div>
            
            <div class="modal-body">
                <div style="margin-bottom: 20px; display: flex; gap: 10px; align-items: center;">
                    <input type="text" id="jd-library-search" placeholder="Search by name, job title, or company..." 
                           style="flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 6px;"
                           onkeyup="searchJDLibrary()">
                    <button onclick="showJDLibrary()" class="btn btn-secondary" style="padding: 10px 20px;">
                        🔄 Refresh
                    </button>
                </div>
                
                ${jdsHTML}
            </div>
            
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeJDLibraryModal()">Close</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.style.display = 'flex';
}

/**
 * Use JD from Library
 */
/**
 * Use JD from Library - FIXED VERSION
 * Now properly navigates to Step 2 (Review & Approve) instead of Step 3
 */
async function useJDFromLibrary(jdId) {
    try {
        Utils.showLoading('Loading JD from library...');
        
        // Get JD data
        const response = await Utils.makeRequest(`/api/jd-library/get/${jdId}`);
        
        if (response.status === 'success') {
            const jd = response.jd;
            
            // Generate new session ID
            const newSessionId = generateSessionId();
            appState.setSessionId(newSessionId);
            
            // Store JD data in appState (pre-approved structure)
            appState.jdData = {
                structured_data: jd.structured_data,
                session_id: newSessionId,
                skills_weightage: jd.skills_weightage || {},
                isFromLibrary: true,  // Flag to indicate this is from library
                jdLibraryId: jd.id
            };
            
            // Close library modal FIRST
            closeJDLibraryModal();
            
            // CRITICAL FIX: Display structured JD in Step 2 WITHOUT auto-approval
            displayStructuredJD(jd.structured_data);
            
            // FIXED: Navigate to Step 2 (Review & Approve) instead of Step 3
            appState.currentStep = 2;
            appState.updateUI();
            
            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
            
            // Show informative message
            Utils.showToast(`✅ JD "${jd.jd_name}" loaded! Please review and approve.`, 'success');
            
            // Optional: Add a helper message in the UI
            const structuredDisplay = document.getElementById('structured-jd-display');
            if (structuredDisplay) {
                const helperMessage = document.createElement('div');
                helperMessage.className = 'library-jd-notice';
                helperMessage.style.cssText = 'background: #e3f2fd; padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #2196f3;';
                helperMessage.innerHTML = `
                    <p style="margin: 0; color: #1976d2; font-weight: 500;">
                        📚 This JD was loaded from your library: <strong>${jd.jd_name}</strong>
                    </p>
                    <p style="margin: 8px 0 0 0; color: #1976d2; font-size: 13px;">
                        Please review the structure below and click "Approve Structure" to continue.
                    </p>
                `;
                structuredDisplay.insertBefore(helperMessage, structuredDisplay.firstChild);
            }
        }
        
    } catch (error) {
        console.error('❌ Error using JD from library:', error);
        Utils.showToast('Error loading JD: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

/**
 * Modified approveStructure function to handle library JDs
 * This ensures proper workflow when approving library JDs
 */
/**
 * Modified approveStructure function to handle library JDs
 * This ensures proper workflow when approving library JDs
 */
async function approveStructure() {
    try {
        Utils.showLoading('Approving structure...');
        
        // Check if this is a library JD that hasn't been saved to session yet
        if (appState.jdData && appState.jdData.isFromLibrary) {
            // For library JDs, directly approve without upload step
            const sessionId = appState.getSessionId();
            
            // Directly approve with structured data from library
            const response = await Utils.makeRequest(`/api/jd/approve-structure/${sessionId}`, {
                method: 'POST',
                body: {
                    approved: true,
                    structured_data: appState.jdData.structured_data
                }
            });
            
            if (response.ready_for_skills_weightage || response.status === 'approved') {
                // Generate skills weightage form with pre-configured weights
                await generateSkillsWeightageForm(
                    appState.jdData.structured_data,
                    appState.jdData.skills_weightage
                );
                
                // Remove the library flag
                delete appState.jdData.isFromLibrary;
                
                // Move to Step 3
                appState.nextStep();
                Utils.showToast('Structure approved! Please set skills weightage.', 'success');
            }
        } else {
            // Normal JD approval flow (not from library)
            const sessionResponse = await Utils.makeRequest(`/api/jd/session/${appState.getSessionId()}`);
            const currentStructure = sessionResponse.structuring_session?.current_structure;
            console.log('Current structure before approval:', currentStructure);
            
            const response = await Utils.makeRequest(`/api/jd/approve-structure/${appState.getSessionId()}`, {
                method: 'POST',
                body: { approved: true }
            });
            
            if (response.ready_for_skills_weightage) {
                appState.jdData = response;
                await generateSkillsWeightageForm(currentStructure);
                appState.nextStep();
                Utils.showToast('Structure approved! Please set skills weightage.', 'success');
            }
        }
    } catch (error) {
        console.error('Error approving structure:', error);
        Utils.showToast(error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}





/**
 * Save current JD to library
 */
async function saveCurrentJDToLibrary() {
    const jdName = prompt('Enter a name for this JD (e.g., "Senior Python Developer - Remote"):');
    
    if (!jdName || !jdName.trim()) {
        Utils.showToast('JD name is required', 'warning');
        return;
    }
    
    try {
        Utils.showLoading('Saving JD to library...');
        
        // Get current session ID
        const sessionId = appState.getSessionId();
        
        if (!sessionId) {
            throw new Error('No active session found. Please process a JD first.');
        }
        
        console.log('📋 Fetching session data for:', sessionId);
        
        // Get current session data
        const sessionResponse = await Utils.makeRequest(`/api/jd/session/${sessionId}`);
        
        console.log('📊 Session Response:', sessionResponse);
        
        // Extract structured data from response
        const structuredData = sessionResponse?.jd_data?.structured_data 
                            || sessionResponse?.structuring_session?.current_structure
                            || appState.jdData?.structured_data;
        
        if (!structuredData) {
            throw new Error('No structured JD data found. Please approve the JD structure first.');
        }
        
        console.log('✅ Structured Data Found:', structuredData);
        
        // Prepare data for saving
        const saveData = {
            jd_name: jdName.trim(),
            original_text: sessionResponse?.jd_data?.original_text || '',
            structured_data: structuredData,
            skills_weightage: appState.skillsWeightage || sessionResponse?.jd_data?.skills_weightage || {},
            tags: [
                structuredData.job_title || 'Unknown Position',
                ...(structuredData.primary_skills || []).slice(0, 3)
            ].filter(Boolean) // Remove undefined/null
        };
        
        console.log('💾 Saving to library:', saveData);
        
        // Save to library
        const response = await Utils.makeRequest('/api/jd-library/save', {
            method: 'POST',
            body: saveData
        });
        
        console.log('📤 Save Response:', response);
        
        if (response.status === 'success') {
            Utils.showToast(`✅ JD "${jdName}" saved to library successfully!`, 'success');
        } else {
            throw new Error(response.message || 'Failed to save to library');
        }
        
    } catch (error) {
        console.error('❌ Error saving JD to library:', error);
        Utils.showToast(`Error saving JD: ${error.message}`, 'error');
    } finally {
        Utils.hideLoading();
    }
}


/**
 * View JD Details
 */
async function viewJDDetails(jdId) {
    try {
        Utils.showLoading('Loading JD details...');
        
        const response = await Utils.makeRequest(`/api/jd-library/get/${jdId}`);
        
        if (response.status === 'success') {
            displayJDDetailsModal(response.jd);
        }
        
    } catch (error) {
        console.error('Error loading JD details:', error);
        Utils.showToast('Error loading details: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

/**
 * Display JD Details Modal
 */
function displayJDDetailsModal(jd) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.id = 'jd-details-modal';
    
    const structured = jd.structured_data || {};
    
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 800px;">
            <div class="modal-header">
                <h3>${jd.jd_name}</h3>
                <button class="modal-close" onclick="closeJDDetailsModal()">&times;</button>
            </div>
            
            <div class="modal-body">
                <div class="structured-jd">
                    ${structured.job_title ? `<div class="jd-field"><strong>Job Title:</strong> ${structured.job_title}</div>` : ''}
                    ${structured.company ? `<div class="jd-field"><strong>Company:</strong> ${structured.company}</div>` : ''}
                    ${structured.location ? `<div class="jd-field"><strong>Location:</strong> ${structured.location}</div>` : ''}
                    ${structured.experience_required ? `<div class="jd-field"><strong>Experience:</strong> ${structured.experience_required}</div>` : ''}
                    
                    ${structured.primary_skills && structured.primary_skills.length > 0 ? `
                        <div class="jd-field">
                            <strong>Primary Skills:</strong>
                            <div class="skills-tags" style="margin-top: 8px;">
                                ${structured.primary_skills.map(skill => `<span class="skill-tag primary">${skill}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    ${structured.secondary_skills && structured.secondary_skills.length > 0 ? `
                        <div class="jd-field">
                            <strong>Secondary Skills:</strong>
                            <div class="skills-tags" style="margin-top: 8px;">
                                ${structured.secondary_skills.map(skill => `<span class="skill-tag secondary">${skill}</span>`).join('')}
                            </div>
                        </div>
                    ` : ''}
                </div>
                
                <div style="margin-top: 20px; padding-top: 20px; border-top: 1px solid #eee;">
                    <p><strong>Usage Count:</strong> ${jd.usage_count} times</p>
                    <p><strong>Created:</strong> ${new Date(jd.created_at).toLocaleString()}</p>
                    ${jd.last_used_at ? `<p><strong>Last Used:</strong> ${new Date(jd.last_used_at).toLocaleString()}</p>` : ''}
                </div>
            </div>
            
            <div class="modal-footer">
                <button class="btn btn-primary" onclick="useJDFromLibrary(${jd.id})">Use This JD</button>
                <button class="btn btn-secondary" onclick="closeJDDetailsModal()">Close</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.style.display = 'flex';
}

/**
 * Delete JD from Library
 */
async function deleteJDFromLibrary(jdId) {
    if (!confirm('Are you sure you want to archive this JD?')) {
        return;
    }
    
    try {
        Utils.showLoading('Archiving JD...');
        
        await Utils.makeRequest(`/api/jd-library/delete/${jdId}`, {
            method: 'DELETE'
        });
        
        Utils.showToast('JD archived successfully', 'success');
        
        // Refresh library
        showJDLibrary();
        
    } catch (error) {
        console.error('Error deleting JD:', error);
        Utils.showToast('Error archiving JD: ' + error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

/**
 * Search JD Library
 */
async function searchJDLibrary() {
    const searchInput = document.getElementById('jd-library-search');
    const searchTerm = searchInput ? searchInput.value.trim() : '';
    
    try {
        const url = searchTerm 
            ? `/api/jd-library/list?search=${encodeURIComponent(searchTerm)}`
            : '/api/jd-library/list';
        
        const response = await Utils.makeRequest(url);
        
        if (response.status === 'success') {
            // Re-render the JD cards
            const container = document.querySelector('.jd-library-grid');
            if (container && container.parentElement) {
                // Remove old modal and show new one
                closeJDLibraryModal();
                displayJDLibraryModal(response.jds, response.user_role);
            }
        }
        
    } catch (error) {
        console.error('Error searching JD library:', error);
    }
}

/**
 * Close Modals
 */
function closeJDLibraryModal() {
    const modal = document.getElementById('jd-library-modal');
    if (modal) {
        modal.remove();
    }
}

function closeJDDetailsModal() {
    const modal = document.getElementById('jd-details-modal');
    if (modal) {
        modal.remove();
    }
}

/**
 * Generate Session ID
 */
function generateSessionId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

// Make functions globally available
window.showJDLibrary = showJDLibrary;
window.useJDFromLibrary = useJDFromLibrary;
window.saveCurrentJDToLibrary = saveCurrentJDToLibrary;
window.viewJDDetails = viewJDDetails;
window.deleteJDFromLibrary = deleteJDFromLibrary;
window.searchJDLibrary = searchJDLibrary;
window.closeJDLibraryModal = closeJDLibraryModal;
window.closeJDDetailsModal = closeJDDetailsModal;