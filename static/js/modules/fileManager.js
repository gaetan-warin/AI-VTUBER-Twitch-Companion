import { emit } from './socket.js';
import { showNotification } from './ui.js';

let fileManagerModal;
let currentTab = 'all';
let allDocuments = [];

export function initializeFileManager() {
    fileManagerModal = document.getElementById('fileManagerModal');
    const closeBtn = fileManagerModal.querySelector('.close');
    const uploadBtn = document.getElementById('uploadBtn');
    const fileInput = document.getElementById('fileUpload');

    // Close modal
    closeBtn.onclick = () => fileManagerModal.style.display = 'none';
    window.onclick = (event) => {
        if (event.target === fileManagerModal) fileManagerModal.style.display = 'none';
    };

    // Upload button click
    uploadBtn.onclick = () => fileInput.click();

    // File selection handler
    fileInput.onchange = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = () => {
            emit('upload_document', {
                file: {
                    name: file.name,
                    content: reader.result
                }
            });
        };
        reader.readAsArrayBuffer(file);
        fileInput.value = ''; // Reset file input
    };

    // Tab switching
    const tabButtons = fileManagerModal.querySelectorAll('.tab-button');
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all tabs
            tabButtons.forEach(btn => btn.classList.remove('active'));
            // Add active class to clicked tab
            button.classList.add('active');
            // Update current tab and filter documents
            currentTab = button.dataset.tab;
            updateUploadSectionVisibility();
            filterAndDisplayDocuments();
        });
    });

    loadDocuments(); // Initial load
}

function updateUploadSectionVisibility() {
    const uploadSection = document.getElementById('fileUploadSection');
    if (uploadSection) {
        // Show upload section only for RAG Documents tab
        uploadSection.style.display = currentTab === 'rag' ? 'block' : 'none';
    }
}

export function openFileManagerModal() {
    if (fileManagerModal) {
        fileManagerModal.style.display = 'block';
        loadDocuments(); // Refresh the document list when opening the modal
    }
}

export function handleDocumentsList(data) {
    if (!data.documents) return;
    
    allDocuments = data.documents;
    updateUploadSectionVisibility();
    filterAndDisplayDocuments();
}

function filterAndDisplayDocuments() {
    const tbody = document.querySelector('#documentsTable tbody');
    
    let filteredDocs = allDocuments;
    
    // Filter based on current tab
    if (currentTab === 'rag') {
        filteredDocs = allDocuments.filter(doc => doc.category === 'rag');
    } else if (currentTab === 'llm') {
        filteredDocs = allDocuments.filter(doc => doc.category === 'llm');
    }
    
    if (filteredDocs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 20px; color: #999;">
                    No documents found in this category
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = filteredDocs.map(doc => `
        <tr>
            <td title="${doc.name}">
                <a href="#" onclick="window.downloadDocument('${doc.name}', '${doc.category}'); return false;" style="color: #4CAF50; text-decoration: none; cursor: pointer;">
                    ${doc.name}
                </a>
            </td>
            <td>${doc.type}</td>
            <td>${doc.size}</td>
            <td>${doc.location || 'N/A'}</td>
            <td>
                <button class="delete-btn" onclick="window.deleteDocument('${doc.name}', '${doc.category}')">Delete</button>
            </td>
        </tr>
    `).join('');
}

export function handleDocumentDeleted(response) {
    if (response.status === 'success') {
        loadDocuments();
        showNotification('success', response.message);
    } else {
        showNotification('error', response.message);
    }
}

export function handleDocumentUploaded(response) {
    if (response.status === 'success') {
        loadDocuments();
        showNotification('success', response.message);
    } else {
        showNotification('error', response.message);
    }
}

export function loadDocuments() {
    emit('list_documents');
}

export function deleteDocument(filename, category) {
    if (!confirm(`Are you sure you want to delete ${filename}?`)) return;
    emit('delete_document', { filename, category });
}

export function downloadDocument(filename, category) {
    // Construct the download URL based on category
    const downloadUrl = category === 'rag' 
        ? `/download/document/rag/${encodeURIComponent(filename)}`
        : `/download/document/llm/${encodeURIComponent(filename)}`;
    
    console.log('Downloading:', filename, 'from category:', category, 'URL:', downloadUrl);
    
    // Direct download using fetch
    fetch(downloadUrl)
        .then(response => {
            if (!response.ok) throw new Error('Download failed');
            return response.blob();
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        })
        .catch(error => {
            console.error('Download error:', error);
            showNotification('error', `Failed to download ${filename}`);
        });
}

// Make functions available globally for onclick handlers
window.deleteDocument = deleteDocument;
window.downloadDocument = downloadDocument;
