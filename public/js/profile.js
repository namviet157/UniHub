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

// Load profile when page loads
document.addEventListener('DOMContentLoaded', () => {
    loadUserProfile();
});