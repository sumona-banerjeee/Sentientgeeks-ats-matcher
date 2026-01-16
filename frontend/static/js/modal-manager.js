
class ModalManager {
    constructor() {
        this.activeModals = new Set();
        this.init();
    }

    init() {
        // Listen for modal additions to the DOM
        this.setupMutationObserver();
        
        // Setup global click handler
        this.setupGlobalClickHandler();
        
        // Setup escape key handler
        this.setupEscapeKeyHandler();
        
        console.log('✅ Modal Manager initialized');
    }

    /**
     * Watch for modal elements being added to DOM
     */
    setupMutationObserver() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) { // Element node
                        // Check if it's a modal or contains a modal
                        if (this.isModal(node)) {
                            this.registerModal(node);
                        } else {
                            // Check children
                            const modals = node.querySelectorAll 
                                ? node.querySelectorAll('[class*="modal"]')
                                : [];
                            modals.forEach(modal => this.registerModal(modal));
                        }
                    }
                });

                mutation.removedNodes.forEach((node) => {
                    if (node.nodeType === 1) {
                        if (this.isModal(node)) {
                            this.unregisterModal(node);
                        }
                    }
                });
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    /**
     * Check if element is a modal
     */
    isModal(element) {
        const className = element.className || '';
        return className.includes('modal-overlay') || 
               className.includes('candidate-modal-overlay') ||
               className.includes('interview-modal') ||
               className.includes('emergency-candidate-modal') ||
               element.id === 'history-modal' ||
               element.id === 'jd-library-modal' ||
               element.id === 'jd-details-modal' ||
               element.id === 'history-details-modal' ||
               element.id === 'interview-questions-modal' ||
               element.id === 'detailed-modal';
    }

    /**
     * Register a modal for management
     */
    registerModal(modal) {
        if (!this.isModal(modal)) return;

        // Check if modal is visible
        const style = window.getComputedStyle(modal);
        if (style.display !== 'none') {
            this.activeModals.add(modal);
            this.lockBodyScroll();
            console.log('📌 Modal registered:', modal.id || modal.className);
        }
    }

    /**
     * Unregister a modal
     */
    unregisterModal(modal) {
        this.activeModals.delete(modal);
        
        // If no more active modals, unlock scroll
        if (this.activeModals.size === 0) {
            this.unlockBodyScroll();
        }
        console.log('📍 Modal unregistered:', modal.id || modal.className);
    }

    /**
     * Lock body scroll when modal is open
     */
    lockBodyScroll() {
        document.body.classList.add('modal-open');
        document.body.style.overflow = 'hidden';
        document.body.style.height = '100vh';
    }

    /**
     * Unlock body scroll when all modals are closed
     */
    unlockBodyScroll() {
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.height = '';
    }

    /**
     * Setup global click handler for click-outside-to-close
     */
    setupGlobalClickHandler() {
        document.addEventListener('click', (e) => {
            // Check if clicked element is a modal overlay
            const clickedModal = Array.from(this.activeModals).find(modal => 
                modal === e.target
            );

            if (clickedModal) {
                // User clicked on the modal overlay (background)
                // Don't close if clicked on modal content
                const modalContent = clickedModal.querySelector('.modal-content') ||
                                    clickedModal.querySelector('[class*="modal-content"]') ||
                                    clickedModal.querySelector('div[style*="background: white"]');

                if (modalContent && !modalContent.contains(e.target)) {
                    this.closeModal(clickedModal);
                }
            }
        }, true);
    }

    /**
     * Setup ESC key handler to close modals
     */
    setupEscapeKeyHandler() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.activeModals.size > 0) {
                // Close the most recently opened modal
                const modals = Array.from(this.activeModals);
                const topModal = modals[modals.length - 1];
                this.closeModal(topModal);
            }
        });
    }

    /**
     * Close a specific modal
     */
    closeModal(modal) {
        if (!modal) return;

        // Try to find and trigger existing close functions
        const modalId = modal.id;
        const closeFunctions = {
            'history-modal': 'closeHistoryModal',
            'history-details-modal': 'closeHistoryDetailsModal',
            'jd-library-modal': 'closeJDLibraryModal',
            'jd-details-modal': 'closeJDDetailsModal',
            'interview-questions-modal': 'closeInterviewModal',
            'detailed-modal': 'closeModal'
        };

        // Check for specific close function
        if (modalId && closeFunctions[modalId]) {
            const closeFunc = window[closeFunctions[modalId]];
            if (typeof closeFunc === 'function') {
                closeFunc();
                return;
            }
        }

        // Check for candidate modal
        if (modal.classList.contains('candidate-modal-overlay') || 
            modal.classList.contains('emergency-candidate-modal')) {
            if (typeof window.closeCandidateModal === 'function') {
                window.closeCandidateModal();
                return;
            }
            if (typeof window.closeEmergencyModal === 'function') {
                window.closeEmergencyModal();
                return;
            }
        }

        // Fallback: remove modal directly
        this.unregisterModal(modal);
        modal.remove();
    }

    /**
     * Force close all modals
     */
    closeAllModals() {
        this.activeModals.forEach(modal => {
            this.closeModal(modal);
        });
        this.activeModals.clear();
        this.unlockBodyScroll();
    }
}

