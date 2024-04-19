from typing import List, Optional, Sequence, Tuple
import os
import uuid
import shutil
import pickle
from langchain_core.retrievers import BaseRetriever
from loguru import logger
from langchain.retrievers import MultiVectorRetriever
from langchain.storage import LocalFileStore
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings


from app.backend.splitters import PDFSplitter
from app.backend.retrievers import ChromaRetriever
from app.backend.utils import get_rand_str, compute_file_digest
from app.backend.chains.docqa.summarize_table import create_summarize_chain


class SerializableLocalDocumentStore(LocalFileStore):
    """
    Wraps the LocalFileStore to make the retrieved documents serializable by returning them as strings instead of bytes.
    """

    def mset(self, key_value_pairs: Sequence[Tuple[str, Document]]) -> None:

        serialized_key_value_pairs = [(k, pickle.dumps(v)) for k, v in key_value_pairs]
        return super().mset(serialized_key_value_pairs)

    def mget(self, keys: Sequence[str]) -> List[Optional[Document]]:
        values_bytes = super().mget(keys)
        docs = [pickle.loads(v) if v is not None else v for v in values_bytes]
        return docs


class MultiModalChromaRetriever(ChromaRetriever):

    def __init__(
        self,
        chroma_store: str,
        local_store: str,
        collection: str | None = None,
        embeddings=OpenAIEmbeddings(),
        top_k: int = 4,
        source_id: (
            str | None
        ) = None,  # Used only for retrieval, not for adding new docs
        search_type: str = "mmr",
    ) -> None:

        super().__init__(
            chroma_store=chroma_store,
            collection=collection,
            embeddings=embeddings,
            top_k=top_k,
            source_id=source_id,
            search_type=search_type,
        )

        self.local_store_folder = os.path.join(local_store, collection)
        store = SerializableLocalDocumentStore(root_path=self.local_store_folder)

        self.docstore_id = "doc_id"
        self.retriever = MultiVectorRetriever(
            vectorstore=self.vectorstore,
            docstore=store,
            id_key=self.docstore_id,
            search_kwargs=self.search_config,
            search_type=self.search_type,
        )

        self.table_summarize_chain = create_summarize_chain()

    def get_retriever(self) -> BaseRetriever:
        return self.retriever

    def add_file(self, file_path: str, splitter: PDFSplitter) -> str:
        docs = splitter.split(file_path=file_path)

        texts, tables, images = [], [], []
        for doc in docs:
            doc_t = doc.metadata["doc_type"]
            if doc_t == "text":
                texts.append(doc)
            elif doc_t == "table":
                tables.append(doc)
            elif doc_t == "image":
                images.append(doc)
            else:
                logger.error(f"Doc type {doc_t} not supported!")
                raise NotImplementedError

        self._add_textual_docs(texts)
        self._add_tables(tables)
        self._add_images(images)

        # Return the file digest as ID for all chunks created from the given source
        return docs[0].metadata["source_id"]

    def delete_source_data(self, source_id: str):
        data = self.vectorstore.get(where={"source_id": source_id})
        chunks_ids = data["ids"]
        chunks_docs_ids = [md[retriever.docstore_id] for md in data["metadatas"]]

        self.vectorstore.delete(ids=chunks_ids)
        self.retriever.docstore.mdelete(keys=chunks_docs_ids)

    def _add_textual_docs(self, docs: List[Document]):
        if len(docs) == 0:
            return

        doc_ids = []
        for doc in docs:
            id = str(uuid.uuid4())
            doc.metadata[self.docstore_id] = id
            doc_ids.append(id)

        self.retriever.vectorstore.add_documents(docs)
        self.retriever.docstore.mset(list(zip(doc_ids, docs)))

    def _add_tables(self, docs: List[Document]):
        if len(docs) == 0:
            return

        table_summaries = self.summarize_tables([doc.page_content for doc in docs])

        doc_ids = []
        summary_docs = []
        for i in range(len(docs)):
            id = str(uuid.uuid4())
            summary_doc = Document(
                page_content=table_summaries[i], metadata=docs[i].metadata
            )
            summary_doc.metadata[self.docstore_id] = id
            doc_ids.append(id)
            summary_docs.append(summary_doc)

        self.retriever.vectorstore.add_documents(summary_docs)
        self.retriever.docstore.mset(list(zip(doc_ids, docs)))

    def _add_images(self, docs: List[Document]):
        if len(docs) == 0:
            return

        doc_ids = []
        for doc in docs:
            id = str(uuid.uuid4())
            doc.metadata[self.docstore_id] = id
            doc_ids.append(id)

        self.retriever.vectorstore.add_documents(docs)
        self.retriever.docstore.mset(list(zip(doc_ids, docs)))

    def reset(self):
        super().reset()
        if os.path.exists(self.local_store_folder):
            shutil.rmtree(self.local_store_folder)

    def summarize_tables(self, tables: List[str]):
        return self.table_summarize_chain.batch(tables, {"max_concurrency": 5})

    def log_docs(self, docs):
        for i, doc in enumerate(docs):
            logger.info(f"Document {i+1}:")
            logger.info(doc)
        return docs


if __name__ == "__main__":
    from app.backend.splitters import MultiModalPDFSplitter, PageSplitPDFSplitter

    pdf_doc = "data/test/documents/swda_factsheet.pdf"
    source_id = get_rand_str(12)

    retriever = MultiModalChromaRetriever(
        chroma_store="data/test/retriever/chromadb",
        local_store="data/test/retriever/file_stores",
        collection="mm_retriever_test",
        top_k=4,
        source_id=source_id,
    )

    splitter = PageSplitPDFSplitter()
    retriever.reset()

    retriever.add_file(file_path=pdf_doc, splitter=splitter)
    docs = retriever.get_documents(source_id=source_id)
    assert len(docs) == 6, docs

    docs = retriever.get_retriever().get_relevant_documents(
        "Which are the top holdings?"
    )
    assert len(docs) == 4

    retriever.delete_source_data(source_id=source_id)
    docs = retriever.get_documents(source_id=source_id)
    assert len(docs) == 0
