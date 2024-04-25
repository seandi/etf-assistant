from typing import List, Tuple
import os
from io import BytesIO
import base64
import shutil
from fitz import Document
import math
from loguru import logger

from app.web.utils import get_rand_str
from app.web.storage.docs_db import ETFDocumentsDatabase, DocMetadata
from app.web.storage.bucket import BucketStorage


from app.backend.retrievers import MultiModalChromaRetriever
from app.backend.splitters import MultiModalPDFSplitter, MultiModalPageSplitPDFSplitter


TMP_WORKING_FOLDER = "work_dir"


# Wrapper for adding, retrieving and/or updating etf docs
class ETFDocStorage:
    def __init__(self) -> None:
        self.docs_db = ETFDocumentsDatabase(db_path=os.environ.get("DOC_DB"))
        self.docs_bucket = BucketStorage(
            url=os.environ.get("BUCKET_URL"),
            key=os.environ.get("BUCKET_KEY"),
            secret=os.environ.get("BUCKET_SECRET"),
        )
        self.retriever = MultiModalChromaRetriever(
            chroma_store=os.environ["RETRIEVER_VECTORSTORE_PATH"],
            local_store=os.environ["RETRIEVER_DOCSTORE_PATH"],
            collection=os.environ["RETRIEVER_VECTORSTORE_COLLECTION"],
        )

    # Add to bucket, # add to vector store, # add to db
    def add_document(
        self,
        data: BytesIO,
        name: str,
        split_by: str,
        multimodal: bool,
        top_k: int,
        description: str | None = None,
        filter_sources: bool = False,
        assigned_etfs: List[str] = [],
    ) -> int | None:

        doc_id = None
        bucket = os.environ.get("BUCKET_NAME")

        try:
            bucket_file = self.docs_bucket.add_file(bucket=bucket, data=data)
        except Exception as e:
            logger.opt(exception=e).error("Failed to add file to bucket.")
            return doc_id

        try:
            if split_by == "bypage":
                splitter = MultiModalPageSplitPDFSplitter(
                    work_dir=os.environ["SPLITTERS_CACHE"],
                    extract_images=multimodal,
                    filter_captions=multimodal,
                )

            elif split_by == "bylayout":
                splitter = MultiModalPDFSplitter(
                    work_dir=os.environ["SPLITTERS_CACHE"],
                    max_chunk_size=3000,
                    min_chunk_size=0,
                    extract_images=multimodal,
                    filter_captions=multimodal,
                )
            else:
                raise NotImplementedError

            tmp_file = os.path.join(TMP_WORKING_FOLDER, get_rand_str(12))
            os.makedirs(TMP_WORKING_FOLDER, exist_ok=True)
            open(tmp_file, "wb").write(data.getvalue())

            vectordb_source_id = self.retriever.add_file(
                file_path=tmp_file, splitter=splitter
            )
            os.remove(tmp_file)
        except Exception as e:
            logger.opt(exception=e).error("Failed to add document to the vectorstore")
            self.docs_bucket.delete_file(bucket=bucket, filename=bucket_file)
            return doc_id

        try:
            doc_id = self.docs_db.add_new_doc(
                name=name,
                description=description,
                bucket_file=bucket + "/" + bucket_file,
                vectorstore_id=vectordb_source_id,
                top_k=top_k,
                filter_sources=filter_sources,
            )
        except Exception as e:
            logger.opt(exception=e).error("Failed to add document to the database")
            # Undo operation
            self.docs_bucket.delete_file(bucket=bucket, filename=bucket_file)
            return doc_id

        if len(assigned_etfs):
            for etf_isin in assigned_etfs:
                res = self.docs_db.assign_doc_to_etf(doc_id=doc_id, etf_isin=etf_isin)
                if res is None:
                    logger.warning(f"Skipped etf {etf_isin}!")

        return doc_id

    def get_documents(
        self,
        etf_isin: str,
    ) -> List[Tuple[DocMetadata, bytes]]:

        docs_metadata: List[DocMetadata] = self.docs_db.get_docs_by_etf(
            etf_isin=etf_isin
        )

        if len(docs_metadata) == 0:
            return []

        os.makedirs(TMP_WORKING_FOLDER, exist_ok=True)
        docs = []
        for doc_metadata in docs_metadata:
            bucket, filename = doc_metadata.bucket_filename.split("/")
            doc_tmp_path = self.docs_bucket.get_file(
                bucket=bucket,
                filename=filename,
                save_folder=TMP_WORKING_FOLDER,
            )
            with open(doc_tmp_path, "rb") as f:
                doc_bytes = f.read()

            docs.append((doc_metadata, doc_bytes))

        shutil.rmtree(TMP_WORKING_FOLDER)
        return docs

    def delete_doc(self, doc_id: int):
        res = self.docs_db.delete_doc(doc_id=doc_id)

        if not res:
            return False

        return True
