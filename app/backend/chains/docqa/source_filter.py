from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers.boolean import BooleanOutputParser
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langfuse.callback import CallbackHandler

SOURCE_FILTER_PROMPT_TEMPLATE = """Given a question, the generated answer and a source document, return YES if information from the source document is useful for answering the question and NO if it isn't.

> Question:
>>
{question}
<<

> Answer:
>>
{answer}
<<

> Source document:
>>
{source}
<<

Relevant (YES/NO):"""


class SourceFilterChain:
    def __init__(
        self,
        langfuse_handler: CallbackHandler | None = None,
    ) -> None:

        self.langfuse_handler = langfuse_handler

        self.chain = (
            ChatPromptTemplate.from_template(SOURCE_FILTER_PROMPT_TEMPLATE)
            | ChatOpenAI(temperature=0)
            | BooleanOutputParser()
        )

    def run(
        self,
        question: str,
        answer: str,
        source_doc: Document,
    ) -> bool:
        config = {}
        if self.langfuse_handler:
            config["callbacks"] = [self.langfuse_handler]

        res = self.chain.invoke(
            {
                "question": question,
                "answer": answer,
                "source": source_doc.page_content,
            },
            config=config,
        )

        # print(res)
        return res
