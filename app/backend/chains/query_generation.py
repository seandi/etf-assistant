from typing import List, Dict
from loguru import logger
from operator import itemgetter
from langchain_core.prompts import (
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    ChatPromptTemplate,
)
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers.openai_tools import PydanticToolsParser
from langchain.memory.chat_memory import BaseChatMemory
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field


QUERY_GENERATION_SYSTEM_PROMPT = """You are assistant designed to answer user questions. 
You have access to a {dialect} database of ETFs with tables described below. 
If the LAST user question involves extracting data from this database, then you should generate a correct SQL query to find all ETFs that match the user reuqest. 
You can use any column for filtering and you MUST select ALL columns of each eft found.
Otherwise, you can directly answer the user question.

Database tables description:
{tables}


You must call either one of two tools: 
    - 'query_database' if you need to extract data from the db to answer the user 
    - 'answer_directly' if the last question does not involve the database 
"""


class query_database(BaseModel):
    """Executes the SQL query to retrieve the data from the database."""

    query: str = Field(..., description="The SQL query to execute")


class answer_directly(BaseModel):
    """Directly answer the user if its question does not require extracting data from the database"""

    answer: str = Field(..., description="The answer")


class QueryGenerationChain:
    def __init__(
        self,
        db_description: str,
        memory: BaseChatMemory | None = None,
    ) -> None:

        self.db_description = db_description

        # Memory is externally managed
        self.memory = memory
        self.tools = [query_database, answer_directly]

        prompt_messages = [
            SystemMessagePromptTemplate.from_template(QUERY_GENERATION_SYSTEM_PROMPT)
        ]
        prompt_messages.append(MessagesPlaceholder("history"))
        prompt_messages.append(HumanMessagePromptTemplate.from_template("{question}"))

        chain_additional_inputs = {
            "history": RunnableLambda(self.memory.load_memory_variables)
            | itemgetter("history")
        }

        self.chain = (
            RunnablePassthrough.assign(**chain_additional_inputs)
            | ChatPromptTemplate.from_messages(messages=prompt_messages)
            | ChatOpenAI().bind_tools(self.tools, tool_choice="any")
            | PydanticToolsParser(tools=self.tools)
        )

    def run(self, question: str, callbacks: List = []) -> str | None:
        tool_calls = self.chain.invoke(
            {
                "question": question,
                "tables": self.db_description,
                "dialect": "sqlite",
            },
            config={"callbacks": callbacks},
        )

        for tool in tool_calls:
            print(tool.__class__)
            if isinstance(tool, query_database):
                tool: query_database
                return tool.query, None
            elif isinstance(tool, answer_directly):
                tool: answer_directly
                return None, tool.answer
            else:
                logger.error(
                    f"The LLM did not call on of the expected tools ({self.tools})."
                )
                return None, None


if __name__ == "__main__":
    from app.backend.prompts.etf import TABLES_DESCRIPTION
    from langchain.memory import ConversationBufferWindowMemory

    chat = QueryGenerationChain(
        db_description=TABLES_DESCRIPTION,
        memory=ConversationBufferWindowMemory(
            input_key="question",
            output_key="answer",
            return_messages=True,
            k=5,
        ),
    )

    question = "Im interested in ETFs domiciled in Ireland"

    query, answer = chat.run(question=question)
    print(query, answer)

    query, answer = chat.run(question="Ok, thank you!")
    print(query, answer)
