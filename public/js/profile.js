// Load user profile data
async function loadUserProfile() {
    const token = getToken();
    
    if (!token) {
        // Redirect to login if not authenticated
        window.location.href = 'login.html';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/me`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            if (response.status === 401) {
                // Token expired or invalid
                removeToken();
                window.location.href = 'login.html';
                return;
            }
            throw new Error('Failed to load profile');
        }
        
        const userData = await response.json();
        
        // Update user name
        const fullnameElement = document.getElementById('userFullname');
        if (fullnameElement) {
            fullnameElement.textContent = userData.fullname || 'User';
        }
        
        // Update university - need to map ID to name
        const universityElement = document.getElementById('userUniversity');
        if (universityElement) {
            const universityName = await getUniversityName(userData.university);
            universityElement.textContent = universityName || userData.university || 'Not specified';
        }
        
        // Update major - only show if exists
        const majorElement = document.getElementById('userMajor');
        const majorContainer = document.getElementById('userMajorContainer');
        if (majorElement && majorContainer) {
            if (userData.major && userData.major.trim()) {
                majorElement.textContent = userData.major;
                majorContainer.style.display = 'block';
            } else {
                majorContainer.style.display = 'none';
            }
        }
        
        // Update avatar if available
        const avatarImg = document.querySelector('.profile-avatar img');
        if (avatarImg && userData.avatar_url) {
            avatarImg.src = userData.avatar_url;
            avatarImg.onerror = function() {
                this.onerror = null;
                this.src = './data/avatars/default-avatar.png';
            };
        } else if (avatarImg) {
            // Set default avatar if no avatar_url
            avatarImg.src = './data/avatars/default-avatar.png';
        }
        
    } catch (error) {
        console.error('Error loading profile:', error);
        // Show error but don't redirect
        const fullnameElement = document.getElementById('userFullname');
        if (fullnameElement) {
            fullnameElement.textContent = 'Error loading profile';
        }
    }
}

// Get university name from ID
async function getUniversityName(universityId) {
    if (!universityId) return null;
    
    try {
        // Try to load from universities.json
        const response = await fetch('./data/universities.json');
        if (response.ok) {
            const data = await response.json();
            const university = data.universities.find(uni => uni.id === universityId);
            return university ? university.name : universityId;
        }
    } catch (error) {
        console.error('Error loading universities:', error);
    }
    
    // Fallback: return ID if can't find name
    return universityId;
}

// Load documents for each tab
async function loadMyUploads() {
    const token = getToken();
    if (!token) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/my-uploads`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load uploads');
        }
        
        const documents = await response.json();
        displayDocuments(documents, 'uploads');
    } catch (error) {
        console.error('Error loading uploads:', error);
        document.getElementById('uploads').querySelector('.document-list').innerHTML = 
            '<p class="error-text">Failed to load documents. Please try again.</p>';
    }
}

async function loadMyDownloads() {
    const token = getToken();
    if (!token) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/my-downloads`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load downloads');
        }
        
        const documents = await response.json();
        displayDocuments(documents, 'downloads');
    } catch (error) {
        console.error('Error loading downloads:', error);
        document.getElementById('downloads').querySelector('.document-list').innerHTML = 
            '<p class="error-text">Failed to load documents. Please try again.</p>';
    }
}

async function loadMyFavorites() {
    const token = getToken();
    if (!token) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/my-favorites`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to load favorites');
        }
        
        const documents = await response.json();
        displayDocuments(documents, 'favorites');
    } catch (error) {
        console.error('Error loading favorites:', error);
        const favoritesTab = document.getElementById('favorites');
        if (favoritesTab) {
            favoritesTab.innerHTML = `
                <div class="section-header">
                    <h2>Favorite Documents</h2>
                </div>
                <div class="empty-state">
                    <i class="fas fa-heart"></i>
                    <h3>No favorites yet</h3>
                    <p>Start adding documents to your favorites by clicking the heart icon</p>
                    <a href="explorer.html" class="btn btn-primary">Browse Documents</a>
                </div>
            `;
        }
    }
}

