let allDocuments = [];
let filteredDocuments = [];

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const sortSelect = document.getElementById('sortSelect');
    
    loadAllDocuments();
    
    if (searchBtn) {
        searchBtn.addEventListener('click', performSearch);
    }
    
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }
    
    if (sortSelect) {
        sortSelect.addEventListener('change', () => {
            if (filteredDocuments.length > 0) {
                sortDocuments();
                displayDocuments(filteredDocuments);
            }
        });
    }
});

async function loadAllDocuments() {
    try {
        const response = await fetch('/documents/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        allDocuments = await response.json();
        filteredDocuments = [...allDocuments];
        displayDocuments(filteredDocuments);
    } catch (error) {
        console.error('Error loading documents:', error);
        const resultsList = document.getElementById('searchResultsList');
        if (resultsList) {
            resultsList.innerHTML = `
                <div class="error-text" style="text-align: center; padding: 40px; color: var(--error-color);">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Failed to load documents. Please try again later.</p>
                </div>
            `;
        }
    }
}

function performSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchTerm = searchInput ? searchInput.value.trim().toLowerCase() : '';
    
    if (!searchTerm) {
        filteredDocuments = [...allDocuments];
    } else {
        filteredDocuments = allDocuments.filter(doc => {
            const title = (doc.documentTitle || doc.filename || '').toLowerCase();
            const description = (doc.description || '').toLowerCase();
            const course = (doc.course || '').toLowerCase();
            const university = (doc.university || '').toLowerCase();
            const faculty = (doc.faculty || '').toLowerCase();
            const tags = (doc.tags || '').toLowerCase();
            const summary = (doc.summary || '').toLowerCase();
            const keywords = Array.isArray(doc.keywords) 
                ? doc.keywords.map(k => k.toLowerCase()).join(' ')
                : '';
            
            return title.includes(searchTerm) ||
                   description.includes(searchTerm) ||
                   course.includes(searchTerm) ||
                   university.includes(searchTerm) ||
                   faculty.includes(searchTerm) ||
                   tags.includes(searchTerm) ||
                   summary.includes(searchTerm) ||
                   keywords.includes(searchTerm);
        });
    }
    
    sortDocuments();
    displayDocuments(filteredDocuments);
}

function sortDocuments() {
    const sortSelect = document.getElementById('sortSelect');
    const sortBy = sortSelect ? sortSelect.value : 'relevance';
    
    switch (sortBy) {
        case 'recent':
            filteredDocuments.sort((a, b) => {
                const dateA = new Date(a.uploaded_at || 0);
                const dateB = new Date(b.uploaded_at || 0);
                return dateB - dateA;
            });
            break;
        case 'popular':
            filteredDocuments.sort((a, b) => {
                const scoreA = (a.vote_count || 0) * 2 + (a.comment_count || 0);
                const scoreB = (b.vote_count || 0) * 2 + (b.comment_count || 0);
                return scoreB - scoreA;
            });
            break;
        case 'relevance':
        default:
            break;
    }
}

function displayDocuments(documents) {
    const resultsList = document.getElementById('searchResultsList');
    const resultsCount = document.getElementById('resultsCount');
    
    if (!resultsList) return;
    
    if (resultsCount) {
        resultsCount.textContent = `(${documents.length} document${documents.length !== 1 ? 's' : ''} found)`;
    }
    
    if (documents.length === 0) {
        resultsList.innerHTML = `
            <div class="empty-state" style="text-align: center; padding: 60px 20px;">
                <i class="fas fa-search" style="font-size: 64px; color: var(--text-secondary); margin-bottom: 20px;"></i>
                <h3>No documents found</h3>
                <p>Try adjusting your search terms or browse all documents.</p>
                <button class="btn btn-primary" onclick="document.getElementById('searchInput').value=''; performSearch();" style="margin-top: 20px;">
                    Show All Documents
                </button>
            </div>
        `;
        return;
    }
    
    resultsList.innerHTML = '';
    
    documents.forEach(doc => {
        const card = createDocumentCard(doc);
        resultsList.insertAdjacentHTML('beforeend', card);
    });
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
        <div class="document-card-large">
            <div class="document-icon-large">
                <i class="${fileIcon}"></i>
            </div>
            <div class="document-content-large">
                <h3>${title}</h3>
                <p class="document-description">${description}</p>
                <div class="document-meta">
                    ${tagsHTML}
                </div>
                <div class="document-info">
                    <span><i class="far fa-calendar"></i> ${uploadedDate}</span>
                    <span><i class="fas fa-university"></i> ${escapeHtml(doc.university || 'N/A')}</span>
                    <span><i class="fas fa-book"></i> ${escapeHtml(doc.course || 'N/A')}</span>
                    <span><i class="fas fa-arrow-up"></i> ${doc.vote_count || 0} votes</span>
                    ${doc.comment_count ? `<span><i class="fas fa-comment"></i> ${doc.comment_count} comments</span>` : ''}
                </div>
            </div>
            <div class="document-actions-large">
                <a href="/${doc.saved_path}" download class="btn btn-primary">
                    <i class="fas fa-download"></i>
                    Download
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

