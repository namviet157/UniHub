// Load user profile data

async function loadUserProfile() {
  const token = getToken();

  if (!token) {
    // Redirect to login if not authenticated

    window.location.href = "login.html";

    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/me`, {
      method: "GET",

      headers: {
        Authorization: `Bearer ${token}`,

        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        // Token expired or invalid

        removeToken();

        window.location.href = "login.html";

        return;
      }

      throw new Error("Failed to load profile");
    }

    const userData = await response.json();

    // Update user name

    const fullnameElement = document.getElementById("userFullname");

    if (fullnameElement) {
      fullnameElement.textContent = userData.fullname || "User";
    }

    // Update university - need to map ID to name

    const universityElement = document.getElementById("userUniversity");

    if (universityElement) {
      const universityName = await getUniversityName(userData.university);

      universityElement.textContent =
        universityName || userData.university || "Not specified";
    }
  } catch (error) {
    console.error("Error loading profile:", error);

    // Show error but don't redirect

    const fullnameElement = document.getElementById("userFullname");

    if (fullnameElement) {
      fullnameElement.textContent = "Error loading profile";
    }
  }
}

// Get university name from ID

async function getUniversityName(universityId) {
  if (!universityId) return null;

  try {
    // Try to load from universities.json

    const response = await fetch("./data/universities.json");

    if (response.ok) {
      const data = await response.json();

      const university = data.universities.find(
        (uni) => uni.id === universityId
      );

      return university ? university.name : universityId;
    }
  } catch (error) {
    console.error("Error loading universities:", error);
  }

  // Fallback: return ID if can't find name

  return universityId;
}

// (Đây là code mới để thêm vào profile.js)

// ... (Bên dưới hàm getUniversityName) ...

async function loadMyUploads() {
  const token = getToken();
  if (!token) return; // Không có token, không cần làm gì

  const container = document.getElementById("my-uploads-list");
  const loadingMessage = document.getElementById("uploads-loading-message");

  try {
    const response = await fetch(`${API_BASE_URL}/api/me/documents`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        // Token hết hạn, hàm loadUserProfile sẽ xử lý redirect
        return;
      }
      throw new Error("Failed to load uploads");
    }

    const documents = await response.json();

    // Xóa thông báo "Loading..."
    if (loadingMessage) {
      loadingMessage.remove();
    }
    container.innerHTML = ""; // Xóa sạch nội dung (phòng trường hợp)

    // 1. Trường hợp không có tài liệu nào
    if (documents.length === 0) {
      container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-upload"></i>
                    <h3>You haven't uploaded any documents yet</h3>
                    <p>Click the 'Upload New' button to share your first document.</p>
                    <a href="upload.html" class="btn btn-primary">Upload New</a>
                </div>
            `;
      return;
    }

    // 2. Trường hợp có tài liệu, lặp qua và tạo HTML
    documents.forEach((doc) => {
      // Lấy thông tin từ object 'doc' (giống hệt cấu trúc MongoDB)
      const docTitle = doc.documentTitle;
      const docDesc = doc.description;
      const docCourse = doc.course;
      const docType = doc.documentType;
      const docFaculty = doc.faculty;
      const docTags = doc.tags
        .split(",")
        .map((tag) =>
          tag.trim() ? `<span class="tag">${tag.trim()}</span>` : ""
        )
        .join("");

      // Format ngày upload (ví dụ)
      const uploadedDate = new Date(doc.uploaded_at).toLocaleDateString(
        "en-US",
        {
          year: "numeric",
          month: "short",
          day: "numeric",
        }
      );

      const cardHTML = `
                <div class="document-card-large" data-doc-id="${doc.id}"> <div class="document-icon-large">
                        <i class="fas fa-file-pdf"></i> </div>
                    <div class="document-content-large">
                        <h3>${docTitle}</h3>
                        <p class="document-description">${docDesc}</p>
                        <div class="document-meta">
                            <span class="tag">${docFaculty}</span>
                            <span class="tag">${docCourse}</span>
                            <span class="tag">${docType}</span>
                            ${docTags} </div>
                        <div class="document-info">
                            <span><i class="far fa-calendar"></i> Uploaded ${uploadedDate}</span>
                            <span><i class="fas fa-download"></i> 0 downloads</span>
                            <span><i class="fas fa-arrow-up"></i> 0 upvotes</span>
                            <span class="rating"><i class="fas fa-star"></i> N/A</span>
                        </div>
                    </div>
                    <div class="document-actions-large">
                        <button class="btn btn-secondary">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button class="btn btn-danger">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            `;

      // Thêm thẻ HTML vừa tạo vào trong container
      container.insertAdjacentHTML("beforeend", cardHTML);
    });
  } catch (error) {
    console.error("Error loading uploads:", error);
    if (loadingMessage) {
      loadingMessage.remove();
    }
    container.innerHTML = `<p style="color: red; text-align: center;">Error loading your documents.</p>`;
  }
}
// (Thêm code này vào profile.js, bên dưới hàm loadMyUploads)
//  testing
async function loadMyDownloads() {
  const token = getToken();
  if (!token) return;

  const container = document.getElementById("my-downloads-list");
  const loadingMessage = document.getElementById("downloads-loading-message");

  try {
    const response = await fetch(`${API_BASE_URL}/api/me/downloads`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error("Failed to load download history");
    }

    const documents = await response.json();

    // Xóa thông báo "Loading..."
    if (loadingMessage) {
      loadingMessage.remove();
    }
    container.innerHTML = ""; // Xóa sạch

    // 1. Trường hợp chưa tải gì
    if (documents.length === 0) {
      container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-download"></i>
                    <h3>No downloads yet</h3>
                    <p>Your downloaded documents will appear here.</p>
                    <a href="search.html" class="btn btn-primary">Browse Documents</a>
                </div>
            `;
      return;
    }

    // 2. Trường hợp có tài liệu, lặp qua và tạo HTML
    documents.forEach((doc) => {
      const cardHTML = `
                <div class="document-card-large" data-doc-id="${doc.id}">
                    <div class="document-icon-large">
                        <i class="fas fa-file-pdf"></i>
                    </div>
                    <div class="document-content-large">
                        <h3>${doc.documentTitle}</h3>
                        <p class="document-description">${doc.description}</p>
                        <div class="document-meta">
                            <span class="tag">${doc.faculty}</span>
                            <span class="tag">${doc.course}</span>
                            <span class="tag">${doc.documentType}</span>
                        </div>
                        <div class="document-info">
                            <span><i class="fas fa-university"></i> ${
                              doc.university
                            }</span>
                            <span><i class="far fa-calendar"></i> Uploaded ${new Date(
                              doc.uploaded_at
                            ).toLocaleDateString()}</span>
                        </div>
                    </div>
                    <div class="document-actions-large">
                        <button class="btn btn-primary" onclick="triggerDownload('${
                          doc.id
                        }', '${doc.saved_path}')">
                            <i class="fas fa-download"></i>
                            Download Again
                        </button>
                        <button class="icon-btn-large">
                            <i class="fas fa-heart"></i>
                        </button>
                    </div>
                </div>
            `;
      container.insertAdjacentHTML("beforeend", cardHTML);
    });
  } catch (error) {
    console.error("Error loading downloads:", error);
    if (loadingMessage) {
      loadingMessage.remove();
    }
    container.innerHTML = `<p style="color: red; text-align: center;">Error loading your download history.</p>`;
  }
}

// Thêm hàm này để xử lý việc tải lại (nó cũng sẽ log lại)

function switchTab(event, tabName) {
  const tabContents = document.querySelectorAll(".tab-content");

  const tabBtns = document.querySelectorAll(".tab-btn");

  tabContents.forEach((content) => content.classList.remove("active"));

  tabBtns.forEach((btn) => btn.classList.remove("active"));

  document.getElementById(tabName).classList.add("active");

  event.currentTarget.classList.add("active");
}

// Load user profile data
// Giả sử API_BASE_URL và getToken() đã được định nghĩa trong auth.js
// const API_BASE_URL = ""; // Hoặc URL đầy đủ nếu cần
// const getToken = () => localStorage.getItem("token");