function displayDocuments(documents, tabId) {
    const tabContent = document.getElementById(tabId);
    if (!tabContent) return;
    
    const documentList = tabContent.querySelector('.document-list');
    if (!documentList) return;
    
    if (documents.length === 0) {
        if (tabId === 'uploads') {
            documentList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-upload"></i>
                    <h3>No uploads yet</h3>
                    <p>Start sharing your documents with the community</p>
                    <a href="upload.html" class="btn btn-primary">Upload Document</a>
                </div>
            `;
        } else if (tabId === 'downloads') {
            documentList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-download"></i>
                    <h3>No downloads yet</h3>
                    <p>Download documents to access them here</p>
                    <a href="explorer.html" class="btn btn-primary">Browse Documents</a>
                </div>
            `;
        } else if (tabId === 'favorites') {
            documentList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-heart"></i>
                    <h3>No favorites yet</h3>
                    <p>Start adding documents to your favorites by clicking the heart icon</p>
                    <a href="explorer.html" class="btn btn-primary">Browse Documents</a>
                </div>
            `;
        }
        return;
    }
    
    let html = '';
    documents.forEach(doc => {
        const uploadedDate = doc.uploaded_at ? formatDate(doc.uploaded_at) : 'Unknown date';
        const fileIcon = getFileIcon(doc.content_type || doc.filename);
        
        html += `
            <div class="document-card-large">
                <div class="document-icon-large">
                    <i class="${fileIcon}"></i>
                </div>
                <div class="document-content-large">
                    <h3>${escapeHtml(doc.documentTitle || doc.filename)}</h3>
                    <p class="document-description">${escapeHtml(doc.description || 'No description')}</p>
                    <div class="document-meta">
                        ${doc.university ? `<span class="tag">${escapeHtml(doc.university)}</span>` : ''}
                        ${doc.course ? `<span class="tag">${escapeHtml(doc.course)}</span>` : ''}
                        ${doc.documentType ? `<span class="tag">${escapeHtml(doc.documentType)}</span>` : ''}
                    </div>
                    <div class="document-info">
                        <span><i class="far fa-calendar"></i> ${uploadedDate}</span>
                        <span><i class="fas fa-download"></i> ${doc.download_count || 0} downloads</span>
                        <span><i class="fas fa-arrow-up"></i> ${doc.vote_count || 0} upvotes</span>
                        ${doc.comment_count ? `<span><i class="fas fa-comment"></i> ${doc.comment_count} comments</span>` : ''}
                    </div>
                </div>
                <div class="document-actions-large">
                    ${tabId === 'uploads' ? `
                        <a href="/${doc.saved_path}" download class="btn btn-primary">
                            <i class="fas fa-download"></i>
                            Download
                        </a>
                        <button class="btn btn-danger" onclick="deleteDocument('${doc.id}')">
                            <i class="fas fa-trash"></i>
                        </button>
                    ` : `
                        <a href="/${doc.saved_path}" download class="btn btn-primary">
                            <i class="fas fa-download"></i>
                            Download
                        </a>
                    `}
                </div>
            </div>
        `;
    });
    
    documentList.innerHTML = html;
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

// Global function for tab switching (called from HTML)
function switchTab(event, tabName) {
    const tabContents = document.querySelectorAll('.tab-content');
    const tabBtns = document.querySelectorAll('.tab-btn');

    tabContents.forEach(content => content.classList.remove('active'));
    tabBtns.forEach(btn => btn.classList.remove('active'));

    document.getElementById(tabName).classList.add('active');
    event.currentTarget.classList.add('active');
    
    // Load documents when tab is switched
    if (tabName === 'uploads') {
        loadMyUploads();
    } else if (tabName === 'downloads') {
        loadMyDownloads();
    } else if (tabName === 'favorites') {
        loadMyFavorites();
    }
}

// Load profile when page loads
document.addEventListener('DOMContentLoaded', () => {
    loadUserProfile();
    // Load uploads by default
    loadMyUploads();
});