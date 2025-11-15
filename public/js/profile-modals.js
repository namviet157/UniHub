// Profile Modals and Settings Management

// Modal Management
const editProfileModal = document.getElementById('editProfileModal');
const settingsModal = document.getElementById('settingsModal');
const editProfileBtn = document.getElementById('editProfileBtn');
const settingsBtn = document.getElementById('settingsBtn');
const closeEditModal = document.getElementById('closeEditModal');
const closeSettingsModal = document.getElementById('closeSettingsModal');
const cancelEditBtn = document.getElementById('cancelEditBtn');
const cancelSettingsBtn = document.getElementById('cancelSettingsBtn');

// Edit Profile Modal
if (editProfileBtn) {
    editProfileBtn.addEventListener('click', () => {
        openEditProfileModal();
    });
}

if (closeEditModal || cancelEditBtn) {
    [closeEditModal, cancelEditBtn].forEach(btn => {
        if (btn) {
            btn.addEventListener('click', () => {
                closeModal(editProfileModal);
            });
        }
    });
}

// Settings Modal
if (settingsBtn) {
    settingsBtn.addEventListener('click', () => {
        openSettingsModal();
    });
}

if (closeSettingsModal || cancelSettingsBtn) {
    [closeSettingsModal, cancelSettingsBtn].forEach(btn => {
        if (btn) {
            btn.addEventListener('click', () => {
                closeModal(settingsModal);
            });
        }
    });
}

// Close modal when clicking outside
[editProfileModal, settingsModal].forEach(modal => {
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(modal);
            }
        });
    }
});

function openEditProfileModal() {
    if (editProfileModal) {
        editProfileModal.style.display = 'flex';
        editProfileModal.classList.add('active');
        loadEditProfileData();
    }
}

function openSettingsModal() {
    if (settingsModal) {
        settingsModal.style.display = 'flex';
        settingsModal.classList.add('active');
        loadDarkModeSetting();
    }
}

function closeModal(modal) {
    if (modal) {
        modal.style.display = 'none';
        modal.classList.remove('active');
    }
}

// Load current profile data into edit form
async function loadEditProfileData() {
    const token = getToken();
    if (!token) return;

    try {
        const response = await fetch(`${API_BASE_URL}/api/me`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const userData = await response.json();
            
            // Fill form fields
            const fullnameInput = document.getElementById('editFullname');
            const universitySelect = document.getElementById('editUniversity');
            const majorInput = document.getElementById('editMajor');
            const bioInput = document.getElementById('editBio');
            const avatarPreview = document.getElementById('avatarPreview');

            if (fullnameInput) fullnameInput.value = userData.fullname || '';
            if (majorInput) majorInput.value = userData.major || '';
            if (bioInput) bioInput.value = userData.bio || '';
            
            // Store current major for later use
            if (majorInput) {
                majorInput.dataset.originalValue = userData.major || '';
            }
            
            // Load universities
            await loadUniversitiesForEdit(universitySelect, userData.university);
            
            // Load avatar if exists
            if (avatarPreview) {
                if (userData.avatar_url) {
                    avatarPreview.src = userData.avatar_url;
                } else {
                    avatarPreview.src = './data/avatars/default-avatar.png';
                }
                avatarPreview.onerror = function() {
                    this.onerror = null;
                    this.src = './data/avatars/default-avatar.png';
                };
            }
        }
    } catch (error) {
        console.error('Error loading profile data:', error);
    }
}

// Load universities for edit form
async function loadUniversitiesForEdit(selectElement, currentUniversity) {
    if (!selectElement) return;
    
    try {
        const response = await fetch('./data/universities_majors.json');
        if (response.ok) {
            const data = await response.json();
            // Get unique universities
            const universityMap = new Map();
            if (data.universities_majors) {
                data.universities_majors.forEach(item => {
                    if (!universityMap.has(item.id)) {
                        universityMap.set(item.id, item.name);
                    }
                });
            }
            
            const universities = Array.from(universityMap.entries()).map(([id, name]) => ({ id, name }));
            
            selectElement.innerHTML = '<option value="">Select university</option>';
            universities.forEach(uni => {
                const option = document.createElement('option');
                option.value = uni.id;
                option.textContent = uni.name;
                if (uni.id === currentUniversity) {
                    option.selected = true;
                }
                selectElement.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading universities:', error);
    }
}

// Handle avatar upload preview
const avatarInput = document.getElementById('avatarInput');
const avatarPreview = document.getElementById('avatarPreview');

if (avatarInput && avatarPreview) {
    avatarInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
                avatarPreview.src = event.target.result;
            };
            reader.readAsDataURL(file);
        }
    });
}

