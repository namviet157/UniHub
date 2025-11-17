let selectedFile = null;
let selectedDocumentId = null;
let generatedQuiz = null;
let processedData = null;

document.addEventListener('DOMContentLoaded', () => {
    if (typeof checkAuth === 'function') {
        checkAuth();
    }

    const fileInput = document.getElementById('fileInput');
    const selectFromDocuments = document.getElementById('selectFromDocuments');
    const clearSelection = document.getElementById('clearSelection');
    const generateQuizBtn = document.getElementById('generateQuizBtn');
    const downloadQuizBtn = document.getElementById('downloadQuizBtn');
    const startQuizBtn = document.getElementById('startQuizBtn');

    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file && file.type === 'application/pdf') {
                selectedFile = file;
                selectedDocumentId = null;
                showSelectedFile(file.name);
                hideDocumentList();
                showQuizSettings();
            } else {
                alert('Please select a PDF file');
            }
        });
    }

    if (selectFromDocuments) {
        selectFromDocuments.addEventListener('click', async () => {
            await loadDocuments();
            document.getElementById('documentListSection').style.display = 'block';
        });
    }

    if (clearSelection) {
        clearSelection.addEventListener('click', () => {
            selectedFile = null;
            selectedDocumentId = null;
            fileInput.value = '';
            hideSelectedFile();
            hideQuizSettings();
        });
    }

    if (generateQuizBtn) {
        generateQuizBtn.addEventListener('click', async () => {
            const numQuestions = parseInt(document.getElementById('numQuestions').value) || 10;
            await generateQuiz(numQuestions);
        });
    }

    if (downloadQuizBtn) {
        downloadQuizBtn.addEventListener('click', () => {
            downloadQuizJSON();
        });
    }

    if (startQuizBtn) {
        startQuizBtn.addEventListener('click', () => {
            startQuiz();
        });
    }
});

async function loadDocuments() {
    const documentList = document.getElementById('documentList');
    documentList.innerHTML = '<p class="loading-text">Loading documents...</p>';

    try {
        const response = await fetch('/documents/');
        if (!response.ok) throw new Error('Failed to load documents');

        const documents = await response.json();
        const pdfDocuments = documents.filter(doc => 
            doc.content_type && doc.content_type.toLowerCase().includes('pdf')
        );

        if (pdfDocuments.length === 0) {
            documentList.innerHTML = '<p class="no-documents">No PDF documents found. Please upload a PDF first.</p>';
            return;
        }

        let html = '';
        pdfDocuments.forEach(doc => {
            html += `
                <div class="document-item" data-doc-id="${doc.id}" data-doc-path="${doc.saved_path}">
                    <div class="document-icon">
                        <i class="fas fa-file-pdf"></i>
                    </div>
                    <div class="document-info">
                        <h4>${escapeHtml(doc.documentTitle || doc.filename)}</h4>
                        <p>${escapeHtml(doc.description || 'No description')}</p>
                        <span class="document-meta">${doc.university || ''} • ${doc.course || ''}</span>
                    </div>
                    <button class="btn btn-primary btn-small select-doc-btn">
                        <i class="fas fa-check"></i> Select
                    </button>
                </div>
            `;
        });

        documentList.innerHTML = html;

        document.querySelectorAll('.select-doc-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const docItem = this.closest('.document-item');
                const docId = docItem.dataset.docId;
                const docPath = docItem.dataset.docPath;
                const docTitle = docItem.querySelector('h4').textContent;

                selectedDocumentId = docId;
                selectedFile = null;
                showSelectedFile(docTitle, true);
                hideDocumentList();
                showQuizSettings();
            });
        });

    } catch (error) {
        console.error('Error loading documents:', error);
        documentList.innerHTML = '<p class="error-text">Failed to load documents. Please try again.</p>';
    }
}

function showSelectedFile(fileName, isDocument = false) {
    const selectedFileInfo = document.getElementById('selectedFileInfo');
    const selectedFileName = document.getElementById('selectedFileName');
    
    selectedFileName.textContent = fileName;
    selectedFileInfo.style.display = 'flex';
}

