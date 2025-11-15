/*
sidebar (Giữ nguyên của bạn)
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

document.addEventListener("DOMContentLoaded", () => {
  const documentListContainer = document.getElementById("document-list");

  if (documentListContainer) {
    fetchAndDisplayDocuments();
  }
});

async function fetchAndDisplayDocuments() {
  const container = document.getElementById("document-list");

  try {
    // Call API endpoint (GET /documents/)
    const response = await fetch("/documents/");

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // convert to JSON
    const documents = await response.json();

    if (documents.length === 0) {
      container.innerHTML =
        "<p>No documents have been uploaded for this category yet.</p>";
      return;
    }

    container.innerHTML = "";

    documents.forEach((doc) => {
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

      container.insertAdjacentHTML("beforeend", documentCardHTML);
    });
  } catch (error) {
    console.error("Error loading documents:", error);
    container.innerHTML = "<p style='color: red;'>Can not load documents.</p>";
  }
}

function generateTagsHTML(tagsString) {
  if (!tagsString || tagsString.trim() === "") {
    return ""; // Return empty string if no tags
  }

  // Split string by commas, trim whitespace, and create HTML
  return tagsString
    .split(",")
    .map((tag) => tag.trim())
    .filter((tag) => tag) // Filter out empty tags
    .map((tag) => `<span class="tag">${tag}</span>`)
    .join(""); // Join all together
}

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
