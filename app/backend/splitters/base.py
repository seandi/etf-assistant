from typing import List
from abc import ABC, abstractmethod
from langchain_core.documents import Document


class PDFSplitter(ABC):
    @abstractmethod
    def split(self, file_path: str) -> List[Document]:
        pass

    @staticmethod
    def pretty_print_chunks(chunks: List[Document], file: str | None = None):
        chunks_by_page = {}
        for chunk in chunks:
            page = chunk.metadata["page"]
            if page not in chunks_by_page:
                chunks_by_page[page] = []

            chunks_by_page[page].append(chunk)

        chunks_by_page = dict(sorted(chunks_by_page.items()))

        out = ""
        for page, chunks in chunks_by_page.items():
            out += "\n-----------------------------------------------------------------------------------------------------------"

            out += f"\n|                                                 PAGE {page}                                                   |"

            for chunk in chunks:
                out += "\n\n-----------------------------------------------------------------------------------------------------------\n"
                out += chunk.page_content

        if file is not None:
            with open(file, "w") as f:
                f.write(out)

        return out