function hideSelectedFile() {
    document.getElementById('selectedFileInfo').style.display = 'none';
}

function hideDocumentList() {
    document.getElementById('documentListSection').style.display = 'none';
}

function showQuizSettings() {
    document.getElementById('quizSettings').style.display = 'block';
}

function hideQuizSettings() {
    document.getElementById('quizSettings').style.display = 'none';
}

async function generateQuiz(numQuestions) {
    document.getElementById('fileSelectionSection').style.display = 'none';
    document.getElementById('loadingSection').style.display = 'block';
    document.getElementById('quizResultsSection').style.display = 'none';
    
    const loadingMessage = document.getElementById('loadingMessage');
    if (loadingMessage) {
        loadingMessage.textContent = 'Processing PDF: Extracting text, generating summary, extracting keywords, and creating quiz questions. This may take a few moments...';
    }

    try {
        if (typeof getToken !== 'function') {
            console.error('getToken function not found. Make sure auth.js is loaded.');
            alert('Authentication error. Please refresh the page and log in again.');
            window.location.href = 'login.html';
            return;
        }

        const token = getToken();
        if (!token) {
            alert('Please log in to generate quiz');
            window.location.href = 'login.html';
            return;
        }

        let response;
        
        if (selectedFile) {
            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('num_questions', numQuestions);
            formData.append('include_summary', 'true');
            formData.append('include_keywords', 'true');
            
            response = await fetch('/api/generate-quiz-from-file-complete', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });
        } else if (selectedDocumentId) {
            const requestBody = {
                num_questions: numQuestions,
                include_summary: true,
                include_keywords: true
            };
            
            response = await fetch(`/api/documents/${selectedDocumentId}/process-pdf`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(requestBody)
            });
        } else {
            throw new Error('Please select a file or document');
        }

        if (!response.ok) {
            if (response.status === 401) {
                alert('Your session has expired. Please log in again.');
                if (typeof removeToken === 'function') {
                    removeToken();
                }
                window.location.href = 'login.html';
                return;
            }
            
            let errorMessage = 'Failed to process PDF';
            try {
                const error = await response.json();
                errorMessage = error.detail || errorMessage;
            } catch (e) {
                errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            }
            throw new Error(errorMessage);
        }

        processedData = await response.json();
        generatedQuiz = processedData.quiz;
        displayAllResults(processedData);

    } catch (error) {
        console.error('Error processing PDF:', error);
        alert('Failed to process PDF: ' + error.message);
        
        document.getElementById('fileSelectionSection').style.display = 'block';
        document.getElementById('loadingSection').style.display = 'none';
    }
}

function displayAllResults(data) {
    document.getElementById('loadingSection').style.display = 'none';
    document.getElementById('quizResultsSection').style.display = 'block';

    if (data.summary) {
        const summarySection = document.getElementById('summarySection');
        const summaryContent = document.getElementById('summaryContent');
        if (summarySection && summaryContent) {
            summarySection.style.display = 'block';
            const escapedSummary = escapeHtml(data.summary);
            const formattedSummary = escapedSummary.replace(/\n/g, '<br>');
            summaryContent.innerHTML = `<div class="summary-text">${formattedSummary}</div>`;
        }
    } else {
        document.getElementById('summarySection').style.display = 'none';
    }

    if (data.keywords && data.keywords.length > 0) {
        const keywordsSection = document.getElementById('keywordsSection');
        const keywordsContent = document.getElementById('keywordsContent');
        if (keywordsSection && keywordsContent) {
            keywordsSection.style.display = 'block';
            let keywordsHtml = '<div class="keywords-list">';
            data.keywords.forEach(keyword => {
                keywordsHtml += `<span class="keyword-tag">${escapeHtml(keyword)}</span>`;
            });
            keywordsHtml += '</div>';
            keywordsContent.innerHTML = keywordsHtml;
        }
    } else {
        document.getElementById('keywordsSection').style.display = 'none';
    }

    if (data.quiz) {
        displayQuizResults(data.quiz);
        document.getElementById('quizPreviewSection').style.display = 'block';
    } else {
        document.getElementById('quizPreviewSection').style.display = 'none';
    }
}

