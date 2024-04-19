from abc import abstractmethod, ABCMeta
from typing import List
from loguru import logger

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_community.vectorstores.chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from app.backend.splitters import PDFSplitter


class ChromaRetriever:
    def __init__(
        self,
        chroma_store: str,
        collection: str | None = None,
        embeddings=OpenAIEmbeddings(),
        top_k: int = 4,
        source_id: str | None = None,
        search_type: str = "mmr",
    ) -> None:

        self.embeddings = embeddings
        self.top_k = top_k
        self.source_id = source_id
        self.search_type = search_type

        self.search_config = {
            "k": self.top_k,
        }
        if source_id is not None:
            self.search_config["filter"] = {"source_id": self.source_id}

        self.vectorstore = Chroma(
            persist_directory=chroma_store,
            collection_name=collection,
            collection_metadata={"hnsw:space": "cosine"},
            embedding_function=embeddings,
        )

    def get_documents(self, source_id: str | None = None) -> List[Document]:
        data = (
            self.vectorstore.get()
            if source_id is None
            else self.vectorstore.get(where={"source_id": source_id})
        )

        docs = []
        for i in range(len(data["ids"])):
            docs.append(
                Document(
                    page_content=data["documents"][i], metadata=data["metadatas"][i]
                )
            )

        return docs

    def delete_source_data(self, source_id: str):
        data = self.vectorstore.get(where={"source_id": source_id})
        chunks_ids = data["ids"]

        self.vectorstore.delete(ids=chunks_ids)

    def reset(self):
        """Completely resets the vectorstore current collection."""

        collection_name = self.vectorstore._collection.name
        self.vectorstore.delete_collection()
        self.vectorstore._collection = self.vectorstore._client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_file(
        self,
        file_path: str,
        splitter: PDFSplitter,
    ):
        docs = splitter.split(file_path=file_path)

        self.vectorstore.add_documents(documents=docs)
        logger.info(f"Added {len(docs)} documents to the database.")

    def get_retriever(self) -> BaseRetriever:
        return self.vectorstore.as_retriever(
            search_type=self.search_type,
            search_kwargs=self.search_config,
        )

    @staticmethod
    def combine_docs(docs: List[Document]) -> str:
        return "\n\n".join([doc.page_content for doc in docs])


if __name__ == "__main__":
    from app.backend.splitters import PageSplitPDFSplitter

    pdf_doc = "experimental/data/documents/vwce_kid.pdf"

    retriever = ChromaRetriever(
        chroma_store="data/test/retriever/chromadb",
        collection="vwce_page_split_test_v1",
        pdf_chunker=PageSplitPDFSplitter(),
    )

    retriever.reset()
    retriever.add_file(pdf_doc)

    docs = retriever.get_documents()

    print(docs[0].metadata)
    retriever.reset()
