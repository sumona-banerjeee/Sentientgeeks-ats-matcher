// JD Processing specific functions

async function approveStructure() {
    try {
        Utils.showLoading('Approving structure...');
        
        // Get current session data first
        const sessionResponse = await Utils.makeRequest(`/api/jd/session/${appState.getSessionId()}`);
        const currentStructure = sessionResponse.structuring_session?.current_structure;
        
        console.log('Current structure before approval:', currentStructure);
        
        const response = await Utils.makeRequest(`/api/jd/approve-structure/${appState.getSessionId()}`, {
            method: 'POST',
            body: {
                approved: true
            }
        });
        
        if (response.ready_for_skills_weightage) {
            // Store the approved structure
            appState.jdData = response;
            
            // Generate skills weightage form with the current structure
            await generateSkillsWeightageForm(currentStructure);
            appState.nextStep();
            Utils.showToast('Structure approved! Please set skills weightage.', 'success');
        }
        
    } catch (error) {
        console.error('Error approving structure:', error);
        Utils.showToast(error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

async function requestStructureChanges() {
    const feedback = document.getElementById('structure-feedback').value.trim();
    
    if (!feedback) {
        Utils.showToast('Please provide feedback for the changes needed', 'warning');
        return;
    }
    
    if (!appState.getSessionId()) {
        Utils.showToast('Session not found. Please start over.', 'error');
        return;
    }
    
    try {
        Utils.showLoading('Processing your feedback...');
        
        console.log('Sending feedback:', feedback);
        console.log('Session ID:', appState.getSessionId());
        
        const response = await Utils.makeRequest(`/api/jd/approve-structure/${appState.getSessionId()}`, {
            method: 'POST',
            body: {
                approved: false,
                feedback: feedback
            }
        });
        
        console.log('Response from API:', response);
        
        if (response.status === 'revised') {
            // Display revised structure
            displayStructuredJD(response.revised_structure);
            
            // Clear feedback
            document.getElementById('structure-feedback').value = '';
            
            // Show success notification
            showRevisionNotification(response.revision_count);
            
            Utils.showToast(`Structure revised (Revision #${response.revision_count}). Please review the changes.`, 'success');
        } else {
            Utils.showToast('Unexpected response from server', 'warning');
            console.log('Unexpected response:', response);
        }
        
    } catch (error) {
        console.error('Error requesting changes:', error);
        Utils.showToast(`Error: ${error.message}`, 'error');
        
        // Debug information
        console.log('Full error details:', error);
    } finally {
        Utils.hideLoading();
    }
}


function showRevisionNotification(revisionCount) {
    // Remove existing notification
    const existingNotif = document.querySelector('.revision-notification');
    if (existingNotif) {
        existingNotif.remove();
    }
    
    // Create new notification
    const notification = document.createElement('div');
    notification.className = 'revision-notification';
    notification.innerHTML = `Structure revised (Revision #${revisionCount})`;
    
    // Add to page
    const header = document.querySelector('.header .container');
    if (header) {
        header.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
}

async function generateSkillsWeightageForm(structuredData = null) {
    const container = document.getElementById('skills-weightage-form');
    
    try {
        // Get structured data if not provided
        if (!structuredData) {
            const response = await Utils.makeRequest(`/api/jd/session/${appState.getSessionId()}`);
            structuredData = response.jd_data?.structured_data || response.structuring_session?.current_structure;
        }
        
        console.log('Generating skills form with data:', structuredData);
        
        if (!structuredData) {
            container.innerHTML = '<p class="error">No structured data found. Please go back and process the JD again.</p>';
            return;
        }
        
        // Extract all skills
        const allSkills = [];
        
        if (structuredData.primary_skills && Array.isArray(structuredData.primary_skills)) {
            allSkills.push(...structuredData.primary_skills.map(skill => ({ 
                skill: skill.toLowerCase().trim(), 
                display: skill,
                isPrimary: true 
            })));
        }
        
        if (structuredData.secondary_skills && Array.isArray(structuredData.secondary_skills)) {
            allSkills.push(...structuredData.secondary_skills.map(skill => ({ 
                skill: skill.toLowerCase().trim(), 
                display: skill,
                isPrimary: false 
            })));
        }
        
        console.log('Extracted skills:', allSkills);
        
        if (allSkills.length === 0) {
            container.innerHTML = `
                <div class="no-skills-found">
                    <p class="error">❌ No skills found in the job description.</p>
                    <p>The structured data might be incomplete. Please:</p>
                    <ol>
                        <li>Go back to Step 2</li>
                        <li>Review the structured job description</li>
                        <li>Add feedback to include specific skills</li>
                        <li>Click "Request Changes"</li>
                    </ol>
                    <button onclick="goBackToStep2()" class="btn btn-warning">← Go Back to Step 2</button>
                    
                    <div class="manual-skills-entry" style="margin-top: 2rem;">
                        <h4>Or manually add skills:</h4>
                        <textarea id="manual-skills-input" placeholder="Enter skills separated by commas (e.g., Python, JavaScript, SQL, React)" rows="3" style="width: 100%; margin: 1rem 0;"></textarea>
                        <button onclick="processManualSkills()" class="btn btn-primary">Add Skills Manually</button>
                    </div>
                </div>
            `;
            return;
        }
        
        // Remove duplicates based on skill name
        const uniqueSkills = allSkills.filter((skill, index, self) => 
            index === self.findIndex(s => s.skill === skill.skill)
        );
        
        // Generate form HTML
        let html = '<div class="skills-weightage-header">';
        html += `<p class="skills-count">Found <strong>${uniqueSkills.length} skills</strong> in the job description:</p>`;
        html += '</div>';
        
        html += '<div class="skills-weightage-grid">';
        
        uniqueSkills.forEach((skillData, index) => {
            //const defaultWeight = skillData.isPrimary ? 10 : 5;
            const defaultWeight = 0; // First time load, everything is 0

            html += `
                <div class="skill-input-group">
                    <label for="skill-${index}">${skillData.display}</label>
                    <input type="number" 
                           id="skill-${index}" 
                           name="${skillData.skill}" 
                           value="${defaultWeight}" 
                           min="1" 
                           max="100" 
                           data-skill="${skillData.skill}" onkeyup="weightValidation()">
                    <span class="skill-type ${skillData.isPrimary ? 'primary' : 'secondary'}">
                        ${skillData.isPrimary ? 'Primary' : 'Secondary'}
                    </span>
                </div>
            `;
        });
        
        html += '</div>';
        
        html += '<div class="weightage-controls">';
        html += '<div class="weightage-summary"><p><strong>Total Weightage: </strong><span id="total-weightage">0</span>%</p></div>';
        html += '<div class="weightage-actions">';
        html += '<button onclick="resetWeights()" class="btn btn-secondary">Reset Weights</button>';
        html += '<button onclick="autoSetWeights()" class="btn btn-secondary">Auto-Set Weights</button>';
        html += '</div>';
        html += '</div>';
        
        html += '<div class="weightage-note"><p><em>💡 Tip: Higher weights mean more importance in matching. Primary skills get higher default weights.</em></p></div>';
        
        container.innerHTML = html;
        
        // Add event listeners for real-time total calculation
        container.querySelectorAll('input[type="number"]').forEach(input => {
            input.addEventListener('input', updateTotalWeightage);
            input.addEventListener('change', updateTotalWeightage);
        });
        
        // Initial calculation
        updateTotalWeightage();
        
        console.log(`✅ Skills weightage form generated with ${uniqueSkills.length} skills`);
        
    } catch (error) {
        console.error('Error generating skills form:', error);
        container.innerHTML = `
            <div class="error-container">
                <p class="error">Error generating skills form: ${error.message}</p>
                <button onclick="generateSkillsWeightageForm()" class="btn btn-warning">Try Again</button>
                <button onclick="goBackToStep2()" class="btn btn-secondary">← Go Back to Step 2</button>
            </div>
        `;
    }
}


// Weightage validation within 100
function weightValidation(){

 let total = 0;
 let inputs =  document.querySelectorAll(".skill-input-group input[type = 'number']");
console.log(inputs);
 inputs.forEach( input => {
    let val = parseInt(input.value) || 0;
    total += val;
});


let totalEl = document.getElementById("total-weightage");
totalEl.innerText = total;
if(total>100){
    alert("Total weightage can not exceed 100!!!");

let lastInput = event.target;
console.log(lastInput)
lastInput.value = 0;

total = 0;
inputs.forEach(input => {
    total += parseInt(input.value) || 0;
});

totalEl.innerText = total;
}
}

function processManualSkills() {
    const skillsInput = document.getElementById('manual-skills-input').value.trim();
    
    if (!skillsInput) {
        Utils.showToast('Please enter some skills', 'warning');
        return;
    }
    
    // Parse skills from input
    const skills = skillsInput.split(',').map(s => s.trim()).filter(s => s.length > 0);
    
    if (skills.length === 0) {
        Utils.showToast('No valid skills found', 'warning');
        return;
    }
    
    // Create mock structured data with manual skills
    const mockStructuredData = {
        primary_skills: skills.slice(0, Math.ceil(skills.length / 2)),
        secondary_skills: skills.slice(Math.ceil(skills.length / 2))
    };
    
    // Generate form with manual skills
    generateSkillsWeightageForm(mockStructuredData);
    
    Utils.showToast(`Added ${skills.length} skills manually`, 'success');
}




function resetWeights() {
    const inputs = document.querySelectorAll('#skills-weightage-form input[type="number"]');
    const totalInputs = inputs.length;
    if (totalInputs === 0) return;

    const evenWeight = Math.floor(100 / totalInputs); // distribute evenly
    let remaining = 100;

    inputs.forEach((input, index) => {
        if (index === totalInputs - 1) {
            input.value = remaining; // last one gets remainder
        } else {
            input.value = evenWeight;
            remaining -= evenWeight;
        }
    });

    updateTotalWeightage();
    Utils.showToast('Weights reset evenly to total 100', 'info');
}






function autoSetWeights() {
    const inputs = document.querySelectorAll('#skills-weightage-form input[type="number"]');
    if (inputs.length === 0) return;

    let primaryInputs = [];
    let secondaryInputs = [];

    inputs.forEach(input => {
        const skillGroup = input.closest('.skill-input-group');
        const isPrimary = skillGroup.querySelector('.skill-type.primary');
        if (isPrimary) {
            primaryInputs.push(input);
        } else {
            secondaryInputs.push(input);
        }
    });

    // Let's say: 70% to primary, 30% to secondary
    let primaryTotal = Math.floor(100 * 0.7);
    let secondaryTotal = 100 - primaryTotal;

    // Distribute primary weights
    if (primaryInputs.length > 0) {
        const perPrimary = Math.floor(primaryTotal / primaryInputs.length);
        let remaining = primaryTotal;
        primaryInputs.forEach((input, index) => {
            if (index === primaryInputs.length - 1) {
                input.value = remaining;
            } else {
                input.value = perPrimary;
                remaining -= perPrimary;
            }
        });
    }

    // Distribute secondary weights
    if (secondaryInputs.length > 0) {
        const perSecondary = Math.floor(secondaryTotal / secondaryInputs.length);
        let remaining = secondaryTotal;
        secondaryInputs.forEach((input, index) => {
            if (index === secondaryInputs.length - 1) {
                input.value = remaining;
            } else {
                input.value = perSecondary;
                remaining -= perSecondary;
            }
        });
    }

    updateTotalWeightage();
    Utils.showToast('Weights auto-distributed (total = 100)', 'success');
}





function updateTotalWeightage() {
    const inputs = document.querySelectorAll('#skills-weightage-form input[type="number"]');
    let total = 0;
    
    inputs.forEach(input => {
        total += parseInt(input.value) || 0;
    });
    
    const totalElement = document.getElementById('total-weightage');
    if (totalElement) {
        totalElement.textContent = total;
        
        // Add visual feedback for total
        totalElement.className = '';
        if (total > 200) {
            totalElement.classList.add('high-total');
        } else if (total < 50) {
            totalElement.classList.add('low-total');
        } else {
            totalElement.classList.add('good-total');
        }
    }
}

async function setSkillsWeightage() {
    const inputs = document.querySelectorAll('#skills-weightage-form input[type="number"]');
    const skillsData = {};
    let totalSkills = 0;
    
    inputs.forEach(input => {
        const skill = input.getAttribute('data-skill');
        const weight = parseInt(input.value) || 0;
        if (weight > 0 && skill) {
            skillsData[skill] = weight;
            totalSkills++;
        }
    });
    
    if (totalSkills === 0) {
        Utils.showToast('Please set at least one skill weightage greater than 0', 'warning');
        return;
    }
    
    try {
        Utils.showLoading(`Setting weightage for ${totalSkills} skills...`);
        
        const response = await Utils.makeRequest(`/api/jd/set-skills-weightage/${appState.getSessionId()}`, {
            method: 'POST',
            body: skillsData
        });
        
        if (response.ready_for_resume_upload) {
            appState.nextStep();
            Utils.showToast(`Skills weightage set for ${totalSkills} skills!`, 'success');
            
            // Store skills data for later use
            appState.skillsWeightage = skillsData;
            console.log('Skills weightage saved:', skillsData);
        }
        
    } catch (error) {
        console.error('Error setting skills weightage:', error);
        Utils.showToast(error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

function displayStructuredJD(structuredData) {
    const container = document.getElementById('structured-jd-display');
    
    if (!structuredData || Object.keys(structuredData).length === 0) {
        container.innerHTML = `
            <div class="empty-structure">
                <p class="error">No structured data available.</p>
                <p>Please provide feedback below to help structure the job description properly.</p>
            </div>
        `;
        return;
    }
    
    let html = '<div class="structured-jd">';
    html += '<h3>📋 Structured Job Description</h3>';
    
    // Job Title
    if (structuredData.job_title) {
        html += `<div class="jd-field">
            <strong>🎯 Job Title:</strong> 
            <span>${structuredData.job_title}</span>
        </div>`;
    }
    
    // Company
    if (structuredData.company) {
        html += `<div class="jd-field">
            <strong>🏢 Company:</strong> 
            <span>${structuredData.company}</span>
        </div>`;
    }
    
    // Location
    if (structuredData.location) {
        html += `<div class="jd-field">
            <strong>📍 Location:</strong> 
            <span>${structuredData.location}</span>
        </div>`;
    }
    
    // Job Type
    if (structuredData.job_type) {
        html += `<div class="jd-field">
            <strong>💼 Job Type:</strong> 
            <span>${structuredData.job_type}</span>
        </div>`;
    }
    
    // Experience Required
    if (structuredData.experience_required) {
        html += `<div class="jd-field">
            <strong>⏱️ Experience Required:</strong> 
            <span>${structuredData.experience_required}</span>
        </div>`;
    }
    
    // Primary Skills
    if (structuredData.primary_skills && Array.isArray(structuredData.primary_skills) && structuredData.primary_skills.length > 0) {
        html += '<div class="jd-field skills-field primary-skills">';
        html += '<strong>🔥 Primary Skills:</strong>';
        html += '<div class="skills-tags">';
        structuredData.primary_skills.forEach(skill => {
            html += `<span class="skill-tag primary">${skill}</span>`;
        });
        html += '</div></div>';
    }
    
    // Secondary Skills
    if (structuredData.secondary_skills && Array.isArray(structuredData.secondary_skills) && structuredData.secondary_skills.length > 0) {
        html += '<div class="jd-field skills-field secondary-skills">';
        html += '<strong>⭐ Secondary Skills:</strong>';
        html += '<div class="skills-tags">';
        structuredData.secondary_skills.forEach(skill => {
            html += `<span class="skill-tag secondary">${skill}</span>`;
        });
        html += '</div></div>';
    }
    
    // Responsibilities
    if (structuredData.responsibilities && Array.isArray(structuredData.responsibilities) && structuredData.responsibilities.length > 0) {
        html += '<div class="jd-field"><strong>📋 Key Responsibilities:</strong><ul>';
        structuredData.responsibilities.forEach(resp => {
            html += `<li>${resp}</li>`;
        });
        html += '</ul></div>';
    }
    
    // Qualifications
    if (structuredData.qualifications && Array.isArray(structuredData.qualifications) && structuredData.qualifications.length > 0) {
        html += '<div class="jd-field"><strong>🎓 Qualifications:</strong><ul>';
        structuredData.qualifications.forEach(qual => {
            html += `<li>${qual}</li>`;
        });
        html += '</ul></div>';
    }
    
    // Summary stats
    const primarySkillsCount = (structuredData.primary_skills && Array.isArray(structuredData.primary_skills)) ? structuredData.primary_skills.length : 0;
    const secondarySkillsCount = (structuredData.secondary_skills && Array.isArray(structuredData.secondary_skills)) ? structuredData.secondary_skills.length : 0;
    const totalSkills = primarySkillsCount + secondarySkillsCount;
    
    if (totalSkills > 0) {
        html += `<div class="jd-summary">
            <strong>📊 Skills Summary:</strong> 
            ${totalSkills} total skills (${primarySkillsCount} primary, ${secondarySkillsCount} secondary)
        </div>`;
    }
    
    // Show raw data in collapsible section for debugging
    html += `<details class="debug-section" style="margin-top: 1rem;">
        <summary style="cursor: pointer; color: #666; font-size: 0.9rem;">🔧 Debug Info (Click to expand)</summary>
        <pre style="background: #f5f5f5; padding: 1rem; border-radius: 4px; overflow-x: auto; font-size: 0.8rem;">${JSON.stringify(structuredData, null, 2)}</pre>
    </details>`;
    
    html += '</div>';
    
    container.innerHTML = html;
    
    console.log('✅ Structured JD displayed:', structuredData);
    console.log(`Found ${totalSkills} skills total`);
}

// Helper functions
function goBackToStep2() {
    appState.currentStep = 2;
    appState.updateUI();
    Utils.showToast('Returned to Step 2', 'info');
}

function goBackToStep1() {
    appState.currentStep = 1;
    appState.updateUI();
    Utils.showToast('Returned to Step 1', 'info');
}

// Validation function for JD processing
function validateJobDescriptionData(jdData) {
    const required = ['job_title', 'primary_skills'];
    const missing = [];
    
    required.forEach(field => {
        if (!jdData[field] || (Array.isArray(jdData[field]) && jdData[field].length === 0)) {
            missing.push(field);
        }
    });
    
    return {
        isValid: missing.length === 0,
        missingFields: missing
    };
}