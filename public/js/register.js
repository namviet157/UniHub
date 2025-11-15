const registerForm = document.getElementById('registerForm');

async function loadUniversities() {
    const universitySelect = document.getElementById('university');
    if (!universitySelect) return;
    
    try {
        universitySelect.innerHTML = '<option value="">Loading universities...</option>';
        
        const response = await fetch('./data/universities.json');
        if (!response.ok) {
            throw new Error('Failed to load universities');
        }
        
        const data = await response.json();
        universitySelect.innerHTML = '<option value="">Select your university</option>';
        
        data.universities.forEach(uni => {
            const option = document.createElement('option');
            option.value = uni.id;
            option.textContent = uni.name;
            universitySelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading universities:', error);
        universitySelect.innerHTML = '<option value="">Error loading universities</option>';
    }
}

// Load universities when page loads
document.addEventListener('DOMContentLoaded', loadUniversities);

if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const fullname = document.getElementById('fullname').value.trim();
        const email = document.getElementById('email').value.trim();
        const university = document.getElementById('university').value;
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        // Validation
        if (!fullname || !email || !university || !password || !confirmPassword) {
            showNotification('Please fill in all fields', 'error');
            return;
        }
        
        if (password !== confirmPassword) {
            showNotification('Passwords do not match', 'error');
            return;
        }
        
        if (password.length < 6) {
            showNotification('Password must be at least 6 characters', 'error');
            return;
        }
        
        // Disable submit button
        const submitBtn = registerForm.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating Account...';
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    fullname,
                    email,
                    university,
                    password
                })
            });
            
            // Check if response is ok before parsing JSON
            if (!response.ok) {
                let errorMessage = 'Registration failed';
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.detail || errorMessage;
                } catch (e) {
                    // If response is not JSON, use status text
                    errorMessage = `Error ${response.status}: ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }
            
            const data = await response.json();
            
            // Save token
            saveToken(data.access_token);
            
            // Show success message
            showNotification('Account created successfully!', 'success');
            
            // Redirect to profile or home page
            setTimeout(() => {
                window.location.href = 'profile.html';
            }, 1000);
            
        } catch (error) {
            console.error('Registration error:', error);
            
            // Handle different types of errors
            let errorMessage = 'Registration failed. Please try again.';
            
            if (error.message) {
                errorMessage = error.message;
            } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
                errorMessage = 'Cannot connect to server. Please make sure the backend is running on ' + API_BASE_URL;
            } else if (error.name === 'NetworkError' || error.message === 'Failed to fetch') {
                errorMessage = 'Network error. Please check your connection and make sure the backend server is running.';
            }
            
            showNotification(errorMessage, 'error');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalText;
        }
    });
}

