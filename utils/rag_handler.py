"""RAG (Retrieval-Augmented Generation) handler module for document processing and retrieval.

This module implements a hybrid retrieval system combining:
- FAISS for semantic (dense) vector similarity search
- BM25 for lexical (sparse) keyword-based search
"""

import os
import logging
import numpy as np
import fitz  # PyMuPDF
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
import faiss

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
    """
    Hybrid RAG Handler combining FAISS (semantic) and BM25 (lexical) retrieval.

    This implementation uses:
    - SentenceTransformers for creating embeddings
    - FAISS for fast semantic similarity search
    - BM25 for keyword-based lexical search
    - Reciprocal Rank Fusion (RRF) to combine results
    """
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.documents = []  # Original documents
        self.corpus = []     # Preprocessed documents
        self.bm25 = None
        self.faiss_index = None
        self.embeddings = None
        self.model = None
        self.model_name = model_name
        self.is_initialized = False

    def load_embedding_model(self):
        """Load the sentence transformer model for embeddings."""
        if self.model is None:
            try:
                logger.info("Loading embedding model: %s", self.model_name)
                self.model = SentenceTransformer(self.model_name)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.error("Error loading embedding model: %s", e)
                raise

    def preprocess_text(self, text):
        """Preprocess text for BM25 indexing."""
        return text.lower().strip()

    def tokenize(self, text):
        """Tokenize text into words for BM25."""
        return text.split(" ")

    def create_embeddings(self, texts):
        """Create embeddings for a list of texts using the sentence transformer."""
        if not self.model:
            self.load_embedding_model()

        try:
            logger.info("Creating embeddings for %d documents", len(texts))
            embeddings = self.model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
            logger.info("Embeddings created successfully")
            return embeddings
        except Exception as e:
            logger.error("Error creating embeddings: %s", e)
            return None

    def build_faiss_index(self, embeddings):
        """Build FAISS index from embeddings."""
        try:
            dimension = embeddings.shape[1]
            # Use L2 distance (Euclidean) for similarity
            index = faiss.IndexFlatL2(dimension)
            index.add(embeddings.astype('float32'))
            logger.info("FAISS index built with %d vectors", index.ntotal)
            return index
        except Exception as e:
            logger.error("Error building FAISS index: %s", e)
            return None

    def update_index(self):
        """Update both BM25 and FAISS indices with current documents."""
        if not self.documents:
            self.is_initialized = False
            return

        try:
            # 1. Update BM25 index (lexical search)
            self.corpus = [self.preprocess_text(doc) for doc in self.documents]
            tokenized_corpus = [self.tokenize(doc) for doc in self.corpus]
            self.bm25 = BM25Okapi(tokenized_corpus)
            logger.info("BM25 index updated successfully")

            # 2. Update FAISS index (semantic search)
            self.embeddings = self.create_embeddings(self.documents)
            if self.embeddings is not None:
                self.faiss_index = self.build_faiss_index(self.embeddings)
                self.is_initialized = True
                logger.info("Hybrid index (BM25 + FAISS) updated successfully")
            else:
                logger.warning("Failed to create embeddings, falling back to BM25 only")
                self.is_initialized = True  # Still usable with BM25
        except Exception as e:
            logger.error("Error updating indices: %s", e)
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
        """
        Retrieve relevant documents using hybrid search (FAISS + BM25).

        Uses Reciprocal Rank Fusion (RRF) to combine results from both methods.
        """
        if not self.is_initialized:
            return []

        try:
            results = {}

            # 1. BM25 (Lexical) Search
            tokenized_query = self.tokenize(self.preprocess_text(query))
            bm25_scores = self.bm25.get_scores(tokenized_query)

            # Get top documents from BM25
            bm25_top_indices = np.argsort(bm25_scores)[::-1][:top_n * 2]  # Get more for fusion

            # Add BM25 results with RRF scoring
            for rank, idx in enumerate(bm25_top_indices):
                doc_id = idx
                # RRF formula: 1 / (rank + k), where k=60 is standard
                rrf_score = 1 / (rank + 60)
                if doc_id in results:
                    results[doc_id] += rrf_score
                else:
                    results[doc_id] = rrf_score

            # 2. FAISS (Semantic) Search
            if self.faiss_index is not None:
                query_embedding = self.create_embeddings([query])
                if query_embedding is not None:
                    # Search FAISS index
                    distances, indices = self.faiss_index.search(
                        query_embedding.astype('float32'),
                        top_n * 2
                    )

                    # Add FAISS results with RRF scoring
                    for rank, idx in enumerate(indices[0]):
                        if idx != -1:  # Valid index
                            doc_id = int(idx)
                            rrf_score = 1 / (rank + 60)
                            if doc_id in results:
                                results[doc_id] += rrf_score
                            else:
                                results[doc_id] = rrf_score

            # 3. Combine and rank results
            sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
            top_doc_indices = [doc_id for doc_id, _ in sorted_results[:top_n]]

            # Return top documents
            top_docs = [self.documents[idx] for idx in top_doc_indices if idx < len(self.documents)]

            logger.info("Hybrid search for query: %s", query)
            logger.info("Retrieved %d documents", len(top_docs))

            return top_docs

        except Exception as e:
            logger.error("Error retrieving relevant documents: %s", e)
            return []
