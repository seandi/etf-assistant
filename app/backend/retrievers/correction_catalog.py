from typing import List, Tuple
from loguru import logger

from langchain_community.vectorstores.chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from app.backend.chains import FilterExtractionChain
from app.backend.utils import query_db
from app.backend.config import (
    SEARCH_TABLES,
    ETF_DB_PATH,
    CATALOG_COLUMNS,
    CATALOG_DB_PATH,
    CATALOG_DB_COLLECTION,
    CORRECTION_THRESHOLD,
)


class DBValuesCatalog:
    def __init__(self) -> None:
        self.filter_chain = FilterExtractionChain()

        self.vectorstore = Chroma(
            persist_directory=CATALOG_DB_PATH,
            collection_name=CATALOG_DB_COLLECTION,
            collection_metadata={"hnsw:space": "cosine"},
            embedding_function=OpenAIEmbeddings(),
        )

        df = query_db(query=f"SELECT * FROM {SEARCH_TABLES[0]}", db_path=ETF_DB_PATH)

        out_of_date = False
        docs, metadata = [], []
        for col in CATALOG_COLUMNS:
            values = self.vectorstore.get(where={"column": col})["documents"]

            _docs = df[col].unique()
            docs.extend(_docs)
            metadata.extend([{"column": col}] * len(_docs))

            if set(values) != set(_docs):
                print(set(values), set(_docs))
                out_of_date = True

        if out_of_date:
            logger.info("Catalog out of date, updating...")
            self.vectorstore.delete_collection()
            self.vectorstore._collection = self.vectorstore._client.create_collection(
                name=CATALOG_DB_COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
            self.vectorstore.add_texts(texts=docs, metadatas=metadata)

    def get_correction(self, column, value) -> str | None:
        doc, score = self.vectorstore.similarity_search_with_relevance_scores(
            query=value, k=1, filter={"column": column}
        )[0]

        if score > CORRECTION_THRESHOLD:
            return doc.page_content
        else:
            return None


if __name__ == "__main__":
    catalog = DBValuesCatalog()

    correction = catalog.get_correction(column="domicile_country", value="ireland")
    print(correction)
