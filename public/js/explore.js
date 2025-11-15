function toggleTree(element) {
  const children = element.nextElementSibling;
  const icon = element.querySelector(".fa-chevron-right, .fa-chevron-down");

  if (children.style.display === "none") {
    children.style.display = "block";
    icon.classList.remove("fa-chevron-right");
    icon.classList.add("fa-chevron-down");
  } else {
    children.style.display = "none";
    icon.classList.remove("fa-chevron-down");
    icon.classList.add("fa-chevron-right");
  }
}

/**
 * Chờ cho toàn bộ trang web được tải xong
 */
document.addEventListener("DOMContentLoaded", () => {
  // Tìm container chứa danh sách document
  const documentListContainer = document.getElementById("document-list");

  if (documentListContainer) {
    // Nếu tìm thấy (tức là đang ở trang explore.html),
    // gọi hàm để lấy và hiển thị tài liệu
    fetchAndDisplayDocuments();
  }
});

/**
 * Hàm này gọi API /documents/ và hiển thị kết quả ra HTML
 */
async function fetchAndDisplayDocuments() {
  const container = document.getElementById("document-list");

  try {
    // 1. Gọi API endpoint (GET /documents/)
    const response = await fetch("/documents/");

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // 2. Chuyển đổi dữ liệu trả về thành mảng JSON
    const documents = await response.json(); // Đây là MẢNG các object

    if (documents.length === 0) {
      container.innerHTML =
        "<p>Chưa có tài liệu nào được upload cho mục này.</p>";
      return;
    }

    // Debug: Log first document to check vote_count and comment_count
    if (documents.length > 0) {
      console.log("Sample document from API:", {
        id: documents[0].id,
        vote_count: documents[0].vote_count,
        comment_count: documents[0].comment_count,
        has_voted: documents[0].has_voted
      });
    }

    // Xóa thông báo "Đang tải..."
    container.innerHTML = "";

    // 3. DÙNG VÒNG LẶP ĐỂ TRUY CẬP TỪNG OBJECT
    documents.forEach((doc) => {
      // 'doc' chính là TỪNG OBJECT (tài liệu) của bạn

      // =============================================
      // === TẠO HTML CHO CARD LỚN (ĐÃ CẬP NHẬT) ===
      // =============================================
      const documentCardHTML = `
            <div class="document-card-large">
                <div class="document-icon-large">
                    ${getIconForFile(doc.content_type)} </div>
                <div class="document-content-large">
                    <h3>${doc.documentTitle}</h3>
                    <p class="document-description">${doc.description}</p>
                    
                    <div class="document-meta">
                        <span class="tag">${doc.documentType}</span>
                        ${generateTagsHTML(doc.tags)}
                    </div>
                    
                    <div class="document-info">
                        <span>
                            <i class="far fa-calendar"></i> 
                            ${new Date(doc.uploaded_at).toLocaleDateString()}
                        </span>
                        <span>
                            <i class="fas fa-university"></i>
                            ${doc.university}
                        </span>
                         <span>
                            <i class="fas fa-book"></i>
                            ${doc.course}
                        </span>
                    </div>
                </div>
                <div class="document-actions-large">
                    <button class="icon-btn-large vote-btn ${doc.has_voted ? 'voted' : ''}" data-doc-id="${doc.id || doc._id || ''}" title="Vote">
                        <i class="fas fa-arrow-up"></i>
                        <span class="vote-count">${doc.vote_count !== undefined ? doc.vote_count : 0}</span>
                    </button>
                    <button class="icon-btn-large comment-btn" data-doc-id="${doc.id || doc._id || ''}" title="Comments">
                        <i class="fas fa-comment"></i>
                        <span class="comment-count">${doc.comment_count !== undefined ? doc.comment_count : 0}</span>
                    </button>
                    <button class="btn btn-secondary preview-btn" data-doc-id="${doc.id || doc._id || ''}" data-doc-path="${doc.saved_path}" data-doc-type="${doc.content_type}" title="Preview">
                        <i class="fas fa-eye"></i>
                        Preview
                    </button>
                    <a href="/${
                      doc.saved_path
                    }" download class="btn btn-primary">
                        <i class="fas fa-download"></i>
                        Download
                    </a>
                </div>
            </div>
            `;

      // Thêm HTML vừa tạo vào trong container
      container.insertAdjacentHTML("beforeend", documentCardHTML);
      
      // Load vote status and comment count for this document
      const docId = doc.id || doc._id || '';
      if (docId) {
        // Vote count is already loaded from API, just check user vote status
        checkUserVoteStatus(docId);
        // Comment count is already loaded from API
      }
    });
    
    // Attach event listeners to comment and vote buttons
    attachCommentButtonListeners();
    attachVoteButtonListeners();
    attachPreviewButtonListeners();
  } catch (error) {
    console.error("Lỗi khi tải tài liệu:", error);
    container.innerHTML =
      "<p style='color: red;'>Không thể tải danh sách tài liệu. Vui lòng thử lại.</p>";
  }
}

