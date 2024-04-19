from typing import List, Mapping, Tuple
from langchain.memory import ConversationBufferMemory
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import (
    PromptTemplate,
    ChatPromptTemplate,
    AIMessagePromptTemplate,
    MessagesPlaceholder,
    HumanMessagePromptTemplate,
)
from langchain_core.runnables import (
    RunnableParallel,
    RunnablePassthrough,
    RunnableLambda,
)
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langfuse.callback import CallbackHandler
from operator import itemgetter

CONDENSE_QUESTION_PROMPT_TEMPLATE = """Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question, in its original language.

Chat History:
{history}
Follow Up Input: {question}
Standalone question:"""


class RAGChain:
    def __init__(
        self,
        retriever: BaseRetriever,
        combine_docs_func: Mapping[List[Document], str],
        langfuse_handler: CallbackHandler | None = None,
    ) -> None:
        self.retriever = retriever
        self.combine_docs_func = combine_docs_func
        self.langfuse_handler = langfuse_handler

        self.memory = ConversationBufferMemory(
            return_messages=True, output_key="answer", input_key="question"
        )
        self.chain = self._build_chain()

    def _build_chain(self):

        # ------- LOAD CHAT HISTORY INTO CHAIN -------- #

        # * -> *, history
        load_history = RunnablePassthrough.assign(
            history=RunnableLambda(self.memory.load_memory_variables)
            | itemgetter("history"),
        )

        # ------ RETRIEVE DOCS AND ADD THEM TO THE CHAIN--------- #

        # question, history -> standalone_question
        condense_question = {
            "standalone_question": PromptTemplate.from_template(
                CONDENSE_QUESTION_PROMPT_TEMPLATE
            )
            | ChatOpenAI(temperature=0)
            | StrOutputParser(),
        }

        # standalone_question -> docs
        retrieve_docs = (
            itemgetter("standalone_question") | self.retriever
        )  # when should i use lambda and when itemgetter ????

        # question, history -> question, history, docs
        retrieve_and_load_docs = RunnablePassthrough.assign(
            docs=condense_question | retrieve_docs
        )

        # ------- GENERATE FINAL ANSWER WITH SOURCES -------- #

        # docs, question, history -> context, question, history
        load_context = RunnableParallel(
            context=lambda x: self.combine_docs_func(x["docs"]),
            question=lambda x: x["question"],
            history=lambda x: x["history"],
        )

        generation_prompt = ChatPromptTemplate.from_messages(
            [
                MessagesPlaceholder("history"),
                HumanMessagePromptTemplate.from_template("{question}"),
                AIMessagePromptTemplate.from_template(
                    """I should answer the question based ONLY on the previous messages and the following context:\n{context}"""
                ),
            ]
        )

        # docs, question, history -> output
        generate_answer = load_context | generation_prompt | ChatOpenAI()

        # docs, question, history -> answer, sources
        generate_answer_and_sources = RunnableParallel(
            answer=generate_answer, sources=lambda x: x["docs"]
        )

        return load_history | retrieve_and_load_docs | generate_answer_and_sources

    def run(self, question: str) -> Tuple[str, List[Document]]:
        config = {}
        if self.langfuse_handler:
            config["callbacks"] = [self.langfuse_handler]

        result = self.chain.invoke({"question": question}, config=config)
        answer = result["answer"].content
        source_docs = result["sources"]

        self.memory.save_context({"question": question}, {"answer": answer})

        return answer, source_docs
