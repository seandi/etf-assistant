from typing import List, Dict
from operator import itemgetter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain.memory.chat_memory import BaseChatMemory
from langchain_openai import ChatOpenAI
from langchain_community.utilities.sql_database import SQLDatabase
from langfuse.callback import CallbackHandler


ANSWER_TEMPLATE_FEW_ETFS = """Your task is to repsond to the user question based solely on the previous messagges in the conversation and the list of ETFs found in the database. If no ETFs were found, you should simply respond saying so.

Question:
{question}

Previous messages:
{history}

ETFs found in the database:
{results}
"""

# ANSWER_TEMPLATE_MANY_ETFS = """Your task is to repsond to the user question by informing him/her on the number of ETFs that were found in the database and inviting him/her to consult the table on the left containing the ETFs found (the table will be shown by the frontend, its not jour job to create it).

# Question:
# {question}

# Previous messages:
# {history}

# Number of ETFs found:
# {n_results}

# """

ANSWER_TEMPLATE_MANY_ETFS = """Your task is to repsond to the user question by informing him/her on the number of ETFs that were found in the database and inviting him/her to consult the table on the left containing the ETFs found (the table will be shown by the frontend, its not jour job to create it).
Your are also provided with some suggestions of possible additional information that you can invite to user to provide for further narrowing down the search.

Question:
{question}

Previous messages:
{history}

Number of ETFs found:
{n_results}

Suggestions:
{suggestions}
"""


class AnswerGenerationChain:
    def __init__(
        self,
        memory: BaseChatMemory | None = None,
        max_rows_to_pass: int = 3,
    ) -> None:

        # Memory is externally managed
        self.memory = memory
        self.max_rows_to_pass = max_rows_to_pass

        chain_additional_inputs = {
            "history": RunnableLambda(self.memory.load_memory_variables)
            | itemgetter("history")
        }

        self.chain = RunnablePassthrough.assign(
            **chain_additional_inputs
        ) | RunnableLambda(self.make_answer_chain)

    def make_answer_chain(self, chain_inputs: Dict):
        n_results = chain_inputs["n_results"]

        chain = (
            RunnablePassthrough.assign(
                results=lambda inputs: str(
                    inputs["results"][: min(n_results, self.max_rows_to_pass)]
                )
            )
            | ChatPromptTemplate.from_template(
                ANSWER_TEMPLATE_MANY_ETFS
                if n_results > self.max_rows_to_pass
                else ANSWER_TEMPLATE_FEW_ETFS
            )
            | ChatOpenAI()
            | StrOutputParser()
        )

        return chain

    def run(
        self,
        question: str,
        results: List,
        suggestions: List[str],
        callbacks: List = [],
    ) -> str | None:
        answer = self.chain.invoke(
            {
                "question": question,
                "results": results,
                "n_results": len(results),
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
