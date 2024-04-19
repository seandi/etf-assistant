from typing import List
from loguru import logger

from langchain_core.documents import Document

from app.backend.splitters.page_split import PageSplitPDFSplitter
from app.backend.splitters.multi_modal import MultiModalPDFSplitter


class MultiModalPageSplitPDFSplitter(PageSplitPDFSplitter, MultiModalPDFSplitter):
    """
    A multi-modal splitter that handles images. For each page in the PDF a document is generated
    containing all the textual components found in that page, additionally images are extracted,
    captioned and filtered and an additional document is returned with the caption of relevant images
    such as plots and graphs.
    """

    def __init__(
        self,
        work_dir: str,
        extract_images: bool = False,
        filter_captions: bool = True,
        force_new: bool = False,
    ) -> None:
        super().__init__(
            work_dir,
            max_chunk_size=3000,  # These are irrelevant since textual chunks will be ignored in favor of pages
            min_chunk_size=0,  # These are irrelevant since textual chunks will be ignored in favor of pages
            extract_images=extract_images,
            filter_captions=filter_captions,
            force_new=force_new,
        )

    def split(self, file_path: str) -> List[Document]:
        pages = PageSplitPDFSplitter.split(self, file_path)
        if self.extract_images:
            docs = MultiModalPDFSplitter.split(self, file_path)
            image_docs = [doc for doc in docs if doc.metadata["doc_type"] == "image"]
        else:
            image_docs = []

        chunks = pages + image_docs

        logger.info(f"Generated {len(chunks)} chunks.")
        return chunks


if __name__ == "__main__":
    pdf_doc = "data/test/documents/swda_factsheet.pdf"

    splitter = PageSplitPDFSplitter()

    mm_splitter = MultiModalPageSplitPDFSplitter(
        work_dir="data/test/splitters_cache",
        extract_images=True,
        filter_captions=True,
    )

    docs = mm_splitter.split(pdf_doc)
    print(len(docs))
