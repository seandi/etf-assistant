from typing import Tuple, List
import os
import sqlite3
import pandas as pd
import random
import string
from loguru import logger
from dataclasses import dataclass

from app.web.storage.docs_db import DocMetadata
from app.backend.retrievers import MultiModalChromaRetriever
from app.backend.chats.docqa import DocumentsQAChat


@dataclass
class DocQAMessage:
    role: str
    message: str
    sources: List


def get_rand_str(n: int) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def load_etf_db() -> pd.DataFrame:
    conn = sqlite3.Connection(os.environ["ETF_DB"])
    etf_data_df = pd.read_sql(f"select * from {os.environ['DISPLAY_TABLE']}", con=conn)

    return etf_data_df


def create_docqa_chat(doc_metadata: DocMetadata) -> DocumentsQAChat:
    retriever = MultiModalChromaRetriever(
        chroma_store=os.environ["RETRIEVER_VECTORSTORE_PATH"],
        local_store=os.environ["RETRIEVER_DOCSTORE_PATH"],
        collection=os.environ["RETRIEVER_VECTORSTORE_COLLECTION"],
        top_k=doc_metadata.top_k,
        source_id=doc_metadata.vectorstore_source_id,
    )
    chat = DocumentsQAChat(
        retriever=retriever.get_retriever(),
        combine_docs_func=retriever.combine_docs,
        filter_irrelevant_sources=doc_metadata.filter_sources,
    )
    logger.info(
        f"Initialized new chat on document {retriever.source_id} uising the {retriever.top_k} most relevant chunks."
    )

    return chat
