from typing import List
from langchain_community.document_loaders.pdf import PyMuPDFLoader
from langchain_core.documents import Document

from app.backend.splitters.base import PDFSplitter
from app.backend.utils import compute_file_digest


class PageSplitPDFSplitter(PDFSplitter):
    """A simple splitter the creates a document for each page in the PDF. Images are ignored."""

    def split(self, file_path: str) -> List[Document]:
        file_digest = compute_file_digest(file_path)

        pages = PyMuPDFLoader(file_path).load()

        for page in pages:
            page.metadata["doc_type"] = "text"
            page.metadata["page"] += 1  # correct counting from zero
            page.metadata["source_id"] = file_digest

        return pages


if __name__ == "__main__":
    pdf_doc = "data/test/documents/swda_factsheet.pdf"

    splitter = PageSplitPDFSplitter()

    docs = splitter.split(pdf_doc)
    print(len(docs))
    print(docs[0].metadata)