function displayQuizResults(quizData) {
    const quizPreview = document.getElementById('quizPreview');
    
    let html = `
        <div class="quiz-info">
            <h3>${escapeHtml(quizData.quiz_title || 'Generated Quiz')}</h3>
            <p>Total Questions: ${quizData.total_questions || 0}</p>
        </div>
        <div class="quiz-questions-preview">
    `;

    if (quizData.questions && quizData.questions.length > 0) {
        quizData.questions.forEach((q, index) => {
            html += `
                <div class="question-preview-item">
                    <div class="question-number">Question ${index + 1}</div>
                    <div class="question-text">${escapeHtml(q.question)}</div>
                    <div class="question-options">
            `;
            
            if (q.options) {
                Object.entries(q.options).forEach(([key, value]) => {
                    const isCorrect = q.correct_answer === key || q.correct_answer === value;
                    html += `
                        <div class="option-item ${isCorrect ? 'correct' : ''}">
                            <span class="option-label">${key}</span>
                            <span class="option-text">${escapeHtml(value)}</span>
                            ${isCorrect ? '<i class="fas fa-check-circle"></i>' : ''}
                        </div>
                    `;
                });
            }
            
            html += `
                    </div>
                </div>
            `;
        });
    } else {
        html += '<p class="no-questions">No questions generated. Please try again.</p>';
    }

    html += '</div>';
    quizPreview.innerHTML = html;
}

