from typing import Dict, List, Tuple
import streamlit as st
from dotenv import load_dotenv
import base64

from app.web.storage.docs_storage import ETFDocStorage
from app.web.utils import (
    create_doc_panel,
    load_etf_db,
    make_searchbar,
)
from app.web.ui.chart import display_chart
from app.backend.chats.docqa import DocumentsQAChat

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

# Handle Missing ISIN
load_dotenv(override=True)
etf_df = load_etf_db()

ctitle, csearch = st.columns([0.7, 0.3])

with csearch:
    make_searchbar(etf_df=etf_df, name="details", go_new_page=False)

if "isin" not in st.query_params:
    with ctitle:
        st.title("No ETF appears to have been selected yet...")
    st.stop()


# INITIALIZE SESSION
etf_doc_storage = ETFDocStorage()
etf_name = etf_df[etf_df["isin"] == st.query_params["isin"]]["name"].values[0]


if "documents" not in st.session_state:
    docs = etf_doc_storage.get_documents(
        etf_isin=st.query_params["isin"], doc_max_size=1024**2
    )
    st.session_state.documents = {doc[0].id: doc for doc in docs}

# Controls which document is currently in use for chat/view (if any)
if "active_doc" not in st.session_state:
    st.session_state.active_doc = None

# Holds the doc data of the currently active doc for the viewer to display
if "doc_view_data" not in st.session_state:
    st.session_state.doc_view_data = None
    st.session_state.doc_view_page = 1

# Holds the Chat object for the active document
if "chat" not in st.session_state:
    st.session_state.chat = None

# Stores the conversations for all documents that have one
if "conversations" not in st.session_state:
    st.session_state.conversations = {}


# BUILD PAGE LAYOUT
with ctitle:
    st.title(etf_name)


overview_tab, performance_tab, documents_tab = st.tabs(
    ["Overview", "Performance Chart", "Documentation"]
)

with overview_tab:
    st.dataframe(etf_df[etf_df["isin"] == st.query_params["isin"]])

with performance_tab:
    display_chart(isin=st.query_params["isin"])


with documents_tab:
    if st.session_state.active_doc is None:
        _, rdocs, _ = st.columns([0.35, 0.3, 0.35])
    else:
        rdocs, rview, rchat = st.columns([0.15, 0.55, 0.3])

    with rdocs:
        st.container()

        docs = st.session_state["documents"]

        if docs:
            for doc_id, doc in docs.items():
                create_doc_panel(
                    doc_key=doc_id,
                    doc=doc,
                    collapsed=st.session_state.active_doc is not None,
                )
        else:
            st.write("No documents were found for this ETF!")

    if st.session_state.active_doc is not None:
        with rview:
            view_controller = st.container()
            doc_view = st.empty()

        doc_view_data = st.session_state["doc_view_data"]
        if len(doc_view_data) > 1:
            with view_controller:
                c1, c2 = st.columns([0.65, 0.35])
                c1.warning(
                    "Document is too large to be loaded entirely, it has been split in multiple views!",
                )

                view_slider = c2.slider(
                    label="Document view",
                    min_value=1,
                    max_value=len(doc_view_data),
                    value=st.session_state.doc_view_page,
                )
                if view_slider != st.session_state.doc_view_page:
                    st.session_state.doc_view_page = view_slider

                    st.rerun()

        doc_base64_prop = base64.b64encode(
            doc_view_data[st.session_state.doc_view_page - 1]
        ).decode("utf-8")
        pdf_display = f'<iframe src="data:application/pdf;base64,{doc_base64_prop}" width=100% height="700" type="application/pdf"></iframe>'
        doc_view.markdown(pdf_display, unsafe_allow_html=True)

        with rchat:
            chat: DocumentsQAChat = st.session_state.chat
            reset_button = st.button("Restart conversation", use_container_width=True)
            messages_container = st.container(border=True, height=600)
            question = st.chat_input()

            for message in st.session_state.conversations.get(
                st.session_state.active_doc, []
            ):
                messages_container.chat_message(name=message[0]).write(message[1])

            if question:

                doc_id = st.session_state.active_doc
                if doc_id not in st.session_state.conversations:
                    st.session_state.conversations[doc_id] = []
                st.session_state.conversations[doc_id].append(("user", question))

                messages_container.chat_message(name="user").write(question)

                # answer = "answer"
                answer, sources = chat.chat(question=question)
                print(sources)
                st.session_state.conversations[doc_id].append(("ai", answer))
                messages_container.chat_message(name="ai").write(answer)

            if reset_button:
                st.session_state.conversations[st.session_state.active_doc] = []
                st.rerun()
