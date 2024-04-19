from typing import List, Tuple, Any, Dict
import os
import pandas as pd
import random
from loguru import logger


from langchain.memory import ConversationBufferWindowMemory
from langchain_community.utilities.sql_database import SQLDatabase
from app.backend.chains import QueryGenerationChain, AnswerGenerationChain
from app.backend.prompts.etf import TABLES_DESCRIPTION, UNIQUE_COLUMNS

MAX_ROWS_TO_PASS = 3
N_SUGGESTIONS = 3
COLUMNS_TO_PASS = ["isin", "name"]
SEARCH_TABLES = ["etf_search_data"]

import sqlite3


class ETFDatabase:
    def __init__(self, db_path: str, tables_description: Dict[str, str]) -> None:
        self.db_path = db_path
        self.tables_description = tables_description

    def run_query(
        self, query, return_df: bool = True
    ) -> pd.DataFrame | Tuple[List[List[Any]], List[str]]:
        db_conn = sqlite3.connect(database=self.db_path)
        cursor = db_conn.cursor()

        res = cursor.execute(query)
        rows = res.fetchall()
        column_names = [col[0] for col in cursor.description]

        db_conn.close()

        if return_df:
            return pd.DataFrame(data=rows, columns=column_names)
        else:
            return rows, column_names

    def generate_tables_description(
        self,
        tables: List[str],
    ) -> str:

        db = SQLDatabase.from_uri(
            "sqlite:///" + self.db_path,
            view_support=True,
            sample_rows_in_table_info=0,
        )

        tables_info = []

        for table in tables:
            if table not in self.tables_description:
                logger.error(f"Table {table} not found!")

            schema = db.get_table_info_no_throw(table_names=[table])
            tables_info.append(self.tables_description[table] + "\n" + schema)

        return "\n\n".join(tables_info)


class ETFSearchChat:
    def __init__(self) -> None:

        self.etf_db = ETFDatabase(
            db_path=os.environ["ETF_DB"], tables_description=TABLES_DESCRIPTION
        )

        self.memory = ConversationBufferWindowMemory(
            input_key="question",
            output_key="answer",
            return_messages=True,
            k=5,
        )

        tables_description = self.etf_db.generate_tables_description(
            tables=SEARCH_TABLES
        )

        self.query_chain = QueryGenerationChain(
            tables_description=tables_description, memory=self.memory
        )
        self.answer_chain = AnswerGenerationChain(
            tables_description=tables_description,
            memory=self.memory,
            max_rows_to_pass=MAX_ROWS_TO_PASS,
        )

    def chat(self, question: str) -> Tuple[str, pd.DataFrame | None]:
        query = self.query_chain.run(question=question)
        logger.info(f"Generated the following query: {query}")

        if query is None or "*" not in query:
            raise NotImplementedError

        etfs_found_df = self.etf_db.run_query(query=query)
        # print(etfs_found_df.columns.to_list())
        results_to_pass = etfs_found_df.drop(
            columns=[
                c for c in etfs_found_df.columns.to_list() if c not in COLUMNS_TO_PASS
            ]
        ).values.tolist()

        if len(etfs_found_df) > MAX_ROWS_TO_PASS:
            suggestions = self.find_suggestions(etfs_df=etfs_found_df, n=N_SUGGESTIONS)
        else:
            suggestions = None

        answer = self.answer_chain.run(
            question=question,
            query=query,
            results=results_to_pass,
            suggestions=suggestions,
        )

        self.memory.save_context(
            inputs={"question": question}, outputs={"answer": answer}
        )

        return answer, etfs_found_df

    def find_suggestions(self, etfs_df: pd.DataFrame, n: int = 3):
        # Found columns in df that have more than one unique values
        differing_columns = etfs_df.columns[etfs_df.nunique() > 1].to_list()
        # Exclude columns that always have different values
        differing_columns = [c for c in differing_columns if c not in UNIQUE_COLUMNS]

        return random.sample(differing_columns, k=min(n, len(differing_columns)))


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(override=True)

    chat = ETFSearchChat()
    #
    while True:
        q = input("prompt -> ")
        answer, etf_df = chat.chat(question=q)
        print(f"answer-> {answer}")