function downloadQuizJSON() {
    if (!generatedQuiz) return;

    const dataStr = JSON.stringify(generatedQuiz, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `quiz_${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
}

function startQuiz() {
    if (!generatedQuiz) return;
    
    sessionStorage.setItem('currentQuiz', JSON.stringify(generatedQuiz));
    
    initializeQuizTaking(generatedQuiz);
}

let quizState = {
    currentQuestionIndex: 0,
    answers: {},
    startTime: null,
    quizData: null
};

function initializeQuizTaking(quizData) {
    quizState = {
        currentQuestionIndex: 0,
        answers: {},
        startTime: Date.now(),
        quizData: quizData
    };
    
    const quizModalTitle = document.getElementById('quizModalTitle');
    if (quizModalTitle) {
        quizModalTitle.innerHTML = `<i class="fas fa-question-circle"></i> ${escapeHtml(quizData.quiz_title || 'Quiz')}`;
    }
    
    const quizModal = document.getElementById('quizTakingModal');
    if (quizModal) {
        quizModal.classList.add('active');
    }
    
    loadQuestion(0);
    
    updateQuizNavigation();
}

function loadQuestion(questionIndex) {
    if (!quizState.quizData || !quizState.quizData.questions) return;
    
    const questions = quizState.quizData.questions;
    if (questionIndex < 0 || questionIndex >= questions.length) return;
    
    const question = questions[questionIndex];
    const container = document.getElementById('quizQuestionContainer');
    if (!container) return;
    
    updateProgress(questionIndex + 1, questions.length);
    
    let html = `
        <div class="quiz-question">
            <div class="question-header">
                <span class="question-number-badge">Question ${questionIndex + 1}</span>
            </div>
            <h3 class="question-text">${escapeHtml(question.question)}</h3>
            <div class="question-options-list">
    `;
    
    if (question.options) {
        Object.entries(question.options).forEach(([key, value]) => {
            const isSelected = quizState.answers[question.id] === key;
            html += `
                <label class="option-radio ${isSelected ? 'selected' : ''}" data-option="${key}">
                    <input type="radio" name="question_${question.id}" value="${key}" ${isSelected ? 'checked' : ''}>
                    <span class="option-label">${key}</span>
                    <span class="option-text">${escapeHtml(value)}</span>
                </label>
            `;
        });
    }
    
    html += `
            </div>
        </div>
    `;
    
    container.innerHTML = html;
    
    container.querySelectorAll('input[type="radio"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const questionId = question.id;
            const selectedOption = this.value;
            
            quizState.answers[questionId] = selectedOption;
            
            container.querySelectorAll('.option-radio').forEach(opt => {
                opt.classList.remove('selected');
            });
            this.closest('.option-radio').classList.add('selected');
            
            updateQuizNavigation();
        });
    });
    
    updateQuizNavigation();
}

function updateProgress(current, total) {
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    if (progressFill) {
        const percentage = (current / total) * 100;
        progressFill.style.width = `${percentage}%`;
    }
    
    if (progressText) {
        progressText.textContent = `Question ${current} of ${total}`;
    }
}

function updateQuizNavigation() {
    const questions = quizState.quizData?.questions || [];
    const totalQuestions = questions.length;
    const currentIndex = quizState.currentQuestionIndex;
    
    const prevBtn = document.getElementById('prevQuestionBtn');
    const nextBtn = document.getElementById('nextQuestionBtn');
    const submitBtn = document.getElementById('submitQuizBtn');
    
    if (prevBtn) {
        prevBtn.disabled = currentIndex === 0;
    }
    
    if (currentIndex === totalQuestions - 1) {
        if (nextBtn) nextBtn.style.display = 'none';
        if (submitBtn) submitBtn.style.display = 'inline-flex';
    } else {
        if (nextBtn) nextBtn.style.display = 'inline-flex';
        if (submitBtn) submitBtn.style.display = 'none';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const prevBtn = document.getElementById('prevQuestionBtn');
    const nextBtn = document.getElementById('nextQuestionBtn');
    const submitBtn = document.getElementById('submitQuizBtn');
    const closeQuizModal = document.getElementById('closeQuizModal');
    const quizModal = document.getElementById('quizTakingModal');
    
    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            if (quizState.currentQuestionIndex > 0) {
                quizState.currentQuestionIndex--;
                loadQuestion(quizState.currentQuestionIndex);
            }
        });
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            const questions = quizState.quizData?.questions || [];
            if (quizState.currentQuestionIndex < questions.length - 1) {
                quizState.currentQuestionIndex++;
                loadQuestion(quizState.currentQuestionIndex);
            }
        });
    }
    
    if (submitBtn) {
        submitBtn.addEventListener('click', () => {
            submitQuiz();
        });
    }
    
    if (closeQuizModal) {
        closeQuizModal.addEventListener('click', () => {
            if (confirm('Are you sure you want to close? Your progress will be lost.')) {
                closeQuizModalFunc();
            }
        });
    }
    
    if (quizModal) {
        quizModal.addEventListener('click', function(e) {
            if (e.target === this) {
                if (confirm('Are you sure you want to close? Your progress will be lost.')) {
                    closeQuizModalFunc();
                }
            }
        });
    }
});

function submitQuiz() {
    if (!quizState.quizData) return;
    
    const questions = quizState.quizData.questions;
    let correctCount = 0;
    let totalQuestions = questions.length;
    
    const results = questions.map(question => {
        const userAnswer = quizState.answers[question.id];
        const isCorrect = userAnswer === question.correct_answer;
        
        if (isCorrect) {
            correctCount++;
        }
        
        return {
            question: question.question,
            userAnswer: userAnswer,
            correctAnswer: question.correct_answer,
            isCorrect: isCorrect,
            options: question.options,
            explanation: question.explanation || ''
        };
    });
    
    const score = Math.round((correctCount / totalQuestions) * 100);
    const timeSpent = Math.round((Date.now() - quizState.startTime) / 1000);
    
    closeQuizModalFunc();
    
    showQuizResults({
        score: score,
        correctCount: correctCount,
        totalQuestions: totalQuestions,
        timeSpent: timeSpent,
        results: results,
        quizTitle: quizState.quizData.quiz_title
    });
}

function showQuizResults(resultData) {
    const resultsModal = document.getElementById('quizResultsModal');
    const resultsContent = document.getElementById('quizResultsContent');
    
    if (!resultsModal) {
        console.error('quizResultsModal not found!');
        alert('Error: Results modal not found. Please refresh the page.');
        return;
    }
    
    if (!resultsContent) {
        console.error('quizResultsContent not found!');
        alert('Error: Results content container not found. Please refresh the page.');
        return;
    }
    
    let html = `
        <div class="quiz-score-summary">
            <div class="score-circle">
                <div class="score-value">${resultData.score}%</div>
                <div class="score-label">Score</div>
            </div>
            <div class="score-details">
                <div class="score-item">
                    <i class="fas fa-check-circle" style="color: var(--success-color);"></i>
                    <span>Correct: ${resultData.correctCount}/${resultData.totalQuestions}</span>
                </div>
                <div class="score-item">
                    <i class="fas fa-clock"></i>
                    <span>Time: ${formatTime(resultData.timeSpent)}</span>
                </div>
            </div>
        </div>
        
        <div class="quiz-results-questions">
            <h3>Question Review</h3>
    `;
    
    resultData.results.forEach((result, index) => {
        const statusClass = result.isCorrect ? 'correct' : 'incorrect';
        const statusIcon = result.isCorrect ? 'fa-check-circle' : 'fa-times-circle';
        const statusColor = result.isCorrect ? 'var(--success-color)' : 'var(--error-color)';
        
        html += `
            <div class="result-question-item ${statusClass}">
                <div class="result-question-header">
                    <span class="result-question-number">Q${index + 1}</span>
                    <i class="fas ${statusIcon}" style="color: ${statusColor};"></i>
                </div>
                <div class="result-question-text">${escapeHtml(result.question)}</div>
                <div class="result-answers">
                    <div class="result-answer ${result.isCorrect ? 'correct' : ''}">
                        <strong>Your Answer:</strong> 
                        <span>${result.userAnswer || 'Not answered'}</span>
                        ${result.userAnswer && result.options ? ` - ${escapeHtml(result.options[result.userAnswer] || '')}` : ''}
                    </div>
                    ${!result.isCorrect ? `
                        <div class="result-answer correct">
                            <strong>Correct Answer:</strong> 
                            <span>${result.correctAnswer}</span>
                            ${result.options ? ` - ${escapeHtml(result.options[result.correctAnswer] || '')}` : ''}
                        </div>
                    ` : ''}
                </div>
                ${result.explanation ? `
                    <div class="result-explanation">
                        <i class="fas fa-info-circle"></i>
                        <span>${escapeHtml(result.explanation)}</span>
                    </div>
                ` : ''}
            </div>
        `;
    });
    
    html += `
        </div>
    `;
    
    resultsContent.innerHTML = html;
    
    resultsModal.classList.add('active');
    resultsModal.style.display = 'flex';
    
    resultsModal.scrollTop = 0;
    
    const closeResultsBtn = document.getElementById('closeResultsBtn');
    const closeResultsModal = document.getElementById('closeResultsModal');
    const retakeBtn = document.getElementById('retakeQuizBtn');
    
    if (closeResultsBtn) {
        closeResultsBtn.onclick = () => closeResultsModalFunc();
    }
    
    if (closeResultsModal) {
        closeResultsModal.onclick = () => closeResultsModalFunc();
    }
    
    if (retakeBtn) {
        retakeBtn.onclick = () => {
            closeResultsModalFunc();
            if (quizState.quizData) {
                initializeQuizTaking(quizState.quizData);
            }
        };
    }
}

function closeQuizModalFunc() {
    const quizModal = document.getElementById('quizTakingModal');
    if (quizModal) {
        quizModal.classList.remove('active');
    }
    quizState = {
        currentQuestionIndex: 0,
        answers: {},
        startTime: null,
        quizData: null
    };
}

function closeResultsModalFunc() {
    const resultsModal = document.getElementById('quizResultsModal');
    if (resultsModal) {
        resultsModal.classList.remove('active');
    }
}

function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

