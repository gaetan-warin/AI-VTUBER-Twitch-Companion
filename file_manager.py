import os
import logging
from werkzeug.utils import secure_filename
import humanize

logger = logging.getLogger(__name__)

class FileManager:
    def __init__(self, app_root, socketio, rag_handler):
        self.app_root = app_root
        self.socketio = socketio
        self.rag_handler = rag_handler
        self.doc_dir = os.path.join(self.app_root, 'static', 'doc')

    def list_documents(self):
        documents = []
        if os.path.exists(self.doc_dir):
            for filename in os.listdir(self.doc_dir):
                file_path = os.path.join(self.doc_dir, filename)
                if os.path.isfile(file_path):
                    stats = os.stat(file_path)
                    documents.append({
                        'name': filename,
                        'type': os.path.splitext(filename)[1][1:].upper(),
                        'size': humanize.naturalsize(stats.st_size)
                    })
        return documents

    def delete_document(self, filename):
        if not filename:
            return {'status': 'error', 'message': 'No filename provided'}

        file_path = os.path.join(self.doc_dir, secure_filename(filename))
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.rag_handler.initialize(self.doc_dir)
                return {'status': 'success', 'message': f'Deleted {filename}'}
            return {'status': 'error', 'message': 'File not found'}
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {e}")
            return {'status': 'error', 'message': str(e)}

    def upload_document(self, file_data):
        if not file_data:
            return {'status': 'error', 'message': 'No file provided'}

        filename = secure_filename(file_data['name'])
        content = file_data['content']

        if not filename.endswith(('.pdf', '.txt')):
            return {'status': 'error', 'message': 'Invalid file type'}

        try:
            os.makedirs(self.doc_dir, exist_ok=True)
            file_path = os.path.join(self.doc_dir, filename)

            with open(file_path, 'wb') as f:
                f.write(content)

            self.rag_handler.initialize(self.doc_dir)

            stats = os.stat(file_path)
            return {
                'status': 'success',
                'message': f'Uploaded {filename}',
                'file': {
                    'name': filename,
                    'type': os.path.splitext(filename)[1][1:].upper(),
                    'size': humanize.naturalsize(stats.st_size)
                    # Removed 'modified' field
                }
            }
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return {'status': 'error', 'message': str(e)}

def setup_file_manager_routes(socketio, file_manager):
    @socketio.on('list_documents')
    def handle_list_documents(data=None):  # Added data parameter with default
        documents = file_manager.list_documents()
        socketio.emit('documents_list', {'documents': documents})

    @socketio.on('delete_document')
    def handle_delete_document(data):
        result = file_manager.delete_document(data.get('filename'))
        socketio.emit('document_deleted', result)

    @socketio.on('upload_document')
    def handle_upload_document(data):
        result = file_manager.upload_document(data.get('file'))
        socketio.emit('document_uploaded', result)
