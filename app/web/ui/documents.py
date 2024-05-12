import streamlit as st
import base64
from typing import Tuple, List
import os
from loguru import logger
from fitz import Document
import math

from app.web.storage.docs_db import DocMetadata
from app.web.utils import create_docqa_chat


WELCOME_MESSAGE_DOC_QA = """Hi, I can help you in finding information in this document. Do you have any question?"""


def display_doc_view(ref: st, doc_view_data):
    """"""
    doc_base64_prop = base64.b64encode(doc_view_data).decode("utf-8")
    pdf_display = f'<iframe src="data:application/pdf;base64,{doc_base64_prop}" width=100% height="700" type="application/pdf"></iframe>'
    ref.markdown(pdf_display, unsafe_allow_html=True)


def display_doc_panel(doc: Tuple[DocMetadata, bytes], collapsed: bool = False):
    metadata, doc_data = doc
    doc_id = metadata.id

    cont = st.container(
        border=True,
    )
    with cont:
        st.write(f"#### 📄 {metadata.name}")
        if metadata.description is not None and metadata.description != "":
            st.write(f"{metadata.description}")

        if collapsed:
            cchat = st.empty()
            cdownload = st.empty()
        else:
            cchat, cdownload = st.columns(2)

        chat_button = cchat.button(
            "Chat" if st.session_state.active_doc != doc_id else "Close",
            key="view" + str(doc_id),
            use_container_width=True,
            type="primary",
        )

        cdownload.download_button(
            "Download",
            use_container_width=True,
            key="download_doc" + str(doc_id),
            file_name=f"{metadata.name}.pdf",
            data=doc_data,
        )

        if chat_button:
            # Close current document
            if st.session_state.active_doc == doc_id:
                st.session_state.doc_view_data = None
                st.session_state.active_doc = None
            else:
                st.session_state.active_doc = doc_id
                st.session_state.doc_view_data = split_document(
                    doc_data=doc_data, max_size=int(os.environ["DOC_VIEW_MAX_SIZE"])
                )

                if doc_id not in st.session_state.conversations:
                    st.session_state.chats[doc_id] = create_docqa_chat(
                        doc_metadata=metadata
                    )
                    st.session_state.conversations[doc_id] = []
                    st.session_state.conversations[doc_id].append(
                        ("ai", WELCOME_MESSAGE_DOC_QA)
                    )

            st.rerun()


def split_document(doc_data: bytes, max_size: int) -> List[bytes]:
    """
    Split the input document into smaller chunks such that each chunk contains at most max_size bytes.
    """
    doc_view_chunks = []

    original_doc = Document("pdf", doc_data)
    n_chunks = math.ceil(len(doc_data) / max_size)
    pages_per_chunk = original_doc.page_count // n_chunks
    for page_start in range(0, original_doc.page_count, pages_per_chunk):
        doc_chunk = Document()
        doc_chunk.insert_pdf(
            original_doc,
            from_page=page_start,
            to_page=min(page_start + pages_per_chunk, original_doc.page_count),
        )
        doc_view_chunks.append(doc_chunk.write())

    return doc_view_chunks
