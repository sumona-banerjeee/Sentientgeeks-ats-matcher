// ============================================================================
// ENHANCED ROUTING & STATE PERSISTENCE SYSTEM WITH URL MANAGEMENT
// ============================================================================
// Features:
// - URL-based routing with browser history support
// - Proper back/forward button handling
// - Session state persistence
// - Conditional home button display
// ============================================================================

class AppRouter {
    constructor() {
        this.STATE_KEY = 'ats_app_state';
        this.SESSION_KEY = 'ats_session_data';
        this.homeButton = null;
        this.currentSessionId = null;
        this.hasActiveResults = false; // Track if user has completed matching
        this.initializeRouter();
    }

    /**
     * Initialize router and event listeners
     */
    initializeRouter() {
        // Handle browser back/forward buttons
        window.addEventListener('popstate', (event) => {
            if (event.state && event.state.step) {
                this.navigateToStep(event.state.step, false);
            }
        });
        
        // Save state before page unload
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
                this.initializeFromURL();
            });
        } else {
            this.setupHomeButton();
            this.initializeFromURL();
        }
    }

    /**
     * Initialize application state from URL
     */
    initializeFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const stepParam = urlParams.get('step');
        
        if (stepParam) {
            const step = parseInt(stepParam);
            if (step >= 1 && step <= 5) {
                appState.currentStep = step;
                appState.updateUI();
                this.updateHomeButtonVisibility();
            }
        }
    }

    /**
     * Navigate to a specific step with URL update
     * @param {number} step - Step number (1-5)
     * @param {boolean} addToHistory - Whether to add to browser history
     */
    navigateToStep(step, addToHistory = true) {
        if (step < 1 || step > 5) {
            console.error('Invalid step:', step);
            return;
        }

        console.log(`📍 Navigating to Step ${step}`);
        
        // Update app state
        appState.currentStep = step;
        appState.updateUI();
        
        // Update URL and browser history
        const url = new URL(window.location);
        url.searchParams.set('step', step);
        
        if (addToHistory) {
            window.history.pushState({ step }, '', url);
        } else {
            window.history.replaceState({ step }, '', url);
        }
        
        // Update home button visibility
        this.updateHomeButtonVisibility();
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
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
        }
    }

    /**
     * Update home button visibility based on current step
     */
    updateHomeButtonVisibility() {
        if (!this.homeButton) {
            this.homeButton = document.getElementById('home-btn');
        }
    
        if (!this.homeButton) return;
    
        const currentStep = appState.currentStep;
    
        // Show home button from Step 2 onwards
        if (currentStep >= 2 && currentStep <= 5) {
            this.homeButton.style.display = 'inline-flex';
        } else {
            this.homeButton.style.display = 'none';
        }
    }

    /**
     * Navigate back to home (Step 1)
     */
    goToHome() {
        const confirmMsg = 'Are you sure you want to go back to home? Your current progress will be lost.';
        if (confirm(confirmMsg)) {
            console.log('Navigating to home...');
            
            // Clear state
            this.clearState();
            
            // Reset to step 1
            appState.currentStep = 1;
            appState.sessionId = null;
            appState.jdData = null;
            appState.resumes = [];
            appState.matchingResults = [];
            this.hasActiveResults = false;
            
            // Navigate to step 1 with URL update
            this.navigateToStep(1);
            
            // Clear form inputs
            this.resetJDUploadForm();
            
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
     * Save temporary state for reload persistence
     */
    saveTemporaryState() {
        try {
            const state = {
                currentStep: appState.currentStep,
                sessionId: appState.sessionId,
                hasActiveResults: this.hasActiveResults,
                timestamp: Date.now(),
                isTemporary: true
            };
            
            sessionStorage.setItem(this.STATE_KEY, JSON.stringify(state));
            console.log('💾 Temporary state saved:', state);
        } catch (error) {
            console.error('❌ Error saving temporary state:', error);
        }
    }

    /**
     * Save permanent state (called after Step 5 completion)
     */
    saveState() {
        try {
            if (appState.currentStep !== 5) {
                console.log(`⏭️ Permanent state NOT saved - User on Step ${appState.currentStep}`);
                return;
            }
            
            const state = {
                currentStep: appState.currentStep,
                sessionId: appState.sessionId,
                hasActiveResults: true,
                timestamp: Date.now(),
                isPermanent: true
            };
            
            localStorage.setItem(this.STATE_KEY, JSON.stringify(state));
            this.hasActiveResults = true;
            console.log('💾 Permanent state saved (Step 5 completed):', state);
        } catch (error) {
            console.error('❌ Error saving permanent state:', error);
        }
    }

    /**
     * Restore application state after refresh
     */
    async restoreState() {
        try {
            // Check temporary state first (page reload)
            let savedState = sessionStorage.getItem(this.STATE_KEY);
            let isTemporary = false;
            
            if (savedState) {
                console.log('🔄 Found temporary state');
                isTemporary = true;
            } else {
                // Check permanent state
                savedState = localStorage.getItem(this.STATE_KEY);
                if (savedState) {
                    console.log('🔄 Found permanent state');
                }
            }
            
            if (!savedState) {
                console.log('ℹ️ No saved state - starting fresh');
                this.updateHomeButtonVisibility();
                return false;
            }

            const state = JSON.parse(savedState);
            
            // Validate session
            if (state.sessionId) {
                const sessionValid = await this.validateSession(state.sessionId);
                
                if (!sessionValid) {
                    console.log('⚠️ Session no longer valid');
                    this.clearState();
                    if (typeof Utils !== 'undefined' && Utils.showToast) {
                        Utils.showToast('Previous session expired. Starting fresh.', 'info');
                    }
                    this.updateHomeButtonVisibility();
                    return false;
                }
            }

            // Restore state
            if (typeof Utils !== 'undefined' && Utils.showLoading) {
                Utils.showLoading('Restoring your session...');
            }

            appState.sessionId = state.sessionId;
            this.currentSessionId = state.sessionId;
            this.hasActiveResults = state.hasActiveResults || false;
            
            // Navigate to saved step
            this.navigateToStep(state.currentStep, false);
            
            // Load step data
            await this.loadStepData(state.currentStep);

            if (isTemporary) {
                sessionStorage.removeItem(this.STATE_KEY);
            }

            if (typeof Utils !== 'undefined' && Utils.hideLoading) {
                Utils.hideLoading();
            }

            if (typeof Utils !== 'undefined' && Utils.showToast) {
                Utils.showToast(`✅ Session restored to Step ${state.currentStep}`, 'success');
            }

            return true;
        } catch (error) {
            console.error('❌ Error restoring state:', error);
            if (typeof Utils !== 'undefined' && Utils.hideLoading) {
                Utils.hideLoading();
            }
            this.clearState();
            return false;
        }
    }

    /**
     * Validate if session exists on backend
     */
    async validateSession(sessionId) {
        if (!sessionId) return false;
        
        try {
            const response = await fetch(`/api/jd/session/${sessionId}`);
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
                case 2:
                    await this.loadJDStructure();
                    break;
                case 3:
                    await this.loadSkillsWeightage();
                    break;
                case 4:
                    await this.loadResumesList();
                    break;
                case 5:
                    await this.loadMatchingResults();
                    break;
            }
        } catch (error) {
            console.error('❌ Error loading step data:', error);
        }
    }

    /**
     * Load JD structure for step 2
     */
    async loadJDStructure() {
        try {
            const response = await fetch(`/api/jd/session/${appState.sessionId}`);
            if (!response.ok) throw new Error('Failed to load JD structure');
            
            const data = await response.json();
            
            let structuredData = data.jd_data?.structured_data 
                              || data.structuring_session?.current_structure 
                              || data.structured_data 
                              || data.jd_data;
            
            if (structuredData && typeof displayStructuredJD === 'function') {
                appState.jdData = data.jd_data || data;
                displayStructuredJD(structuredData);
                console.log('✅ JD structure loaded');
            }
        } catch (error) {
            console.error('❌ Error loading JD structure:', error);
        }
    }

    /**
     * Load skills weightage for step 3
     */
    async loadSkillsWeightage() {
        try {
            const response = await fetch(`/api/jd/session/${appState.sessionId}`);
            if (!response.ok) throw new Error('Failed to load skills');
            
            const data = await response.json();
            let structuredData = data.jd_data?.structured_data 
                              || data.structuring_session?.current_structure 
                              || data.structured_data;
            
            if (structuredData && typeof generateSkillsWeightageForm === 'function') {
                await generateSkillsWeightageForm(structuredData);
                console.log('✅ Skills weightage loaded');
            }
        } catch (error) {
            console.error('❌ Error loading skills:', error);
        }
    }

    /**
     * Load resumes list for step 4
     */
    async loadResumesList() {
        try {
            const response = await fetch(`/api/resumes/session/${appState.sessionId}`);
            if (!response.ok) throw new Error('Failed to load resumes');
            
            const data = await response.json();
            
            if (data.resumes && data.resumes.length > 0) {
                appState.resumes = data.resumes;
                console.log(`✅ Loaded ${data.resumes.length} resumes`);
            }
        } catch (error) {
            console.error('❌ Error loading resumes:', error);
        }
    }

    /**
     * Load matching results for step 5
     */
    async loadMatchingResults() {
        try {
            const response = await fetch(`/api/matching/results/${appState.sessionId}`);
            if (!response.ok) throw new Error('Failed to load results');
            
            const data = await response.json();
            
            if (data.results && data.results.length > 0) {
                appState.matchingResults = data.results;
                this.hasActiveResults = true;
                
                if (typeof displayMatchingResults === 'function') {
                    await displayMatchingResults();
                    console.log('✅ Matching results loaded');
                }
            }
        } catch (error) {
            console.error('❌ Error loading results:', error);
        }
    }

    /**
     * Clear all saved state
     */
    clearState() {
        sessionStorage.removeItem(this.STATE_KEY);
        localStorage.removeItem(this.STATE_KEY);
        this.hasActiveResults = false;
        this.currentSessionId = null;
        console.log('🧹 All state cleared');
    }

    /**
     * Check if user has active matching results
     */
    hasCurrentResults() {
        return this.hasActiveResults && this.currentSessionId === appState.sessionId;
    }
}

// Initialize router globally
const appRouter = new AppRouter();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AppRouter;
}