/**
 * Attach event listeners to all comment buttons
 */
function attachCommentButtonListeners() {
  const commentButtons = document.querySelectorAll('.comment-btn');
  commentButtons.forEach(button => {
    button.addEventListener('click', function() {
      const docId = this.getAttribute('data-doc-id');
      if (!docId || docId === 'undefined' || docId === '') {
        console.error('Invalid document ID');
        alert('Error: Document ID not found. Please refresh the page.');
        return;
      }
      openCommentsModal(docId);
    });
  });
}

/**
 * Attach event listeners to all vote buttons
 */
function attachVoteButtonListeners() {
  const voteButtons = document.querySelectorAll('.vote-btn');
  voteButtons.forEach(button => {
    button.addEventListener('click', async function() {
      const docId = this.getAttribute('data-doc-id');
      if (!docId || docId === 'undefined' || docId === '') {
        console.error('Invalid document ID');
        return;
      }
      
      // Check if user is logged in
      const token = getToken ? getToken() : null;
      if (!token) {
        alert('Please log in to vote');
        window.location.href = 'login.html';
        return;
      }
      
      await toggleVote(docId, this);
    });
  });
}

/**
 * Open comments modal and load comments for a document
 */
async function openCommentsModal(docId) {
  const modal = document.getElementById('commentsModal');
  const commentsList = document.getElementById('commentsList');
  const commentForm = document.getElementById('commentForm');
  
  // Store current document ID
  modal.dataset.docId = docId;
  
  // Show modal
  modal.classList.add('active');
  
  // Load comments
  await loadComments(docId);
  
  // Reset form
  commentForm.reset();
}

/**
 * Close comments modal
 */
function closeCommentsModal() {
  const modal = document.getElementById('commentsModal');
  modal.classList.remove('active');
  const commentsList = document.getElementById('commentsList');
  commentsList.innerHTML = '<p class="loading-text">Loading comments...</p>';
}

/**
 * Load comments for a document
 */
