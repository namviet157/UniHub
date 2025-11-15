const uploadForm = document.getElementById("uploadForm");
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const filePreview = document.getElementById("filePreview");
const removeFileBtn = document.getElementById("removeFile");

if (dropzone && fileInput) {
  dropzone.addEventListener("click", (e) => {
    if (
      e.target.tagName !== "BUTTON" &&
      e.target.tagName !== "LABEL" &&
      e.target.parentElement.tagName !== "LABEL" &&
      e.target.parentElement.tagName !== "BUTTON"
    ) {
      fileInput.click();
    }
  });

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "var(--primary-color)";
    dropzone.style.background = "var(--bg-light)";
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.style.borderColor = "var(--border-color)";
    dropzone.style.background = "";
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.style.borderColor = "var(--border-color)";
    dropzone.style.background = "";
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  });
}

if (removeFileBtn) {
  removeFileBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    resetDropzone();
  });
}

function handleFile(file) {
  fileInput.files = createFileList(file);
  const fileName = document.getElementById("fileName");
  const fileSize = document.getElementById("fileSize");
  fileName.textContent = file.name;
  fileSize.textContent = formatFileSize(file.size);
  document.querySelector(".dropzone-content").style.display = "none";
  filePreview.style.display = "flex";
  document.querySelector(".upload-progress").style.display = "none";
  document.getElementById("progressFill").style.width = "0%";
  document.getElementById("progressText").textContent = "0%";
}

function resetDropzone() {
  filePreview.style.display = "none";
  document.querySelector(".dropzone-content").style.display = "block";
  fileInput.value = "";
}

function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

function createFileList(file) {
  const dataTransfer = new DataTransfer();
  dataTransfer.items.add(file);
  return dataTransfer.files;
}

// ===  SUBMIT FORM  ===
if (uploadForm) {
  uploadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const submitButton = uploadForm.querySelector('button[type="submit"]');
    const file = fileInput.files[0];

    if (!file) {
      alert("Please select a file to upload.");
      return;
    }

    const formData = new FormData(uploadForm);

    const uploadProgress = document.querySelector(".upload-progress");
    const progressFill = document.getElementById("progressFill");
    const progressText = document.getElementById("progressText");

    uploadProgress.style.display = "block";
    progressFill.style.backgroundColor = "var(--primary-color)";
    submitButton.disabled = true;
    submitButton.innerHTML =
      '<i class="fas fa-spinner fa-spin"></i> Uploading...';

    // Send using XMLHttpRequest (XHR) to track upload progress
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/uploadfile/", true); // Send to FastAPI endpoint

    // Track progress
    xhr.upload.onprogress = function (event) {
      if (event.lengthComputable) {
        const percentComplete = (event.loaded / event.total) * 100;
        progressFill.style.width = percentComplete + "%";
        progressText.textContent = Math.round(percentComplete) + "%";
      }
    };

    // Handle upload completion
    xhr.onload = function () {
      submitButton.disabled = false;
      submitButton.innerHTML = '<i class="fas fa-upload"></i> Upload Document';

      if (xhr.status === 200) {
        // Upload SUCCESSFUL
        const result = JSON.parse(xhr.responseText);
        alert(`Thành công! File "${result.filename}" đã được upload.`);
        uploadForm.reset();
        resetDropzone();
      } else {
        // Upload FAILED
        try {
          const result = JSON.parse(xhr.responseText);
          alert(`Error: ${result.detail || "Unable to upload file."}`);
        } catch (err) {
          alert(`Unknown error from server. Status: ${xhr.status}`);
        }
        progressFill.style.backgroundColor = "#e74c3c";
        progressText.textContent = "Upload Failed";
      }
    };

    // Handle network errors
    xhr.onerror = function () {
      submitButton.disabled = false;
      submitButton.innerHTML = '<i class="fas fa-upload"></i> Upload Document';
      alert("Network error or server not responding.");
      progressFill.style.backgroundColor = "#e74c3c";
      progressText.textContent = "Network Error";
    };

    // Send the form data
    xhr.send(formData);
  });
}
