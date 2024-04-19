from typing import List, Dict
import json
from operator import itemgetter
from langchain_core.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    ChatPromptTemplate,
)
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain.memory.chat_memory import BaseChatMemory
from langchain_openai import ChatOpenAI
from langchain_community.utilities.sql_database import SQLDatabase
from langfuse.callback import CallbackHandler


QUERY_GENERATION_SYSTEM_PROMPT = """You are assistant designed to generate a correct SQL query to find all ETFs that match the user reuqest from an SQLITE database containing the tables described below.
Each row in the database correspond to an etf.

Tables description:
{tables}

You can use any column for filtering and you MUST select ALL columns of each eft found.
The QUERY should use a proper syntax for sqlite, in particular you must use double quotes for table and column names.
You MUST respond with a JSON object with a single key 'query' that contains the generated query.
"""


class QueryGenerationChain:
    def __init__(
        self,
        tables_description: str,
        memory: BaseChatMemory | None = None,
    ) -> None:

        self.tables_description = tables_description

        # Memory is externally managed
        self.memory = memory

        prompt_messages = [
            SystemMessagePromptTemplate.from_template(QUERY_GENERATION_SYSTEM_PROMPT)
        ]
        if self.memory is not None:
            prompt_messages.append(MessagesPlaceholder("history"))
        prompt_messages.append(HumanMessagePromptTemplate.from_template("{question}"))

        chain_additional_inputs = {}
        if self.memory is not None:
            chain_additional_inputs["history"] = RunnableLambda(
                self.memory.load_memory_variables
            ) | itemgetter("history")

        self.chain = (
            RunnablePassthrough.assign(**chain_additional_inputs)
            | ChatPromptTemplate.from_messages(messages=prompt_messages)
            | ChatOpenAI(model_kwargs={"response_format": {"type": "json_object"}})
            | StrOutputParser()
        )

    def run(self, question: str, callbacks: List = []) -> str | None:
        res = self.chain.invoke(
            {"question": question, "tables": self.tables_description},
            config={"callbacks": callbacks},
        )

        try:
            res_dict = json.loads(res)
        except:
            return None

        if "query" in res_dict:
            return res_dict["query"]
        if len(res_dict) == 1:
            return list(res_dict.values())[0]

        return None


if __name__ == "__main__":
    from app.backend.prompts.etf import TABLES_DESCRIPTION

    chat = QueryGenerationChain(
        db=SQLDatabase.from_uri(
            "sqlite:///data/sqlite/etf.sqlite3",
            view_support=True,
            sample_rows_in_table_info=1,
        ),
        tables_description=TABLES_DESCRIPTION,
    )

    question = "Im interested in ETFs domiciled in Ireland"

    query = chat.run(question=question)
    print(query)
