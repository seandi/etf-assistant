from typing import Tuple
import pandas as pd
import random
from loguru import logger


from langchain.memory import ConversationBufferWindowMemory
from langchain_community.utilities.sql_database import SQLDatabase
from app.backend.chains import (
    QueryGenerationChain,
    AnswerGenerationChain,
)
from app.backend.prompts.etf import TABLES_DESCRIPTION, UNIQUE_COLUMNS
from app.backend.utils import query_db
from app.backend.config import (
    MAX_ROWS_TO_PASS,
    N_SUGGESTIONS,
    COLUMNS_TO_PASS,
    SEARCH_TABLES,
    ETF_DB_PATH,
)


class ETFSearchChat:
    def __init__(self) -> None:

        self.memory = ConversationBufferWindowMemory(
            input_key="question",
            output_key="answer",
            return_messages=True,
            k=5,
        )

        self.query_chain = QueryGenerationChain(
            db_description=self._build_db_description(db_path=ETF_DB_PATH),
            memory=self.memory,
        )
        self.answer_chain = AnswerGenerationChain(
            memory=self.memory,
            max_rows_to_pass=MAX_ROWS_TO_PASS,
        )

    def chat(self, question: str) -> Tuple[str, pd.DataFrame | None]:
        query, answer = self.query_chain.run(question=question)
        logger.info(f"Generated the following query: {query}")

        if query is None and answer is None:
            return "I am sorry but I was not able to generate a valid response!", None

        if query is None:
            etfs_found_df = None
        else:
            etfs_found_df = query_db(db_path=ETF_DB_PATH, query=query)
            # print(etfs_found_df.columns.to_list())
            results_to_pass = etfs_found_df.drop(
                columns=[
                    c
                    for c in etfs_found_df.columns.to_list()
                    if c not in COLUMNS_TO_PASS
                ]
            ).values.tolist()

            if len(etfs_found_df) > MAX_ROWS_TO_PASS:
                suggestions = self.find_suggestions(
                    etfs_df=etfs_found_df, n=N_SUGGESTIONS
                )
            else:
                suggestions = None

            answer = self.answer_chain.run(
                question=question,
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

    @staticmethod
    def _build_db_description(db_path) -> str:
        db = SQLDatabase.from_uri(
            "sqlite:///" + db_path,
            view_support=True,
            sample_rows_in_table_info=0,
        )

        tables_info = []

        for table in SEARCH_TABLES:
            if table not in TABLES_DESCRIPTION:
                logger.error(f"Table {table} not found!")

            schema = db.get_table_info_no_throw(table_names=[table])
            tables_info.append(TABLES_DESCRIPTION[table] + "\n" + schema)

        return "\n\n".join(tables_info)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv(override=True)

    chat = ETFSearchChat()
    #
    while True:
        q = input("prompt -> ")
        answer, etf_df = chat.chat(question=q)
        print(f"answer-> {answer}")
