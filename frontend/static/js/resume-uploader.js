// Resume upload and processing functions - FIXED VERSION

/**
 * Safety function to ensure skills is always an array
 */
function normalizeSkills(skills) {
    if (!skills) {
        return [];
    }
    
    if (Array.isArray(skills)) {
        return skills;
    }
    
    if (typeof skills === 'object') {
        return Object.values(skills);
    }
    
    if (typeof skills === 'string') {
        return skills.split(',').map(s => s.trim()).filter(s => s.length > 0);
    }
    
    return [];
}


function handleResumeFilesSelect(event) {
    const files = Array.from(event.target.files);
    const container = document.getElementById('selected-files-list');
    const uploadBtn = document.getElementById('upload-resumes-btn');
    
    console.log(`📁 Files selected: ${files.length}`);
    
    if (files.length === 0) {
        if (container) container.innerHTML = '';
        if (uploadBtn) uploadBtn.disabled = true;
        return;
    }
    
    // Check max limit
    const MAX_FILES = 500;
    if (files.length > MAX_FILES) {
        Utils.showToast(`Too many files! Maximum ${MAX_FILES} resumes allowed per upload.`, 'error');
        event.target.value = ''; // Clear selection
        return;
    }
    
    // Validate files
    const validFiles = [];
    const invalidFiles = [];
    
    files.forEach(file => {
        try {
            Utils.validateFile(file);
            validFiles.push(file);
        } catch (error) {
            invalidFiles.push({
                file,
                error: error.message
            });
        }
    });
    
    console.log(`✅ Valid files: ${validFiles.length}, ❌ Invalid: ${invalidFiles.length}`);
    
    // Display file list summary
    let html = `<div style="margin-top: 20px;">`;
    html += `<h4 style="margin-bottom: 15px; color: #333;">Selected Files: ${files.length}</h4>`;
    
    if (validFiles.length > 0) {
        const totalSize = validFiles.reduce((sum, file) => sum + file.size, 0);
        const totalSizeMB = (totalSize / (1024 * 1024)).toFixed(2);
        
        html += `
            <div class="valid-files" style="background: #d4edda; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #28a745;">
                <h5 style="color: #155724; margin: 0 0 15px 0; font-size: 16px;">✅ Valid Files: ${validFiles.length}</h5>
                <p style="margin: 5px 0; color: #155724;"><strong>Total Size:</strong> ${totalSizeMB} MB</p>
                
                <!-- File Details (Show first 10) -->
                <div style="margin-top: 15px; max-height: 300px; overflow-y: auto;">
                    <strong style="color: #155724; display: block; margin-bottom: 10px;">File Names:</strong>
                    <ul style="margin: 0; padding-left: 20px; color: #155724;">
        `;
        
        // Show first 10 files, then summarize rest
        validFiles.slice(0, 10).forEach((file, index) => {
            const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
            html += `
                <li style="margin: 5px 0; font-size: 13px; line-height: 1.6;">
                    <strong>${index + 1}.</strong> ${file.name} 
                    <span style="color: #666; font-size: 12px;">(${fileSizeMB} MB)</span>
                </li>
            `;
        });
        
        if (validFiles.length > 10) {
            html += `
                <li style="margin: 5px 0; font-style: italic; color: #666;">
                    ... and ${validFiles.length - 10} more files
                </li>
            `;
        }
        
        html += `
                    </ul>
                </div>
                <p style="margin: 15px 0 0 0; font-size: 13px; color: #155724; background: rgba(40, 167, 69, 0.1); padding: 10px; border-radius: 4px;">
                    📦 Files will be processed in batches of 10 for optimal performance.
                </p>
            </div>
        `;
    }
    
    if (invalidFiles.length > 0) {
        html += `
            <div class="invalid-files" style="background: #f8d7da; padding: 15px; border-radius: 8px; border-left: 4px solid #dc3545;">
                <h5 style="color: #721c24; margin: 0 0 10px 0;">❌ Invalid Files: ${invalidFiles.length}</h5>
                <ul style="margin: 0; padding-left: 20px; color: #721c24;">
        `;
        invalidFiles.forEach(item => {
            html += `<li style="margin: 5px 0; font-size: 13px;">${item.file.name} - ${item.error}</li>`;
        });
        html += `
                </ul>
            </div>
        `;
    }
    
    html += `</div>`;
    
    if (container) {
        container.innerHTML = html;
        console.log('✅ File list displayed successfully');
    } else {
        console.warn('⚠️ Container #selected-files-list not found');
    }
    
    if (uploadBtn) {
        uploadBtn.disabled = validFiles.length === 0;
        uploadBtn.dataset.validFileCount = validFiles.length;
        
        if (validFiles.length > 0) {
            uploadBtn.textContent = `Upload & Process ${validFiles.length} Resume(s)`;
        } else {
            uploadBtn.textContent = 'Upload & Process Resumes';
        }
    }
}