// Handle Edit Profile Form Submission
const editProfileForm = document.getElementById('editProfileForm');
if (editProfileForm) {
    editProfileForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const token = getToken();
        if (!token) {
            alert('Please log in to update your profile.');
            return;
        }

        const fullname = document.getElementById('editFullname').value;
        const university = document.getElementById('editUniversity').value;
        const major = document.getElementById('editMajor').value;
        const bio = document.getElementById('editBio').value;
        const avatarFile = document.getElementById('avatarInput').files[0];

        const formData = new FormData();
        formData.append('fullname', fullname);
        formData.append('university', university);
        if (major) formData.append('major', major);
        if (bio) formData.append('bio', bio);
        if (avatarFile) formData.append('avatar', avatarFile);

        const submitBtn = editProfileForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

        try {
            const response = await fetch(`${API_BASE_URL}/api/profile/update`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                showNotification('Profile updated successfully!', 'success');
                
                // Update avatar immediately if provided
                if (result.avatar_url) {
                    const profileAvatar = document.querySelector('.profile-avatar img');
                    if (profileAvatar) {
                        profileAvatar.src = result.avatar_url + '?t=' + Date.now(); // Add timestamp to force reload
                    }
                    const modalAvatar = document.getElementById('avatarPreview');
                    if (modalAvatar) {
                        modalAvatar.src = result.avatar_url + '?t=' + Date.now();
                    }
                }
                
                closeModal(editProfileModal);
                // Reload profile data
                await loadUserProfile();
            } else {
                const error = await response.json();
                showNotification(error.detail || 'Failed to update profile', 'error');
            }
        } catch (error) {
            console.error('Error updating profile:', error);
            showNotification('Error updating profile. Please try again.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
}

// Handle Change Password Form
const changePasswordForm = document.getElementById('changePasswordForm');
if (changePasswordForm) {
    changePasswordForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const token = getToken();
        if (!token) {
            alert('Please log in to change your password.');
            return;
        }

        const currentPassword = document.getElementById('currentPassword').value;
        const newPassword = document.getElementById('newPassword').value;
        const confirmPassword = document.getElementById('confirmPassword').value;

        if (newPassword !== confirmPassword) {
            showNotification('New passwords do not match!', 'error');
            return;
        }

        if (newPassword.length < 6) {
            showNotification('Password must be at least 6 characters long!', 'error');
            return;
        }

        const submitBtn = changePasswordForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Updating...';

        try {
            const response = await fetch(`${API_BASE_URL}/api/profile/change-password`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    current_password: currentPassword,
                    new_password: newPassword
                })
            });

            if (response.ok) {
                showNotification('Password changed successfully!', 'success');
                changePasswordForm.reset();
            } else {
                const error = await response.json();
                showNotification(error.detail || 'Failed to change password', 'error');
            }
        } catch (error) {
            console.error('Error changing password:', error);
            showNotification('Error changing password. Please try again.', 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
}

// Dark Mode Toggle
const darkModeToggle = document.getElementById('darkModeToggle');
if (darkModeToggle) {
    // Load saved theme preference
    loadDarkModeSetting();
    
    darkModeToggle.addEventListener('change', (e) => {
        const isDarkMode = e.target.checked;
        toggleDarkMode(isDarkMode);
        localStorage.setItem('darkMode', isDarkMode);
    });
}

function loadDarkModeSetting() {
    const savedDarkMode = localStorage.getItem('darkMode') === 'true';
    if (darkModeToggle) {
        darkModeToggle.checked = savedDarkMode;
    }
    toggleDarkMode(savedDarkMode);
}

function toggleDarkMode(isDark) {
    if (isDark) {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }
}

// Initialize dark mode on page load
document.addEventListener('DOMContentLoaded', () => {
    loadDarkModeSetting();
});

