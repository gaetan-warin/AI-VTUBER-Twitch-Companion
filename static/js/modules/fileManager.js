import { emit } from './socket.js';
import { showNotification } from './ui.js';

let fileManagerModal;

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

    loadDocuments(); // Initial load
}

export function openFileManagerModal() {
    if (fileManagerModal) {
        fileManagerModal.style.display = 'block';
        loadDocuments(); // Refresh the document list when opening the modal
    }
}

export function handleDocumentsList(data) {
    const tbody = document.querySelector('#documentsTable tbody');
    if (!data.documents) return;
    
    tbody.innerHTML = data.documents.map(doc => `
        <tr>
            <td title="${doc.name}">${doc.name}</td>
            <td>${doc.type}</td>
            <td>${doc.size}</td>
            <td>
                <button class="delete-btn" onclick="window.deleteDocument('${doc.name}')">Delete</button>
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

export function deleteDocument(filename) {
    if (!confirm(`Are you sure you want to delete ${filename}?`)) return;
    emit('delete_document', { filename });
}

// Make deleteDocument available globally for onclick handlers
window.deleteDocument = deleteDocument;