async function uploadAndProcessResumes() {
    const fileInput = document.getElementById('resume-files');
    const uploadBtn = document.getElementById('upload-resumes-btn');
    const files = Array.from(fileInput.files);
    
    if (files.length === 0) {
        Utils.showToast('Please select at least one resume file', 'error');
        return;
    }
    
    // ✅ PREVENT DOUBLE CLICKS
    if (uploadBtn.disabled) {
        console.log('Upload already in progress...');
        return;
    }
    
    try {
        // ✅ DISABLE BUTTON IMMEDIATELY
        uploadBtn.disabled = true;
        uploadBtn.textContent = 'Uploading...';
        uploadBtn.style.opacity = '0.6';
        uploadBtn.style.cursor = 'not-allowed';
        
        Utils.showLoading(`Processing ${files.length} resume(s)...`);
        
        const formData = new FormData();
        const sessionId = appState.getSessionId();
        
        if (!sessionId) {
            throw new Error('Session ID not found');
        }
        
        files.forEach(file => {
            formData.append('files', file);
        });
        
        const response = await fetch(`/api/resumes/upload/${sessionId}`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        const result = await response.json();
        
        displayResumeUploadResult(result);
        Utils.hideLoading();
        
        let message = `Successfully processed ${result.successfully_processed} resume(s)!`;
        if (result.skipped_count > 0) {
            message += ` (${result.skipped_count} duplicates skipped)`;
        }
        
        Utils.showToast(message, 'success');
        
        // Clear input
        fileInput.value = '';
        document.getElementById('selected-files-list').innerHTML = '';
        
    } catch (error) {
        console.error('Upload error:', error);
        Utils.hideLoading();
        Utils.showToast(`Upload failed: ${error.message}`, 'error');
    } finally {
        // RE-ENABLE BUTTON
        uploadBtn.disabled = false;
        uploadBtn.textContent = 'Upload & Process Resumes';
        uploadBtn.style.opacity = '1';
        uploadBtn.style.cursor = 'pointer';
    }
}


/**
 * Display resume upload results with safe skills handling
 * FIXED: Safe DOM manipulation, no innerHTML errors
 */
function displayResumeUploadResult(result) {
    // Try multiple possible containers
    let container = document.getElementById('resumes-list') 
                 || document.getElementById('results-content')
                 || document.querySelector('#resume-section .card');
    
    if (!container) {
        console.warn('No suitable container found for resume results');
        // Show toast notification instead
        Utils.showToast(`${result.successfully_processed || 0} resumes uploaded successfully!`, 'success');
        return;
    }
    
    let html = `
        <div class="upload-success" style="background: #d4edda; border: 1px solid #c3e6cb; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <h3 style="color: #155724; margin-bottom: 10px;">✅ Resumes Uploaded Successfully!</h3>
            <p><strong>Total Uploaded:</strong> ${result.total_uploaded || 0}</p>
    `;
    
    if (result.skipped_count && result.skipped_count > 0) {
        html += `<p><strong>Duplicates Skipped:</strong> ${result.skipped_count}</p>`;
    }
    
    html += `</div>`;
    
    if (result.resumes && result.resumes.length > 0) {
        html += `
            <div class="resume-cards" style="margin-top: 20px;">
                <p style="font-weight: 600; margin-bottom: 15px;"><strong>Successfully Processed:</strong> ${result.successfully_processed || result.resumes.length}</p>
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px;">
        `;
        
        result.resumes.forEach((resume, index) => {
            const name = resume.structured_data?.name || 'Not detected';
            const experience = resume.structured_data?.total_experience || 'Not detected';
            const email = resume.structured_data?.email || 'Not detected';
            const phone = resume.structured_data?.phone || 'Not detected';
            
            // SAFE SKILLS HANDLING
            let skillsPreview = 'Not detected';
            if (resume.structured_data && resume.structured_data.skills) {
                const skills = normalizeSkills(resume.structured_data.skills);
                if (skills && skills.length > 0) {
                    skillsPreview = skills.slice(0, 5).join(', ');
                    if (skills.length > 5) {
                        skillsPreview += ` (+${skills.length - 5} more)`;
                    }
                }
            }
            
            html += `
                <div class="resume-card" style="background: white; border: 1px solid #ddd; border-radius: 8px; padding: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding-bottom: 10px; border-bottom: 2px solid #f0f0f0;">
                        <span style="background: #667eea; color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600;">#${index + 1}</span>
                        <span style="font-size: 11px; color: #666; font-family: monospace;">${resume.filename}</span>
                    </div>
                    <div style="font-size: 13px; line-height: 1.8;">
                        <p><strong>Name:</strong> ${name}</p>
                        <p><strong>Email:</strong> ${email}</p>
                        <p><strong>Phone:</strong> ${phone}</p>
                        <p><strong>Experience:</strong> ${experience}${experience !== 'Not detected' ? ' years' : ''}</p>
                        <p><strong>Skills:</strong> ${skillsPreview}</p>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    }
    
    if (result.failed && result.failed.length > 0) {
        html += `
            <div class="upload-errors" style="background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px; padding: 15px; margin-top: 20px;">
                <h4 style="color: #721c24; margin-bottom: 10px;">❌ Failed to Process (${result.failed.length})</h4>
                <ul style="color: #721c24; margin: 0; padding-left: 20px;">
        `;
        
        result.failed.forEach(failed => {
            html += `<li>${failed.filename}: ${failed.error}</li>`;
        });
        
        html += `
                </ul>
            </div>
        `;
    }
    
    // Safe innerHTML assignment
    try {
        container.innerHTML = html;
        console.log('✅ Resume results displayed successfully');
    } catch (e) {
        console.error('❌ Error displaying results:', e);
        Utils.showToast('Results processed but display error occurred', 'warning');
    }
}


/**
 * Initialize event listeners when DOM is ready
 */
function initResumeUploader() {
    const fileInput = document.getElementById('resume-files');
    const uploadBtn = document.getElementById('upload-resumes-btn');
    
    if (fileInput) {
        fileInput.addEventListener('change', handleResumeFilesSelect);
        console.log('✅ Resume file input listener attached');
    } else {
        console.warn('⚠️ Resume file input not found');
    }
    
    if (uploadBtn) {
        uploadBtn.addEventListener('click', uploadAndProcessResumes);
        console.log('✅ Resume upload button listener attached');
    } else {
        console.warn('⚠️ Resume upload button not found');
    }
}


// Event listeners
document.addEventListener('DOMContentLoaded', initResumeUploader);

// Also initialize if DOM is already loaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initResumeUploader);
} else {
    initResumeUploader();
}