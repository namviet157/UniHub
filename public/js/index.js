async function loadRecommendations() {
    const grid = document.getElementById('recommendationsGrid');
    if (!grid) return;
    
    try {
        const response = await fetch('/documents/');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const documents = await response.json();
        
        const recommendations = documents.slice(0, 6);
        
        if (recommendations.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column: 1 / -1; text-align: center; padding: 40px;">
                    <i class="fas fa-file-alt" style="font-size: 48px; color: var(--text-secondary); margin-bottom: 16px;"></i>
                    <h3>No documents available</h3>
                    <p>Be the first to share a document!</p>
                    <a href="upload.html" class="btn btn-primary" style="margin-top: 16px;">Upload Document</a>
                </div>
            `;
            return;
        }
        
        grid.innerHTML = '';
        
        recommendations.forEach(doc => {
            const card = createDocumentCard(doc);
            grid.insertAdjacentHTML('beforeend', card);
        });
        
    } catch (error) {
        console.error('Error loading recommendations:', error);
        grid.innerHTML = `
            <div class="error-text" style="grid-column: 1 / -1; text-align: center; padding: 20px; color: var(--error-color);">
                <i class="fas fa-exclamation-triangle"></i>
                <p>Failed to load recommendations. Please try again later.</p>
            </div>
        `;
    }
}

function createDocumentCard(doc) {
    const uploadedDate = formatDate(doc.uploaded_at);
    const fileIcon = getFileIcon(doc.content_type || doc.filename);
    const title = escapeHtml(doc.documentTitle || doc.filename);
    const description = escapeHtml(doc.description || 'No description available');
    
    let tagsHTML = '';
    if (doc.university) {
        tagsHTML += `<span class="tag">${escapeHtml(doc.university)}</span>`;
    }
    if (doc.course) {
        tagsHTML += `<span class="tag">${escapeHtml(doc.course)}</span>`;
    }
    if (doc.documentType) {
        tagsHTML += `<span class="tag">${escapeHtml(doc.documentType)}</span>`;
    }
    
    return `
        <div class="document-card">
            <div class="document-icon">
                <i class="${fileIcon}"></i>
            </div>
            <div class="document-content">
                <h3>${title}</h3>
                <div class="document-meta">
                    ${tagsHTML}
                </div>
                <div class="document-info">
                    <span><i class="far fa-calendar"></i> ${uploadedDate}</span>
                    <span><i class="fas fa-arrow-up"></i> ${doc.vote_count || 0}</span>
                    ${doc.comment_count ? `<span><i class="fas fa-comment"></i> ${doc.comment_count}</span>` : ''}
                </div>
            </div>
            <div class="document-actions">
                <a href="/${doc.saved_path}" download class="icon-btn" title="Download">
                    <i class="fas fa-download"></i>
                </a>
            </div>
        </div>
    `;
}

function formatDate(dateString) {
    if (!dateString) return 'Unknown date';
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
        if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
        return `${Math.floor(diffDays / 365)} years ago`;
    } catch (e) {
        return dateString;
    }
}

function getFileIcon(contentTypeOrFilename) {
    if (!contentTypeOrFilename) return 'fas fa-file';
    const lower = contentTypeOrFilename.toLowerCase();
    if (lower.includes('pdf')) return 'fas fa-file-pdf';
    if (lower.includes('word') || lower.includes('doc')) return 'fas fa-file-word';
    if (lower.includes('excel') || lower.includes('xls')) return 'fas fa-file-excel';
    if (lower.includes('powerpoint') || lower.includes('ppt')) return 'fas fa-file-powerpoint';
    if (lower.includes('image')) return 'fas fa-file-image';
    return 'fas fa-file';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', () => {
    loadRecommendations();
});

