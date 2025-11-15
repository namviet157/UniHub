// // explore.js (rewritten)

// document.addEventListener("DOMContentLoaded", () => {
//   const classList = [
//     "Engineering Mechanics - Statics",
//     "Introduction to Computer Science",
//     "Programming Basics",
//     "Introduction to Web Development",
//     "Physics I",
//   ];

//   const container = document.getElementById("classContainer");

//   function renderClasses() {
//     container.innerHTML = "";
//     classList.forEach((cls, index) => {
//       const div = document.createElement("div");
//       div.className = "class-item";
//       div.innerHTML = `
//                 <span>${cls}</span>
//                 <button onclick="removeClass(${index})">X</button>
//             `;
//       container.appendChild(div);
//     });
//   }

//   window.removeClass = function (index) {
//     classList.splice(index, 1);
//     renderClasses();
//   };

//   renderClasses();
// });

/**
 * Hàm này dùng cho sidebar (Giữ nguyên của bạn)
 */
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
                    <button class="icon-btn-large">
                        <i class="fas fa-arrow-up"></i>
                        <span>0</span> </button>
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
    });
  } catch (error) {
    console.error("Lỗi khi tải tài liệu:", error);
    container.innerHTML =
      "<p style='color: red;'>Không thể tải danh sách tài liệu. Vui lòng thử lại.</p>";
  }
}

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
