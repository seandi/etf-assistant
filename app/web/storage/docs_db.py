import sqlite3
from typing import List, Tuple
from dataclasses import dataclass
from loguru import logger

CREATE_DOC_TABLE = """
CREATE TABLE IF NOT EXISTS etf_docs (
    doc_id integer PRIMARY KEY,
    bucket_file_id VARCHAR(50),
    vectorstore_id VARCHAR(50),
    name VARCHAR(100),
    description VARCHAR(500),
    top_k INTEGER,
    filter_sources BOOLEAN
);
"""

CREATE_DOC_TO_ETF_TABLE = """
CREATE TABLE IF NOT EXISTS doc_to_etf (
    id integer PRIMARY KEY,
    etf_isin TEXT,
    doc_id integer,
    FOREIGN KEY (etf_isin)
        REFERENCES etf_data (isin),
    FOREIGN KEY (doc_id)
        REFERENCES etf_docs (doc_id)
);
"""

INSERT_DOC = """
INSERT INTO etf_docs(bucket_file_id, vectorstore_id, name, description, top_k, filter_sources)
VALUES(?,?,?,?,?,?);
"""

INSERT_DOC_TO_ETF_RELATION = """
INSERT INTO doc_to_etf(doc_id, etf_isin)
VALUES (?,?);
"""


@dataclass
class DocMetadata:
    id: int
    bucket_filename: str
    vectorstore_source_id: str
    name: str
    description: str | None
    top_k: int
    filter_sources: bool


class ETFDocumentsDatabase:
    def __init__(self, db_path) -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(CREATE_DOC_TABLE)
        self.conn.execute(CREATE_DOC_TO_ETF_TABLE)

    def add_new_doc(
        self,
        bucket_file: str,
        vectorstore_id: str,
        name: str,
        description: str | None = None,
        top_k: int = 4,
        filter_sources: bool = True,
    ) -> int | None:

        cursor = self.conn.cursor()
        cursor.execute(
            INSERT_DOC,
            (bucket_file, vectorstore_id, name, description, top_k, filter_sources),
        )
        self.conn.commit()

        return cursor.lastrowid

    def assign_doc_to_etf(
        self,
        doc_id: int,
        etf_isin: str,
    ) -> int | None:

        cursor = self.conn.cursor()

        if len(
            cursor.execute(
                f"SELECT * FROM doc_to_etf WHERE doc_id = '{doc_id}' AND etf_isin = '{etf_isin}';",
            ).fetchall()
        ):
            logger.error(f"Trying to create an assignment that already exists")
            return None

        cursor.execute(
            INSERT_DOC_TO_ETF_RELATION,
            (doc_id, etf_isin),
        )
        self.conn.commit()

        return cursor.lastrowid

    def get_docs(self):
        cursor = self.conn.cursor()
        cursor.execute(
            f"SELECT * FROM etf_docs;",
        )

        rows = cursor.fetchall()

        return [DocMetadata(*row) for row in rows]

    def get_docs_by_etf(self, etf_isin) -> List[DocMetadata]:
        cursor = self.conn.cursor()
        cursor.execute(
            f"SELECT * FROM etf_docs WHERE doc_id IN (SELECT doc_id FROM doc_to_etf WHERE etf_isin = '{etf_isin}');",
        )

        rows = cursor.fetchall()

        return [DocMetadata(*row) for row in rows]

    def get_doc_etfs(self, doc_id) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute(
            f"SELECT etf_isin FROM doc_to_etf WHERE doc_id = '{doc_id}';",
        )

        rows = cursor.fetchall()

        return [row[0] for row in rows]

    def delete_doc(
        self,
        doc_id: int,
    ) -> bool:
        cursor = self.conn.cursor()
        cursor.execute(f"DELETE FROM etf_docs WHERE doc_id = '{doc_id}';")
        cursor.execute(f"DELETE FROM doc_to_etf WHERE doc_id = '{doc_id}';")
        self.conn.commit()

    def unassign_doc(self, doc_id, etf_isin):
        cursor = self.conn.cursor()
        cursor.execute(
            f"DELETE FROM doc_to_etf WHERE doc_id = '{doc_id}' AND etf_isin = '{etf_isin}';"
        )
        self.conn.commit()


if __name__ == "__main__":
    import dotenv, os

    dotenv.load_dotenv(override=True)
    db = ETFDocumentsDatabase(os.environ["DOC_DB"])

    isin = "ISIN"
    doc_id = db.add_new_doc("A", "B", "c")
    db.assign_doc_to_etf(doc_id, etf_isin=isin)

    try:
        cursor = db.conn.cursor()
        cursor.execute(
            f"SELECT * FROM doc_to_etf WHERE doc_id = '{doc_id}' AND etf_isin = '{isin}';",
        ).fetchall()
        print(cursor.fetchall())
    except Exception as e:
        print(e)

    print(db.get_doc_etfs(doc_id=doc_id))
    db.delete_doc(doc_id=doc_id)
