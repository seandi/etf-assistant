from typing import List, Tuple, Dict
from langfuse.callback import CallbackHandler
from loguru import logger

from app.backend.chains.docqa import RAGChain, SourceFilterChain
from app.backend.retrievers import MultiModalChromaRetriever, ChromaRetriever


class DocumentsQAChat:

    def __init__(
        self,
        retriever: ChromaRetriever | MultiModalChromaRetriever,
        combine_docs_func,
        filter_irrelevant_sources: bool = False,
        langfuse_handler: CallbackHandler | None = None,
    ) -> None:

        self.filter_sources = filter_irrelevant_sources

        self.retriever = retriever
        self.rag_chain = RAGChain(
            retriever=self.retriever,
            combine_docs_func=combine_docs_func,
            langfuse_handler=langfuse_handler,
        )

        if self.filter_sources:
            self.source_filter_chain = SourceFilterChain(
                langfuse_handler=langfuse_handler
            )

    def chat(self, question: str) -> Tuple[str, Dict[str, List[str]]]:
        answer, sources = self.rag_chain.run(question=question)

        if self.filter_sources:
            useful_sources = []
            for source in sources:
                if self.source_filter_chain.run(
                    question=question, answer=answer, source_doc=source
                ):
                    useful_sources.append(source)

            if len(useful_sources) == 0:
                useful_sources.append(sources[0])

            logger.info(
                f"Found {len(useful_sources)} out of {len(sources)} chunks to be relevant."
            )
            sources = useful_sources

        sources_pages = {}
        sources_id = list(set([doc.metadata["source_id"] for doc in sources]))
        for s in sources_id:
            sources_pages[s] = list(
                set(
                    [
                        doc.metadata["page"]
                        for doc in sources
                        if doc.metadata["source_id"] == s
                    ]
                )
            )

        return answer, sources_pages
