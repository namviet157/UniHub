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
  documentListContainer.addEventListener("click", handleDownloadClick);
});
// ... (code của hàm getIconForFile) ...

/**
 * (HÀM MỚI)
 * Xử lý sự kiện khi click nút Download
 * Sẽ gọi API để log, sau đó mới kích hoạt tải file.
 */
/**
 * (HÀM CẬP NHẬT)
 * Xử lý sự kiện khi click nút Download
 * Sẽ gọi API để log, sau đó mới kích hoạt tải file.
 */
async function handleDownloadClick(event) {
  // Kiểm tra xem có phải click trúng nút download không
  const downloadButton = event.target.closest(".download-btn");

  if (!downloadButton) {
    return; // Nếu không phải, bỏ qua
  }

  // Lấy thông tin từ data-attributes
  let documentId = downloadButton.dataset.documentId;
  const token = getToken(); // Dùng hàm từ auth.js

  if (!token) {
    alert("Bạn phải đăng nhập để tải tài liệu.");
    return;
  }

  // Kiểm tra documentId có tồn tại không
  if (!documentId) {
    console.error("Document ID không tồn tại trong data-attribute");
    alert("Lỗi: Không tìm thấy ID của tài liệu. Vui lòng tải lại trang.");
    return;
  }

  // Xử lý documentId - đảm bảo là string hợp lệ
  // documentId từ dataset luôn là string, nhưng có thể là JSON string hoặc string thuần
  if (typeof documentId === "string") {
    // Thử parse nếu là JSON string (ví dụ: '{"$oid":"..."}')
    try {
      const parsed = JSON.parse(documentId);
      if (parsed && parsed.$oid) {
        documentId = parsed.$oid;
      } else if (typeof parsed === "string") {
        documentId = parsed;
      }
    } catch (e) {
      // Nếu không parse được, dùng trực tiếp (đã là string)
      // Loại bỏ khoảng trắng thừa
      documentId = documentId.trim();
    }
  }

  // Kiểm tra documentId có hợp lệ không (MongoDB ObjectId có 24 ký tự hex)
  if (!documentId || documentId.length === 0) {
    console.error("Document ID rỗng sau khi xử lý");
    alert("Lỗi: ID tài liệu không hợp lệ. Vui lòng tải lại trang.");
    return;
  }

  console.log("Document ID để download:", documentId);
  console.log("Document ID length:", documentId.length);

  // Vô hiệu hóa nút và hiển thị spinner
  downloadButton.disabled = true;
  downloadButton.innerHTML =
    '<i class="fas fa-spinner fa-spin"></i> Downloading...';

  try {
    // Encode documentId để đảm bảo an toàn trong URL
    const encodedDocumentId = encodeURIComponent(documentId);
    console.log("Encoded Document ID:", encodedDocumentId);
    
    // Gọi API backend để download file (API sẽ tự động ghi log)
    const response = await fetch(`/api/documents/${encodedDocumentId}/download`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      // Nếu lỗi 401, có thể token hết hạn
      if (response.status === 401) {
        throw new Error("Phiên làm việc hết hạn. Vui lòng đăng nhập lại.");
      }

      // Lấy thông báo lỗi từ response
      let detailMessage = "Lỗi máy chủ không xác định.";
      try {
        const result = await response.json();
        if (typeof result.detail === "string") {
          detailMessage = result.detail;
        } else if (
          Array.isArray(result.detail) &&
          result.detail[0] &&
          result.detail[0].msg
        ) {
          detailMessage = result.detail[0].msg;
        }
      } catch (e) {
        // Nếu không parse được JSON, dùng status text
        detailMessage = response.statusText;
      }

      throw new Error(detailMessage);
    }

    // Lấy blob từ response
    const blob = await response.blob();
    
    // Lấy tên file từ header Content-Disposition hoặc dùng documentId
    let filename = `document_${documentId}`;
    const contentDisposition = response.headers.get("Content-Disposition");
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?(.+?)"?$/);
      if (filenameMatch) {
        filename = filenameMatch[1];
      }
    }

    // Tạo URL từ blob và download
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

    // Cập nhật lại nút
    downloadButton.innerHTML = '<i class="fas fa-check"></i> Downloaded';
    downloadButton.disabled = false;
  } catch (error) {
    console.error("Lỗi khi tải file:", error);

    // Hiển thị thông báo lỗi
    alert(`Không thể tải file: ${error.message}`);

    // Reset nút về trạng thái cũ nếu lỗi
    downloadButton.disabled = false;
    downloadButton.innerHTML = '<i class="fas fa-download"></i> Download';
  }
}
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
      // Xử lý document ID - có thể là object với $oid hoặc string
      let docIdString = "";
      
      if (doc.id) {
        if (typeof doc.id === "object" && doc.id !== null) {
          // Nếu là object, lấy $oid hoặc _id
          if (doc.id.$oid) {
            docIdString = doc.id.$oid;
          } else if (doc.id._id) {
            docIdString = doc.id._id;
          } else if (typeof doc.id === "string") {
            docIdString = doc.id;
          } else {
            // Thử convert sang string
            docIdString = String(doc.id);
          }
        } else if (typeof doc.id === "string") {
          docIdString = doc.id;
        } else {
          // Fallback: convert sang string
          docIdString = String(doc.id);
        }
      } else if (doc._id) {
        // Nếu không có id, thử lấy _id
        if (typeof doc._id === "object" && doc._id !== null && doc._id.$oid) {
          docIdString = doc._id.$oid;
        } else {
          docIdString = String(doc._id);
        }
      }
      
      // Kiểm tra docIdString có hợp lệ không
      if (!docIdString || docIdString.trim() === "") {
        console.warn("Document không có ID hợp lệ:", doc);
        return; // Bỏ qua document này
      }
      
      // Đảm bảo docIdString là string và trim
      docIdString = String(docIdString).trim();
      
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
                <span>0</span>
            </button>
            
            <button 
                class="btn btn-primary download-btn" 
                data-document-id="${docIdString}" 
            >
                <i class="fas fa-download"></i> Download
            </button>
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
