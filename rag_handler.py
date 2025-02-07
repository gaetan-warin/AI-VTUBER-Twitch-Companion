"""RAG (Retrieval-Augmented Generation) handler module for document processing and retrieval."""

import logging
import fitz  # PyMuPDF
import os
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

def load_pdf(pdf_path):
    """Load text content from a PDF file."""
    try:
        doc = fitz.open(pdf_path)
        texts = [page.get_text("text") for page in doc]
        doc.close()  # Properly close the PDF
        return texts
    except Exception as e:
        logger.error(f"Error loading PDF {pdf_path}: {e}")
        return []

def load_txt(txt_path):
    """Load text content from a TXT file."""
    try:
        with open(txt_path, 'r', encoding='utf-8') as file:
            # Split text into paragraphs based on double newlines
            text = file.read()
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            return paragraphs
    except Exception as e:
        logger.error(f"Error loading TXT {txt_path}: {e}")
        return []

def load_documents_from_directory(directory):
    """Load text content from all supported documents in a directory."""
    documents = []
    if not os.path.exists(directory):
        logger.warning(f"Documents directory does not exist: {directory}")
        return documents

    supported_extensions = {
        '.pdf': load_pdf,
        '.txt': load_txt
    }

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        file_extension = os.path.splitext(filename)[1].lower()
        
        if file_extension in supported_extensions:
            logger.info(f"Loading {file_extension} file: {filename}")
            loader = supported_extensions[file_extension]
            documents.extend(loader(file_path))
        else:
            logger.debug(f"Skipping unsupported file: {filename}")

    logger.info(f"Loaded {len(documents)} text segments from {directory}")
    return documents

class RAGHandler:
    def __init__(self):
        self.documents = []  # Original documents
        self.corpus = []     # Preprocessed documents
        self.bm25 = None
        self.is_initialized = False

    def preprocess_text(self, text):
        """Preprocess text for BM25 indexing."""
        # Keep it simple like in the example - just split by spaces
        return text.lower().strip()

    def tokenize(self, text):
        """Tokenize text into words - simple split by spaces as in example."""
        return text.split(" ")

    def update_index(self):
        """Update BM25 index with current documents."""
        if not self.documents:
            self.is_initialized = False
            return

        try:
            # Preprocess documents
            self.corpus = [self.preprocess_text(doc) for doc in self.documents]
            # Tokenize corpus exactly like the example
            tokenized_corpus = [self.tokenize(doc) for doc in self.corpus]
            # Initialize BM25 with tokenized corpus
            self.bm25 = BM25Okapi(tokenized_corpus)
            self.is_initialized = True
            logger.info("BM25 index updated successfully")
        except Exception as e:
            logger.error(f"Error updating BM25 index: {e}")
            self.is_initialized = False

    def initialize(self, documents_dir):
        """Initialize or reinitialize the RAG system with documents from a directory."""
        try:
            logger.info(f"Loading documents from: {documents_dir}")
            documents = load_documents_from_directory(documents_dir)
            self.documents = documents
            self.update_index()
            logger.info(f"Initialized with {len(documents)} documents")
        except Exception as e:
            logger.error(f"Error initializing RAG: {e}")
            self.is_initialized = False

    def add_documents(self, new_documents):
        """Add new documents and update the index."""
        if not new_documents:
            return
        
        try:
            self.documents.extend(new_documents)
            self.update_index()
            logger.info(f"Added {len(new_documents)} new documents")
        except Exception as e:
            logger.error(f"Error adding documents: {e}")

    def get_relevant_documents(self, query, top_n=2):
        """Retrieve relevant documents for a given query."""
        if not self.is_initialized:
            return []

        try:
            # Tokenize query exactly like the example
            tokenized_query = self.tokenize(self.preprocess_text(query))
            
            # Get scores like in the example
            doc_scores = self.bm25.get_scores(tokenized_query)
            
            # Use get_top_n directly like in the example
            top_docs = self.bm25.get_top_n(tokenized_query, self.documents, n=top_n)
            
            # Log scores for debugging
            logger.info(f"Query: {query}")
            logger.info(f"Scores: {doc_scores}")
            logger.info(f"Top docs: {top_docs}")
            
            return top_docs
        except Exception as e:
            logger.error(f"Error retrieving relevant documents: {e}")
            return []