async function loadComments(docId) {
  const commentsList = document.getElementById('commentsList');
  
  try {
    const token = getToken ? getToken() : null;
    const headers = {
      'Content-Type': 'application/json'
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`/api/documents/${docId}/comments`, {
      method: 'GET',
      headers: headers
    });
    
    if (!response.ok) {
      if (response.status === 404) {
        // No comments yet
        commentsList.innerHTML = '<p class="no-comments">No comments yet. Be the first to comment!</p>';
        return;
      }
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const comments = await response.json();
    
    if (!comments || comments.length === 0) {
      commentsList.innerHTML = '<p class="no-comments">No comments yet. Be the first to comment!</p>';
      return;
    }
    
    // Display comments
    commentsList.innerHTML = '';
    comments.forEach(comment => {
      const commentHTML = createCommentHTML(comment);
      commentsList.insertAdjacentHTML('beforeend', commentHTML);
    });
    
    // Update comment count on the button
    updateCommentCount(docId, comments.length);
    
  } catch (error) {
    console.error('Error loading comments:', error);
    commentsList.innerHTML = '<p class="error-text">Failed to load comments. Please try again.</p>';
  }
}

/**
 * Create HTML for a single comment
 */
function createCommentHTML(comment) {
  const date = new Date(comment.created_at || comment.createdAt || Date.now());
  const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
  
  return `
    <div class="comment-item">
      <div class="comment-avatar">
        <i class="fas fa-user"></i>
      </div>
      <div class="comment-content">
        <div class="comment-header">
          <span class="comment-author">${escapeHtml(comment.author_name || comment.authorName || 'Anonymous')}</span>
          <span class="comment-date">${formattedDate}</span>
        </div>
        <div class="comment-text">${escapeHtml(comment.text || comment.content)}</div>
      </div>
    </div>
  `;
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Check if user has voted for a document and update UI
 */
async function checkUserVoteStatus(docId) {
  try {
    const token = getToken ? getToken() : null;
    if (!token) return;
    
    const response = await fetch(`/api/documents/${docId}/votes/check`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      const voteButton = document.querySelector(`.vote-btn[data-doc-id="${docId}"]`);
      if (voteButton) {
        if (data.has_voted) {
          voteButton.classList.add('voted');
        } else {
          voteButton.classList.remove('voted');
        }
      }
    }
  } catch (error) {
    // Silently fail
    console.log('Could not check vote status:', error);
  }
}

/**
 * Toggle vote for a document
 */
async function toggleVote(docId, buttonElement) {
  try {
    const token = getToken ? getToken() : null;
    if (!token) {
      alert('Please log in to vote');
      window.location.href = 'login.html';
      return;
    }
    
    const response = await fetch(`/api/documents/${docId}/votes`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to vote');
    }
    
    const result = await response.json();
    
    // Update vote count
    const voteCountSpan = buttonElement.querySelector('.vote-count');
    if (voteCountSpan) {
      voteCountSpan.textContent = result.vote_count;
    }
    
    // Update voted state
    if (result.has_voted) {
      buttonElement.classList.add('voted');
    } else {
      buttonElement.classList.remove('voted');
    }
    
  } catch (error) {
    console.error('Error toggling vote:', error);
    alert('Failed to vote. Please try again.');
  }
}

/**
 * Update comment count on the button
 */
function updateCommentCount(docId, count) {
  const button = document.querySelector(`.comment-btn[data-doc-id="${docId}"]`);
  if (button) {
    const countSpan = button.querySelector('.comment-count');
    if (countSpan) {
      countSpan.textContent = count;
    }
  }
}

/**
 * Handle comment form submission
 */
document.addEventListener('DOMContentLoaded', () => {
  const commentForm = document.getElementById('commentForm');
  const commentsModal = document.getElementById('commentsModal');
  const closeBtn = document.getElementById('closeCommentsModal');
  
  // Close modal button
  if (closeBtn) {
    closeBtn.addEventListener('click', closeCommentsModal);
  }
  
  // Close modal when clicking outside
  if (commentsModal) {
    commentsModal.addEventListener('click', function(e) {
      if (e.target === this) {
        closeCommentsModal();
      }
    });
  }
  
  // Comment form submission
  if (commentForm) {
    commentForm.addEventListener('submit', async function(e) {
      e.preventDefault();
      
      const docId = commentsModal.dataset.docId;
      const commentText = document.getElementById('commentText').value.trim();
      
      if (!commentText) {
        return;
      }
      
      if (!docId) {
        console.error('No document ID found');
        return;
      }
      
      // Check if user is logged in
      const token = getToken ? getToken() : null;
      if (!token) {
        alert('Please log in to post a comment');
        window.location.href = 'login.html';
        return;
      }
      
      try {
        const response = await fetch(`/api/documents/${docId}/comments`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({
            text: commentText
          })
        });
        
        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Failed to post comment');
        }
        
        // Clear form
        commentForm.reset();
        
        // Reload comments
        await loadComments(docId);
        
      } catch (error) {
        console.error('Error posting comment:', error);
        alert('Failed to post comment. Please try again.');
      }
    });
  }
});

/**
 * Hàm trợ giúp: Tạo các tag HTML từ một chuỗi tags
 * (ví dụ: "python, oop" -> <span...>python</span><span...>oop</span>)
 */
function generateTagsHTML(tagsString) {
  if (!tagsString || tagsString.trim() === "") {
    return ""; // Trả về chuỗi rỗng nếu không có tag
  }

  // Tách chuỗi bằng dấu phẩy, xóa khoảng trắng, và tạo HTML
  return tagsString
    .split(",")
    .map((tag) => tag.trim())
    .filter((tag) => tag) // Lọc bỏ các tag rỗng
    .map((tag) => `<span class="tag">${tag}</span>`)
    .join(""); // Nối tất cả lại
}