// Initialize modal manager
const modalManager = new ModalManager();

// Make it globally available
window.modalManager = modalManager;

// ============================================================================
// ENHANCED CLOSE FUNCTIONS WITH BODY SCROLL UNLOCK
// ============================================================================

/**
 * Enhanced close functions that properly unlock body scroll
 */

// History Modal
window.closeHistoryModal = function() {
    const modal = document.getElementById('history-modal');
    if (modal) {
        modal.remove();
    }
    modalManager.unlockBodyScroll();
};

// History Details Modal
window.closeHistoryDetailsModal = function() {
    const modal = document.getElementById('history-details-modal');
    if (modal) {
        modal.remove();
    }
    modalManager.unlockBodyScroll();
};

// JD Library Modal
window.closeJDLibraryModal = function() {
    const modal = document.getElementById('jd-library-modal');
    if (modal) {
        modal.remove();
    }
    modalManager.unlockBodyScroll();
};

// JD Details Modal
window.closeJDDetailsModal = function() {
    const modal = document.getElementById('jd-details-modal');
    if (modal) {
        modal.remove();
    }
    modalManager.unlockBodyScroll();
};

// Interview Questions Modal
window.closeInterviewModal = function() {
    const modal = document.getElementById('interview-questions-modal');
    if (modal) {
        modal.remove();
    }
    modalManager.unlockBodyScroll();
};

// Generic Detailed Modal
window.closeModal = function() {
    const modal = document.getElementById('detailed-modal');
    if (modal) {
        modal.remove();
    }
    modalManager.unlockBodyScroll();
};

// Candidate Modal
window.closeCandidateModal = function() {
    const modal = document.querySelector('.candidate-modal-overlay');
    if (modal) {
        modal.remove();
    }
    modalManager.unlockBodyScroll();
};

// Emergency Candidate Modal
window.closeEmergencyModal = function() {
    const modal = document.querySelector('.emergency-candidate-modal');
    if (modal) {
        modal.remove();
    }
    modalManager.unlockBodyScroll();
};

// ============================================================================
// HELPER FUNCTIONS FOR MODAL DISPLAY
// ============================================================================

/**
 * Show a modal and register it with modal manager
 */
window.showModal = function(modalElement) {
    if (!modalElement) return;
    
    modalElement.style.display = 'flex';
    modalManager.registerModal(modalElement);
};

/**
 * Hide a modal and unregister it
 */
window.hideModal = function(modalElement) {
    if (!modalElement) return;
    
    modalElement.style.display = 'none';
    modalManager.unregisterModal(modalElement);
};

console.log('Universal modal handlers loaded successfully');