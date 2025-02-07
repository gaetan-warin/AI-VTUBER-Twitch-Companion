"""RAG (Retrieval-Augmented Generation) handler module for document processing and retrieval."""

import os
import logging
import fitz  # PyMuPDF
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

def load_pdf(pdf_path):
    """Load text content from a PDF file."""
    try:
        doc = fitz.open(pdf_path)
        texts = [page.get_text("text") for page in doc]
        doc.close()  # Properly close the PDF
        return texts
    except (fitz.FileDataError, fitz.FileDataError, fitz.FileDataError) as e:
        logger.error("Error loading PDF %s: %s", pdf_path, e)
        return []

def load_txt(txt_path):
    """Load text content from a TXT file."""
    try:
        with open(txt_path, 'r', encoding='utf-8') as file:
            # Split text into paragraphs based on double newlines
            text = file.read()
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            return paragraphs
    except (IOError, OSError) as e:
        logger.error("Error loading TXT %s: %s", txt_path, e)
        return []

def load_documents_from_directory(directory):
    """Load text content from all supported documents in a directory."""
    documents = []
    if not os.path.exists(directory):
        logger.warning("Documents directory does not exist: %s", directory)
        return documents

    supported_extensions = {
        '.pdf': load_pdf,
        '.txt': load_txt
    }

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        file_extension = os.path.splitext(filename)[1].lower()

        if file_extension in supported_extensions:
            logger.info("Loading %s file: %s", file_extension, filename)
            loader = supported_extensions[file_extension]
            documents.extend(loader(file_path))
        else:
            logger.debug("Skipping unsupported file: %s", filename)

    logger.info("Loaded %s text segments from %s", len(documents), directory)
    return documents

class RAGHandler:
    """RAGHandler class for managing the Retrieval-Augmented Generation system's lifecycle and retrieving documents."""
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
        except (ValueError, TypeError) as e:
            logger.error("Error updating BM25 index: %s", e)
            self.is_initialized = False

    def initialize(self, documents_dir):
        """Initialize or reinitialize the RAG system with documents from a directory."""
        try:
            logger.info("Loading documents from: %s", documents_dir)
            documents = load_documents_from_directory(documents_dir)
            self.documents = documents
            self.update_index()
            logger.info("Initialized with %s documents", len(documents))
        except (IOError, OSError) as e:
            logger.error("Error initializing RAG: %s", e)
            self.is_initialized = False

    def add_documents(self, new_documents):
        """Add new documents and update the index."""
        if not new_documents:
            return

        try:
            self.documents.extend(new_documents)
            self.update_index()
            logger.info("Added %s new documents", len(new_documents))
        except (ValueError, TypeError) as e:
            logger.error("Error adding documents: %s", e)

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
            logger.info("Query: %s", query)
            logger.info("Scores: %s", doc_scores)
            logger.info("Top docs: %s", top_docs)

            return top_docs
        except (ValueError, TypeError) as e:
            logger.error("Error retrieving relevant documents: %s", e)
            return []