/**
 * Hàm trợ giúp: Trả về icon dựa trên loại file
 */
function getIconForFile(contentType) {
  if (contentType.includes("pdf")) {
    return '<i class="fas fa-file-pdf"></i>';
  } else if (contentType.includes("word")) {
    return '<i class="fas fa-file-word"></i>';
  } else if (
    contentType.includes("presentation") ||
    contentType.includes("powerpoint")
  ) {
    return '<i class="fas fa-file-powerpoint"></i>';
  } else {
    return '<i class="fas fa-file-alt"></i>'; // Icon chung
  }
}

/**
 * Attach event listeners to all preview buttons
 */
function attachPreviewButtonListeners() {
  const previewButtons = document.querySelectorAll('.preview-btn');
  previewButtons.forEach(button => {
    button.addEventListener('click', function() {
      const docPath = this.getAttribute('data-doc-path');
      const docType = this.getAttribute('data-doc-type');
      const docId = this.getAttribute('data-doc-id');
      
      if (!docPath) {
        console.error('No document path found');
        alert('Error: Document path not found. Please refresh the page.');
        return;
      }
      
      openPreviewModal(docPath, docType, docId);
    });
  });
}

/**
 * Open preview modal and load document
 */
async function openPreviewModal(docPath, docType, docId) {
  const modal = document.getElementById('previewModal');
  const previewContent = document.getElementById('previewContent');
  const previewTitle = document.getElementById('previewTitle');
  const previewDownload = document.getElementById('previewDownload');
  const previewControls = document.getElementById('previewControls');
  
  // Show modal
  modal.classList.add('active');
  
  // Set download link
  previewDownload.href = `/${docPath}`;
  previewDownload.download = docPath.split('/').pop();
  
  // Reset content
  previewContent.innerHTML = '<p class="loading-text">Loading preview...</p>';
  previewControls.style.display = 'none';
  
  // Load preview based on file type
  if (docType && docType.includes('pdf')) {
    await loadPDFPreview(docPath, previewContent, previewControls);
  } else if (docType && (docType.includes('word') || docType.includes('document'))) {
    loadOtherFilePreview(docPath, previewContent, 'Word Document');
  } else if (docType && (docType.includes('presentation') || docType.includes('powerpoint'))) {
    loadOtherFilePreview(docPath, previewContent, 'PowerPoint Presentation');
  } else if (docType && docType.includes('text')) {
    loadTextPreview(docPath, previewContent);
  } else {
    previewContent.innerHTML = '<p class="error-text">Preview not available for this file type. Please download to view.</p>';
  }
}

/**
 * Load PDF preview using PDF.js
 */
async function loadPDFPreview(docPath, container, controlsContainer) {
  try {
    // Set up PDF.js worker
    if (typeof pdfjsLib !== 'undefined') {
      pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    }
    
    const fileUrl = `/${docPath}`;
    container.dataset.fileUrl = fileUrl;
    
    const loadingTask = pdfjsLib.getDocument(fileUrl);
    const pdf = await loadingTask.promise;
    
    // Store PDF data and current page
    container.dataset.pdf = JSON.stringify({ numPages: pdf.numPages });
    container.dataset.currentPage = '1';
    container._pdf = pdf; // Store PDF object for navigation
    
    // Show controls if multiple pages
    if (pdf.numPages > 1) {
      controlsContainer.style.display = 'flex';
      document.getElementById('totalPages').textContent = pdf.numPages;
      document.getElementById('currentPage').textContent = '1';
      
      // Attach page navigation
      document.getElementById('prevPage').onclick = () => navigatePDFPage(container, -1);
      document.getElementById('nextPage').onclick = () => navigatePDFPage(container, +1);
    }
    
    // Render first page
    await renderPDFPage(pdf, 1, container);
    
  } catch (error) {
    console.error('Error loading PDF:', error);
    container.innerHTML = '<p class="error-text">Failed to load PDF preview. Please download to view.</p>';
  }
}

