const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const filePreview = document.getElementById('filePreview');
const removeFileBtn = document.getElementById('removeFile');
const uploadForm = document.getElementById('uploadForm');
const universitySelect = document.getElementById('university');
const facultySelect = document.getElementById('faculty');
const courseSelect = document.getElementById('course');
const courseCustomInput = document.getElementById('courseCustom');

// Store universities and majors data
let universitiesMajorsData = [];
let uniqueUniversities = [];

if (dropzone && fileInput) {
    dropzone.addEventListener('click', (e) => {
        if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'LABEL') {
            fileInput.click();
        }
    });

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.style.borderColor = 'var(--primary-color)';
        dropzone.style.background = 'var(--bg-light)';
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.style.borderColor = 'var(--border-color)';
        dropzone.style.background = '';
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.style.borderColor = 'var(--border-color)';
        dropzone.style.background = '';

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });
}

if (removeFileBtn) {
    removeFileBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        filePreview.style.display = 'none';
        document.querySelector('.dropzone-content').style.display = 'block';
        fileInput.value = '';
    });
}

function handleFile(file) {
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);

    document.querySelector('.dropzone-content').style.display = 'none';
    filePreview.style.display = 'flex';

    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 100) progress = 100;

        progressFill.style.width = progress + '%';
        progressText.textContent = Math.round(progress) + '%';

        if (progress >= 100) {
            clearInterval(interval);
        }
    }, 200);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Load universities and majors from JSON
async function loadUniversitiesAndMajors() {
    if (!universitySelect || !facultySelect) return;
    
    try {
        universitySelect.innerHTML = '<option value="">Loading universities...</option>';
        facultySelect.innerHTML = '<option value="">Select faculty</option>';
        facultySelect.disabled = true;
        
        const response = await fetch('./data/universities_majors.json');
        if (!response.ok) {
            throw new Error('Failed to load universities and majors');
        }
        
        const data = await response.json();
        universitiesMajorsData = data.universities_majors || [];
        
        // Get unique universities
        const universityMap = new Map();
        universitiesMajorsData.forEach(item => {
            if (!universityMap.has(item.id)) {
                universityMap.set(item.id, item.name);
            }
        });
        
        uniqueUniversities = Array.from(universityMap.entries()).map(([id, name]) => ({
            id,
            name
        }));
        
        // Populate university dropdown
        universitySelect.innerHTML = '<option value="">Select university</option>';
        uniqueUniversities.forEach(uni => {
            const option = document.createElement('option');
            option.value = uni.id;
            option.textContent = uni.name;
            universitySelect.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error loading universities and majors:', error);
        universitySelect.innerHTML = '<option value="">Error loading universities</option>';
    }
}

// Load majors when university is selected
function loadMajorsForUniversity(universityId) {
    if (!facultySelect || !universityId) {
        facultySelect.innerHTML = '<option value="">Select faculty</option>';
        facultySelect.disabled = true;
        return;
    }
    
    // Get unique majors for selected university
    const majorsSet = new Set();
    universitiesMajorsData.forEach(item => {
        if (item.id === universityId && item.major && item.major.trim() !== '') {
            majorsSet.add(item.major);
        }
    });
    
    const majors = Array.from(majorsSet).sort();
    
    // Populate faculty dropdown
    facultySelect.innerHTML = '<option value="">Select faculty</option>';
    if (majors.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'No majors available';
        facultySelect.appendChild(option);
        facultySelect.disabled = true;
    } else {
        majors.forEach(major => {
            const option = document.createElement('option');
            option.value = major;
            option.textContent = major;
            facultySelect.appendChild(option);
        });
        facultySelect.disabled = false;
    }
}

// Event listener for university selection change
if (universitySelect) {
    universitySelect.addEventListener('change', (e) => {
        loadMajorsForUniversity(e.target.value);
    });
}

// Handle course selection change
if (courseSelect && courseCustomInput) {
    courseSelect.addEventListener('change', (e) => {
        if (e.target.value === 'other') {
            courseCustomInput.style.display = 'block';
            courseCustomInput.required = true;
            courseCustomInput.focus();
        } else {
            courseCustomInput.style.display = 'none';
            courseCustomInput.required = false;
            courseCustomInput.value = '';
        }
    });
}

// Load data when page loads
document.addEventListener('DOMContentLoaded', loadUniversitiesAndMajors);

if (uploadForm) {
    uploadForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        // Validate custom course input if "other" is selected
        if (courseSelect && courseSelect.value === 'other') {
            if (!courseCustomInput || !courseCustomInput.value.trim()) {
                alert('Vui lòng nhập tên khóa học');
                if (courseCustomInput) {
                    courseCustomInput.focus();
                }
                return;
            }
        }
        
        alert('Document uploaded successfully! Our AI is now processing it for keywords and duplicate detection.');
        window.location.href = 'profile.html';
    });
}