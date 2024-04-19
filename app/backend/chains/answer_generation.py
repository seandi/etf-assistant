from typing import List, Dict
import json
from operator import itemgetter
from langchain_core.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    AIMessagePromptTemplate,
    MessagesPlaceholder,
    ChatPromptTemplate,
)
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain.memory.chat_memory import BaseChatMemory
from langchain_openai import ChatOpenAI
from langchain_community.utilities.sql_database import SQLDatabase
from langfuse.callback import CallbackHandler


ANSWER_GENERATION_SYSTEM_PROMPT = """You are assistant designed to generate a correct SQL query to find all information necessary to answer the user question from an sqlite database containing the tables described below.

Tables description:
{tables}


You should always respond with a JSON object with a single key 'query' that contains the generated query.
"""

QUERY_RECALL_SELF_PROMPT = """To answer the user question I have generated the SQL query reported below on a database with tables described below.
Tables description:
{tables}

Generated query:
{query} 
"""

NO_RESULT_SELF_PROMPT = """
I have found no ETF matching the user request.
"""


PARTIAL_RESULT_SELF_PROMPT = """I have found all the ETFs in the database the match the user request and they will be shown on screen in a table.
Below are reported the Name and ISIN of just a few sample ETFs among those. 

ETF samples:
{results}

I should answer the user using these samples to provide some example of ETF that match the request, however I MUST recall to the user that these are just a few example and that there may be other ETFs that match his/her requirements. I should prompt the user to provide more details such that I can help narrow down the selection of ETFs, I should ask for more information on {suggestions}.
"""

FULL_RESULT_SELF_PROMPT = """I have found all the ETFs in the database the match the user request. Below are reported the Name and ISIN of all the ETFs I have found. 

ETFs:
{results}

I should report these results to the user and remember to him/her that additional details on the ETFs found are reported on screen in the corresponding table.
"""


class AnswerGenerationChain:
    def __init__(
        self,
        tables_description: str,
        memory: BaseChatMemory | None = None,
        max_rows_to_pass: int = 3,
    ) -> None:

        self.tables_description = tables_description
        # Memory is externally managed
        self.memory = memory
        self.max_rows_to_pass = max_rows_to_pass

        chain_additional_inputs = {}
        if self.memory is not None:
            chain_additional_inputs["history"] = RunnableLambda(
                self.memory.load_memory_variables
            ) | itemgetter("history")

        self.chain = RunnablePassthrough.assign(
            **chain_additional_inputs
        ) | RunnableLambda(self.make_answer_chain)

    def make_answer_chain(self, chain_inputs: Dict):
        n_results = len(chain_inputs["results"])

        prompt_messages = []
        if self.memory is not None:
            prompt_messages.append(MessagesPlaceholder("history"))
        prompt_messages.extend(
            [
                HumanMessagePromptTemplate.from_template("{question}"),
                AIMessagePromptTemplate.from_template(QUERY_RECALL_SELF_PROMPT),
            ]
        )

        if n_results == 0:
            template = NO_RESULT_SELF_PROMPT
        if n_results > self.max_rows_to_pass:
            template = PARTIAL_RESULT_SELF_PROMPT
        else:
            template = FULL_RESULT_SELF_PROMPT

        prompt_messages.append(AIMessagePromptTemplate.from_template(template))

        chain = (
            RunnablePassthrough.assign(
                results=lambda inputs: str(
                    inputs["results"][: min(n_results, self.max_rows_to_pass)]
                )
            )
            | ChatPromptTemplate.from_messages(prompt_messages)
            | ChatOpenAI()
            | StrOutputParser()
        )

        return chain

    def run(
        self,
        question: str,
        query: str,
        results: List,
        suggestions: List[str],
        callbacks: List = [],
    ) -> str | None:
        answer = self.chain.invoke(
            {
                "question": question,
                "tables": self.tables_description,
                "query": query,
                "results": results,
                "suggestions": suggestions,
            },
            config={"callbacks": callbacks},
        )

        return answer


if __name__ == "__main__":
    from app.backend.prompts.etf import TABLES_DESCRIPTION

    chat = AnswerGenerationChain(
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