/**
 * Render a specific PDF page
 */
async function renderPDFPage(pdf, pageNum, container) {
  try {
    const page = await pdf.getPage(pageNum);
    const viewport = page.getViewport({ scale: 1.5 });
    
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.height = viewport.height;
    canvas.width = viewport.width;
    
    await page.render({
      canvasContext: context,
      viewport: viewport
    }).promise;
    
    container.innerHTML = '';
    container.appendChild(canvas);
    
    // Update page info
    document.getElementById('currentPage').textContent = pageNum;
    document.getElementById('totalPages').textContent = pdf.numPages;
    
    // Update navigation buttons
    const prevBtn = document.getElementById('prevPage');
    const nextBtn = document.getElementById('nextPage');
    if (prevBtn) prevBtn.disabled = pageNum <= 1;
    if (nextBtn) nextBtn.disabled = pageNum >= pdf.numPages;
    
  } catch (error) {
    console.error('Error rendering PDF page:', error);
    container.innerHTML = '<p class="error-text">Failed to render PDF page.</p>';
  }
}

/**
 * Navigate PDF pages
 */
async function navigatePDFPage(container, direction) {
  let currentPage = parseInt(container.dataset.currentPage) || 1;
  
  // Use stored PDF object if available, otherwise reload
  let pdf = container._pdf;
  if (!pdf) {
    const fileUrl = container.dataset.fileUrl || '';
    const loadingTask = pdfjsLib.getDocument(fileUrl);
    pdf = await loadingTask.promise;
    container._pdf = pdf;
  }
  
  const newPage = currentPage + direction;
  
  if (newPage < 1 || newPage > pdf.numPages) {
    return;
  }
  
  container.dataset.currentPage = newPage;
  container.innerHTML = '<p class="loading-text">Loading page...</p>';
  
  try {
    await renderPDFPage(pdf, newPage, container);
  } catch (error) {
    console.error('Error navigating PDF:', error);
    container.innerHTML = '<p class="error-text">Failed to load page.</p>';
  }
}

/**
 * Load other file types (Word, PowerPoint) using iframe
 */
function loadOtherFilePreview(docPath, container, fileType) {
  const fileUrl = `/${docPath}`;
  
  // For Word and PowerPoint, we'll use Google Docs Viewer or Office Online
  // For now, show a message with download option
  container.innerHTML = `
    <div class="preview-not-supported">
      <i class="fas fa-file" style="font-size: 64px; color: var(--text-secondary); margin-bottom: 20px;"></i>
      <h3>Preview not available</h3>
      <p>Preview for ${fileType} files is not available in the browser.</p>
      <p>Please download the file to view it.</p>
    </div>
  `;
}

/**
 * Load text file preview
 */
async function loadTextPreview(docPath, container) {
  try {
    const response = await fetch(`/${docPath}`);
    if (!response.ok) {
      throw new Error('Failed to load text file');
    }
    
    const text = await response.text();
    container.innerHTML = `
      <pre class="text-preview">${escapeHtml(text)}</pre>
    `;
  } catch (error) {
    console.error('Error loading text file:', error);
    container.innerHTML = '<p class="error-text">Failed to load text preview.</p>';
  }
}

/**
 * Close preview modal
 */
function closePreviewModal() {
  const modal = document.getElementById('previewModal');
  modal.classList.remove('active');
  const previewContent = document.getElementById('previewContent');
  previewContent.innerHTML = '<p class="loading-text">Loading preview...</p>';
  document.getElementById('previewControls').style.display = 'none';
}

// Attach preview modal close handlers
document.addEventListener('DOMContentLoaded', () => {
  const previewModal = document.getElementById('previewModal');
  const closePreviewBtn = document.getElementById('closePreviewBtn');
  const closePreviewModalBtn = document.getElementById('closePreviewModal');
  
  if (closePreviewBtn) {
    closePreviewBtn.addEventListener('click', closePreviewModal);
  }
  
  if (closePreviewModalBtn) {
    closePreviewModalBtn.addEventListener('click', closePreviewModal);
  }
  
  if (previewModal) {
    previewModal.addEventListener('click', function(e) {
      if (e.target === this) {
        closePreviewModal();
      }
    });
  }
});
