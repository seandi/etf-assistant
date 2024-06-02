import streamlit as st
from dotenv import load_dotenv

from app.web.storage.docs_storage import ETFDocStorage
from app.web.utils import load_etf_db, create_docqa_chat
from app.web.ui import (
    display_chart,
    make_searchbar,
    display_overview_table,
    display_doc_panel,
    display_doc_view,
)
from app.web.ui.documents import WELCOME_MESSAGE_DOC_QA

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.markdown(
    " <style> div[class^='block-container'] { padding-top: 2rem; } </style> ",
    unsafe_allow_html=True,
)

load_dotenv(override=True)
etf_df = load_etf_db()

ctitle, csearch = st.columns([0.65, 0.35])

with csearch:
    make_searchbar(etf_df=etf_df, name="details", go_new_page=False)

if "isin" not in st.query_params:
    with ctitle:
        st.write("# No ETF have been selected yet!")
    st.stop()


# INITIALIZE SESSION
etf_doc_storage = ETFDocStorage()
etf_data = etf_df[etf_df["isin"] == st.query_params["isin"]].iloc[0]
etf_name = etf_data["name"]
etf_isin = st.query_params["isin"]
docs = etf_doc_storage.get_documents(etf_isin=etf_isin)

# Controls which document is currently in use for chat/view (if any)
if "active_doc" not in st.session_state:
    st.session_state.active_doc = None

# Holds the doc data of the currently active doc for the viewer to display
if "doc_view_data" not in st.session_state:
    st.session_state.doc_view_data = None

# Holds the Chats object for documents
if "chats" not in st.session_state:
    st.session_state.chats = {}

# Stores the conversations for all documents that have one
if "conversations" not in st.session_state:
    st.session_state.conversations = {}


# BUILD PAGE LAYOUT
with ctitle:
    st.write(f"# {etf_name}")
    st.write(
        f"**ISIN**: {etf_data['isin']} &emsp;&emsp;&emsp; **Ticker**: {etf_data['ticker']}"
    )

overview_tab, documents_tab = st.tabs(["Overview", "Documentation"])

with overview_tab:
    ctable, cchart = st.columns([0.3, 0.7])
    display_overview_table(ref=ctable, etf_data=etf_data)
    display_chart(ref=cchart, isin=etf_isin)


with documents_tab:
    if st.session_state.active_doc is None:
        _, rdocs, _ = st.columns([0.35, 0.3, 0.35])
    else:
        rdocs, rview, rchat = st.columns([0.15, 0.55, 0.3])
        view_page_selector = rdocs.empty()

    with rdocs:
        if docs:
            for doc in docs:
                display_doc_panel(
                    doc=doc, collapsed=st.session_state.active_doc is not None
                )
        else:
            st.write("No documents were found for this ETF!")

    if st.session_state.active_doc is None:
        question, messages_container, reset_button = None, None, None
    else:
        if len(st.session_state["doc_view_data"]) > 1:
            with view_page_selector.container(border=True):
                doc_view_page = st.slider(
                    label="Document view",
                    min_value=1,
                    max_value=len(st.session_state["doc_view_data"]),
                )
        else:
            doc_view_page = 1

        with rview:
            view_controller = st.container()
            doc_view = st.empty()

        display_doc_view(
            ref=doc_view,
            doc_view_data=st.session_state["doc_view_data"][doc_view_page - 1],
        )

        with rchat:
            messages_container = st.container(border=True, height=650)
            col_input, col_reset = st.columns([0.8, 0.2])
            question = col_input.chat_input()
            reset_button = col_reset.button(
                "Reset",
                use_container_width=True,
                type="primary",
                help="Reset the conversation",
            )


# CHAT LOGIC
for message in st.session_state.conversations.get(st.session_state.active_doc, []):
    messages_container.chat_message(name=message[0]).write(message[1])

if st.session_state.active_doc and question:
    active_doc_id = st.session_state.active_doc

    st.session_state.conversations[active_doc_id].append(("user", question))
    messages_container.chat_message(name="user").write(question)

    answer, sources = st.session_state.chats[active_doc_id].chat(question=question)

    st.session_state.conversations[active_doc_id].append(("ai", answer))
    messages_container.chat_message(name="ai").write(answer)

if reset_button:
    active_doc_id = st.session_state.active_doc

    for doc in docs:
        if doc[0].id == active_doc_id:
            active_doc_metadata = doc[0]
            break
    st.session_state.chats[active_doc_id] = create_docqa_chat(
        doc_metadata=active_doc_metadata
    )
    st.session_state.conversations[active_doc_id] = []
    st.session_state.conversations[active_doc_id].append(("ai", WELCOME_MESSAGE_DOC_QA))
    st.rerun()
