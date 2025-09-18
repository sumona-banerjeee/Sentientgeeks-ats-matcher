// Resume upload and processing functions

function handleResumeFilesSelect(event) {
    const files = Array.from(event.target.files);
    const container = document.getElementById('selected-files-list');
    const uploadBtn = document.getElementById('upload-resumes-btn');
    
    if (files.length === 0) {
        container.innerHTML = '';
        uploadBtn.disabled = true;
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
            invalidFiles.push({ file, error: error.message });
        }
    });
    
    // Display file list
    let html = '<h4>Selected Files:</h4>';
    
    if (validFiles.length > 0) {
        html += '<div class="valid-files"><h5>✅ Valid Files:</h5>';
        validFiles.forEach((file, index) => {
            html += `
                <div class="file-item valid">
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">(${(file.size / 1024 / 1024).toFixed(2)} MB)</span>
                    <button type="button" class="btn-remove" onclick="removeFile(${index})">Remove</button>
                </div>
            `;
        });
        html += '</div>';
    }
    
    if (invalidFiles.length > 0) {
        html += '<div class="invalid-files"><h5>❌ Invalid Files:</h5>';
        invalidFiles.forEach(({ file, error }) => {
            html += `
                <div class="file-item invalid">
                    <span class="file-name">${file.name}</span>
                    <span class="file-error">${error}</span>
                </div>
            `;
        });
        html += '</div>';
    }
    
    container.innerHTML = html;
    uploadBtn.disabled = validFiles.length === 0;
    
    // Store valid files for upload
    appState.selectedResumeFiles = validFiles;
    
    if (validFiles.length > 0) {
        Utils.showToast(`${validFiles.length} files ready for upload`, 'success');
    }
    
    if (invalidFiles.length > 0) {
        Utils.showToast(`${invalidFiles.length} files are invalid and will be skipped`, 'warning');
    }
}

function removeFile(index) {
    if (appState.selectedResumeFiles) {
        appState.selectedResumeFiles.splice(index, 1);
        
        // Create new FileList (workaround since FileList is read-only)
        const dt = new DataTransfer();
        appState.selectedResumeFiles.forEach(file => dt.items.add(file));
        document.getElementById('resume-files').files = dt.files;
        
        // Refresh display
        handleResumeFilesSelect({ target: { files: dt.files } });
    }
}

async function uploadResumes() {
    if (!appState.selectedResumeFiles || appState.selectedResumeFiles.length === 0) {
        Utils.showToast('No files selected', 'warning');
        return;
    }
    
    try {
        Utils.showLoading(`Uploading and processing ${appState.selectedResumeFiles.length} resumes...`);
        
        const formData = new FormData();
        appState.selectedResumeFiles.forEach(file => {
            formData.append('files', file);
        });
        
        const response = await fetch(`/api/resumes/upload/${appState.getSessionId()}`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        }
        
        const result = await response.json();
        
        // Store resume data
        appState.resumes = result.resumes;
        
        // Display upload results
        displayUploadResults(result);
        
        // Enable matching if we have successfully processed resumes
        if (result.successfully_processed > 0) {
            appState.nextStep();
            Utils.showToast(`Successfully processed ${result.successfully_processed} out of ${result.total_uploaded} resumes`, 'success');
        } else {
            Utils.showToast('No resumes were successfully processed', 'error');
        }
        
    } catch (error) {
        console.error('Error uploading resumes:', error);
        Utils.showToast(error.message, 'error');
    } finally {
        Utils.hideLoading();
    }
}

function displayUploadResults(result) {
    const container = document.getElementById('selected-files-list');
    
    let html = '<div class="upload-results">';
    html += `<h4>Upload Results</h4>`;
    html += `<p><strong>Total Uploaded:</strong> ${result.total_uploaded}</p>`;
    html += `<p><strong>Successfully Processed:</strong> ${result.successfully_processed}</p>`;
    
    if (result.resumes && result.resumes.length > 0) {
        html += '<div class="resume-results">';
        
        result.resumes.forEach(resume => {
            const statusClass = resume.processing_status === 'success' ? 'success' : 'error';
            html += `
                <div class="resume-result ${statusClass}">
                    <div class="resume-info">
                        <span class="filename">${resume.filename}</span>
                        <span class="status">${resume.processing_status}</span>
                    </div>
            `;
            
            if (resume.processing_status === 'success' && resume.structured_data) {
                html += `
                    <div class="candidate-preview">
                        <p><strong>Name:</strong> ${resume.structured_data.name || 'Not detected'}</p>
                        <p><strong>Experience:</strong> ${resume.structured_data.total_experience || 'Not detected'} years</p>
                        <p><strong>Skills:</strong> ${(resume.structured_data.skills || []).slice(0, 5).join(', ')}${(resume.structured_data.skills || []).length > 5 ? '...' : ''}</p>
                    </div>
                `;
            } else if (resume.error) {
                html += `<div class="error-message">${resume.error}</div>`;
            }
            
            html += '</div>';
        });
        
        html += '</div>';
    }
    
    html += '</div>';
    container.innerHTML = html;
}
