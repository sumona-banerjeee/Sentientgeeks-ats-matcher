// ============================================================================
// ROUTING & STATE PERSISTENCE SYSTEM
// ============================================================================
// Author: SentientGeeks ATS Team
// Features:
// - Browser refresh state persistence FOR ALL STEPS
// - Conditional home button display (Steps 3 & 5 only)
// - Session validation with backend
// - NO auto-save for incomplete sessions (only saves on explicit Step 5 completion)
// ============================================================================

class AppRouter {
    constructor() {
        this.STATE_KEY = 'ats_app_state';
        this.SESSION_KEY = 'ats_session_data';
        this.homeButton = null;
        this.initializeRouter();
    }

    /**
     * Initialize router and event listeners
     */
    initializeRouter() {
        // ✅ Save state ONLY before page unload (for F5/reload persistence)
        // This is temporary state, not permanent storage
        window.addEventListener('beforeunload', () => {
            this.saveTemporaryState();
        });
        
        // Restore state on page load
        window.addEventListener('load', async () => {
            await this.restoreState();
        });
        
        // Setup home button after DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.setupHomeButton();
            });
        } else {
            this.setupHomeButton();
        }
    }

    /**
     * Setup home button event listener
     */
    setupHomeButton() {
        this.homeButton = document.getElementById('home-btn');
        if (this.homeButton) {
            this.homeButton.addEventListener('click', () => {
                this.goToHome();
            });
            console.log('✅ Home button initialized');
        } else {
            console.warn('⚠️ Home button not found in navbar');
        }
    }

   
    /**
 * Update home button visibility based on current step
 * ✅ UPDATED: Show from Step 2 onwards (after JD upload)
 */
    updateHomeButtonVisibility() {
        if (!this.homeButton) {
            this.homeButton = document.getElementById('home-btn');
        }
    
        if (!this.homeButton) return;
    
        const currentStep = appState.currentStep;
    
        // ✅ CHANGED: Show home button from Step 2 onwards (after JD processing)
        if (currentStep >= 2 && currentStep <= 5) {
            this.homeButton.style.display = 'inline-flex';
            console.log(`✅ Home button shown for Step ${currentStep}`);
        } else {
            this.homeButton.style.display = 'none';
            console.log(`🚫 Home button hidden for Step ${currentStep}`);
        }
    }


    /**
     * Navigate back to home (Step 1)
     * Clears all progress and starts fresh
     */
    goToHome() {
        const confirmMsg = 'Are you sure you want to go back to home? Your current progress will be lost.';
        if (confirm(confirmMsg)) {
            console.log('Navigating to home...');
            
            // ✅ Clear ALL state (temporary + permanent)
            this.clearState();
            
            // Reset to step 1
            appState.currentStep = 1;
            appState.sessionId = null;
            appState.jdData = null;
            appState.resumes = [];
            appState.matchingResults = [];
            appState.updateUI();
            
            // Update home button visibility
            this.updateHomeButtonVisibility();
            
            // Clear form inputs on JD upload page
            this.resetJDUploadForm();
            
            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
            
            // Show success message
            if (typeof Utils !== 'undefined' && Utils.showToast) {
                Utils.showToast('✅ Returned to home. Starting fresh session.', 'success');
            }
        }
    }

    /**
     * Reset JD upload form
     */
    resetJDUploadForm() {
        const jdFileInput = document.getElementById('jd-file');
        const jdTextInput = document.getElementById('jd-text');
        if (jdFileInput) jdFileInput.value = '';
        if (jdTextInput) jdTextInput.value = '';
        
        const processBtn = document.getElementById('process-jd-btn');
        if (processBtn) processBtn.disabled = true;
    }

    /**
     * Save temporary state for F5/reload persistence
     * This is NOT permanent storage - just for immediate page reload
     */
    saveTemporaryState() {
        try {
            const state = {
                currentStep: appState.currentStep,
                sessionId: appState.sessionId,
                timestamp: Date.now(),
                isTemporary: true, // Mark as temporary
                // Save page-specific data flags
                hasJDData: !!appState.jdData,
                hasResumes: appState.resumes && appState.resumes.length > 0,
                hasResults: appState.matchingResults && appState.matchingResults.length > 0,
                // Save scroll position
                scrollPosition: window.scrollY,
                // Save URL hash if any
                urlHash: window.location.hash
            };
            
            // Use sessionStorage for temporary state (cleared when tab/browser closes)
            sessionStorage.setItem(this.STATE_KEY, JSON.stringify(state));
            console.log('💾 Temporary state saved for reload:', state);
        } catch (error) {
            console.error('❌ Error saving temporary state:', error);
        }
    }

    /**
     * Save permanent state to localStorage
     * ✅ ONLY called explicitly after Step 5 completion
     */
    saveState() {
        try {
            // ✅ Only save permanent state if user reached Step 5 (Results)
            if (appState.currentStep !== 5) {
                console.log(`⏭️ Permanent state NOT saved - User on Step ${appState.currentStep} (not completed)`);
                return;
            }
            
            const state = {
                currentStep: appState.currentStep,
                sessionId: appState.sessionId,
                timestamp: Date.now(),
                isPermanent: true, // Mark as permanent
                // Save page-specific data flags
                hasJDData: !!appState.jdData,
                hasResumes: appState.resumes && appState.resumes.length > 0,
                hasResults: appState.matchingResults && appState.matchingResults.length > 0,
                // Save scroll position
                scrollPosition: window.scrollY,
                // Save URL hash if any
                urlHash: window.location.hash
            };
            
            // Use localStorage for permanent state
            localStorage.setItem(this.STATE_KEY, JSON.stringify(state));
            console.log('💾 Permanent state saved (Step 5 completed):', state);
        } catch (error) {
            console.error('❌ Error saving permanent state:', error);
        }
    }

    /**
     * Restore application state after refresh
     * Checks sessionStorage first (temporary), then localStorage (permanent)
     */
    async restoreState() {
        try {
            // First check sessionStorage for temporary state (F5 reload)
            let savedState = sessionStorage.getItem(this.STATE_KEY);
            let isTemporary = false;
            
            if (savedState) {
                console.log('🔄 Found temporary state (page reload)');
                isTemporary = true;
            } else {
                // Check localStorage for permanent state (Step 5 completion)
                savedState = localStorage.getItem(this.STATE_KEY);
                if (savedState) {
                    console.log('🔄 Found permanent state (Step 5 completed)');
                }
            }
            
            if (!savedState) {
                console.log('ℹ️ No saved state found - starting fresh session');
                this.updateHomeButtonVisibility();
                return false;
            }

            const state = JSON.parse(savedState);
            
            // For temporary state, always restore (it's a fresh reload)
            if (isTemporary) {
                console.log('🔄 Restoring temporary state from reload:', state);
                await this.restoreStateData(state);
                
                // Clear temporary state after successful restore
                sessionStorage.removeItem(this.STATE_KEY);
                return true;
            }
            
            // For permanent state, check age (within last 24 hours)
            const age = Date.now() - state.timestamp;
            const MAX_AGE = 24 * 60 * 60 * 1000; // 24 hours
            
            if (age > MAX_AGE) {
                console.log('⚠️ Permanent state expired (older than 24 hours)');
                this.clearState();
                this.updateHomeButtonVisibility();
                return false;
            }

            // Restore permanent state (Step 5 only)
            if (state.currentStep === 5) {
                console.log('🔄 Restoring permanent state:', state);
                await this.restoreStateData(state);
                return true;
            }

            this.updateHomeButtonVisibility();
            return false;
        } catch (error) {
            console.error('❌ Error restoring state:', error);
            this.clearState();
            this.updateHomeButtonVisibility();
            return false;
        }
    }

    /**
     * Helper function to restore state data
     */
    async restoreStateData(state) {
        try {
            // Restore session ID
            if (state.sessionId) {
                appState.sessionId = state.sessionId;
            }

            // Verify session still valid on backend
            const sessionValid = await this.validateSession(state.sessionId);
            
            if (!sessionValid) {
                console.log('⚠️ Session no longer valid on server');
                this.clearState();
                if (typeof Utils !== 'undefined' && Utils.showToast) {
                    Utils.showToast('Previous session expired. Starting fresh.', 'info');
                }
                this.updateHomeButtonVisibility();
                return false;
            }

            // Show loading indicator
            if (typeof Utils !== 'undefined' && Utils.showLoading) {
                Utils.showLoading('Restoring your session...');
            }

            // Restore step
            appState.currentStep = state.currentStep;
            appState.updateUI();
            
            // Load step-specific data from backend
            await this.loadStepData(state.currentStep);

            // Restore scroll position
            if (state.scrollPosition) {
                setTimeout(() => {
                    window.scrollTo({
                        top: state.scrollPosition,
                        behavior: 'smooth'
                    });
                }, 300);
            }

            // Update home button visibility
            this.updateHomeButtonVisibility();

            // Hide loading
            if (typeof Utils !== 'undefined' && Utils.hideLoading) {
                Utils.hideLoading();
            }

            // Show success toast
            if (typeof Utils !== 'undefined' && Utils.showToast) {
                Utils.showToast(`✅ Session restored! You're on Step ${state.currentStep}.`, 'success');
            }

            return true;
        } catch (error) {
            console.error('❌ Error in restoreStateData:', error);
            if (typeof Utils !== 'undefined' && Utils.hideLoading) {
                Utils.hideLoading();
            }
            return false;
        }
    }

    /**
     * Validate if session exists on backend
     */
    async validateSession(sessionId) {
        if (!sessionId) return false;
        
        try {
            const response = await fetch(`/api/jd/session/${sessionId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            return response.ok;
        } catch (error) {
            console.error('❌ Session validation failed:', error);
            return false;
        }
    }

    /**
     * Load data specific to current step
     */
    async loadStepData(step) {
        try {
            console.log(`📥 Loading data for Step ${step}...`);
            
            switch(step) {
                case 2: // JD Structure Review
                    await this.loadJDStructure();
                    break;
                case 3: // Skills Weightage
                    await this.loadSkillsWeightage();
                    break;
                case 4: // Resume Upload
                    await this.loadResumesList();
                    break;
                case 5: // Matching Results
                    await this.loadMatchingResults();
                    break;
            }
        } catch (error) {
            console.error('❌ Error loading step data:', error);
            if (typeof Utils !== 'undefined' && Utils.showToast) {
                Utils.showToast('Error restoring session data. Please refresh.', 'error');
            }
        }
    }

    /**
     * Load JD structure for step 2
     * ✅ FIXED: Proper data loading with multiple API response paths
     */
    async loadJDStructure() {
        try {
            const response = await fetch(`/api/jd/session/${appState.sessionId}`);
            if (!response.ok) throw new Error('Failed to load JD structure');
            
            const data = await response.json();
            console.log('📥 API Response for JD structure:', data);
            
            // ✅ FIXED: Try multiple possible data paths from API response
            let structuredData = null;
            
            // Check different possible paths in API response
            if (data.jd_data?.structured_data) {
                structuredData = data.jd_data.structured_data;
            } else if (data.structuring_session?.current_structure) {
                structuredData = data.structuring_session.current_structure;
            } else if (data.structured_data) {
                structuredData = data.structured_data;
            } else if (data.jd_data) {
                structuredData = data.jd_data;
            }
            
            if (structuredData) {
                appState.jdData = data.jd_data || data;
                
                // ✅ CRITICAL: Call displayStructuredJD function
                if (typeof displayStructuredJD === 'function') {
                    displayStructuredJD(structuredData);
                    console.log('✅ JD structure displayed successfully');
                } else if (typeof window.displayStructuredJD === 'function') {
                    window.displayStructuredJD(structuredData);
                    console.log('✅ JD structure displayed via window.displayStructuredJD');
                } else {
                    console.error('❌ displayStructuredJD function not found');
                }
            } else {
                console.warn('⚠️ No structured data found in API response');
                const container = document.getElementById('structured-jd-display');
                if (container) {
                    container.innerHTML = `
                        <div class="empty-structure" style="padding: 20px; text-align: center;">
                            <p style="color: #e74c3c; font-size: 16px; margin-bottom: 10px;">⚠️ No structured data found for this session.</p>
                            <p style="color: #7f8c8d; margin-bottom: 20px;">The session may have expired or been cleared.</p>
                            <button onclick="appRouter.startNewSession()" class="btn btn-primary" style="padding: 10px 20px; background: #3498db; color: white; border: none; border-radius: 5px; cursor: pointer;">Start New Session</button>
                        </div>
                    `;
                }
            }
            
            console.log('✅ JD structure loaded');
        } catch (error) {
            console.error('❌ Error loading JD structure:', error);
            const container = document.getElementById('structured-jd-display');
            if (container) {
                container.innerHTML = `
                    <div class="error-container" style="padding: 20px; text-align: center;">
                        <p style="color: #e74c3c; font-size: 16px; margin-bottom: 10px;">❌ Error loading JD structure: ${error.message}</p>
                        <div style="margin-top: 20px;">
                            <button onclick="location.reload()" class="btn btn-warning" style="padding: 10px 20px; background: #f39c12; color: white; border: none; border-radius: 5px; cursor: pointer; margin-right: 10px;">Retry</button>
                            <button onclick="appRouter.startNewSession()" class="btn btn-secondary" style="padding: 10px 20px; background: #95a5a6; color: white; border: none; border-radius: 5px; cursor: pointer;">Start New Session</button>
                        </div>
                    </div>
                `;
            }
        }
    }

    /**
     * Load skills weightage for step 3
     * ✅ FIXED: Proper data loading with error handling
     */
    async loadSkillsWeightage() {
        try {
            const response = await fetch(`/api/jd/session/${appState.sessionId}`);
            if (!response.ok) throw new Error('Failed to load skills data');
            
            const data = await response.json();
            console.log('📥 API Response for skills:', data);
            
            // ✅ FIXED: Try multiple possible data paths
            let structuredData = null;
            
            if (data.jd_data?.structured_data) {
                structuredData = data.jd_data.structured_data;
            } else if (data.structuring_session?.current_structure) {
                structuredData = data.structuring_session.current_structure;
            } else if (data.structured_data) {
                structuredData = data.structured_data;
            }
            
            if (structuredData) {
                // ✅ CRITICAL: Call generateSkillsWeightageForm function
                if (typeof generateSkillsWeightageForm === 'function') {
                    await generateSkillsWeightageForm(structuredData);
                    console.log('✅ Skills weightage form generated');
                } else if (typeof window.generateSkillsWeightageForm === 'function') {
                    await window.generateSkillsWeightageForm(structuredData);
                    console.log('✅ Skills form generated via window function');
                } else {
                    console.error('❌ generateSkillsWeightageForm function not found');
                }
            } else {
                console.warn('⚠️ No structured data found for skills');
                const container = document.getElementById('skills-weightage-form');
                if (container) {
                    container.innerHTML = `
                        <div class="error-container" style="padding: 20px; text-align: center;">
                            <p style="color: #e74c3c;">❌ No skills data found for this session.</p>
                            <button onclick="appRouter.goToHome()" class="btn btn-primary" style="padding: 10px 20px; margin-top: 15px;">Go to Home</button>
                        </div>
                    `;
                }
            }
            
            console.log('✅ Skills weightage loaded');
        } catch (error) {
            console.error('❌ Error loading skills weightage:', error);
            const container = document.getElementById('skills-weightage-form');
            if (container) {
                container.innerHTML = `
                    <div class="error-container" style="padding: 20px; text-align: center;">
                        <p style="color: #e74c3c;">❌ Error loading skills: ${error.message}</p>
                        <button onclick="location.reload()" class="btn btn-warning" style="padding: 10px 20px; margin-top: 15px;">Retry</button>
                    </div>
                `;
            }
        }
    }

    /**
     * Load resumes list for step 4
     * ✅ FIXED: Proper resumes display with fallback
     */
    async loadResumesList() {
        try {
            const response = await fetch(`/api/resumes/session/${appState.sessionId}`);
            if (!response.ok) throw new Error('Failed to load resumes');
            
            const data = await response.json();
            console.log('📥 API Response for resumes:', data);
            
            if (data.resumes && data.resumes.length > 0) {
                appState.resumes = data.resumes;
                
                // ✅ Display resumes list
                if (typeof displayResumesList === 'function') {
                    displayResumesList(data.resumes);
                    console.log(`✅ Displayed ${data.resumes.length} resumes`);
                } else if (typeof window.displayResumesList === 'function') {
                    window.displayResumesList(data.resumes);
                } else {
                    // Fallback display
                    const container = document.getElementById('resumes-list');
                    if (container) {
                        container.innerHTML = `
                            <div class="resumes-summary" style="padding: 20px; background: #ecf0f1; border-radius: 8px;">
                                <h3 style="color: #27ae60; margin-bottom: 10px;">✅ ${data.resumes.length} Resumes Uploaded</h3>
                                <p style="color: #34495e;">Resumes are ready for matching.</p>
                            </div>
                        `;
                    }
                }
            } else {
                console.log('⚠️ No resumes found for this session');
                const container = document.getElementById('resumes-list');
                if (container) {
                    container.innerHTML = `
                        <div class="no-resumes" style="padding: 20px; text-align: center;">
                            <p style="color: #7f8c8d;">No resumes uploaded yet.</p>
                            <p style="color: #7f8c8d;">Please upload resumes to continue.</p>
                        </div>
                    `;
                }
            }
            
            console.log(`✅ Loaded ${data.resumes?.length || 0} resumes`);
        } catch (error) {
            console.error('❌ Error loading resumes list:', error);
            const container = document.getElementById('resumes-list');
            if (container) {
                container.innerHTML = `
                    <div class="error-container" style="padding: 20px; text-align: center;">
                        <p style="color: #e74c3c;">❌ Error loading resumes: ${error.message}</p>
                        <button onclick="location.reload()" class="btn btn-warning" style="padding: 10px 20px; margin-top: 15px;">Retry</button>
                    </div>
                `;
            }
        }
    }

    /**
     * Load matching results for step 5
     * ✅ FIXED: Proper results display
     */
    async loadMatchingResults() {
        try {
            const response = await fetch(`/api/matching/results/${appState.sessionId}`);
            if (!response.ok) throw new Error('Failed to load matching results');
            
            const data = await response.json();
            console.log('📥 API Response for results:', data);
            
            if (data.results && data.results.length > 0) {
                appState.matchingResults = data.results;
                
                // ✅ Display matching results
                if (typeof displayMatchingResults === 'function') {
                    await displayMatchingResults();
                    console.log(`✅ Displayed ${data.results.length} matching results`);
                } else if (typeof window.displayMatchingResults === 'function') {
                    await window.displayMatchingResults();
                } else {
                    console.error('❌ displayMatchingResults function not found');
                }
            } else {
                console.log('⚠️ No matching results found');
                const container = document.getElementById('results-content');
                if (container) {
                    container.innerHTML = `
                        <div class="no-results" style="padding: 20px; text-align: center;">
                            <p style="color: #7f8c8d;">No matching results found for this session.</p>
                            <button onclick="appRouter.goToHome()" class="btn btn-primary" style="padding: 10px 20px; margin-top: 15px;">Start New Session</button>
                        </div>
                    `;
                }
            }
            
            console.log(`✅ Loaded ${data.results?.length || 0} matching results`);
        } catch (error) {
            console.error('❌ Error loading matching results:', error);
            const container = document.getElementById('results-content');
            if (container) {
                container.innerHTML = `
                    <div class="error-container" style="padding: 20px; text-align: center;">
                        <p style="color: #e74c3c;">❌ Error loading results: ${error.message}</p>
                        <button onclick="location.reload()" class="btn btn-warning" style="padding: 10px 20px; margin-top: 15px;">Retry</button>
                    </div>
                `;
            }
        }
    }

    /**
     * Clear ALL saved state (both temporary and permanent)
     */
    clearState() {
        sessionStorage.removeItem(this.STATE_KEY); // Clear temporary
        localStorage.removeItem(this.STATE_KEY);    // Clear permanent
        console.log('🧹 All state cleared from storage');
    }

    /**
     * Start completely new session
     */
    startNewSession() {
        this.clearState();
        appState.sessionId = null;
        appState.currentStep = 1;
        appState.jdData = null;
        appState.resumes = [];
        appState.matchingResults = [];
        appState.updateUI();
        this.updateHomeButtonVisibility();
        
        if (typeof Utils !== 'undefined' && Utils.showToast) {
            Utils.showToast('🆕 Started new session', 'success');
        }
    }
}

// Initialize router globally
const appRouter = new AppRouter();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AppRouter;
}
