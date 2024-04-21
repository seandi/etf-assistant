from typing import Tuple, List
import os
import streamlit as st
from functools import partial
import sqlite3
import pandas as pd
import random
import string
from loguru import logger

from app.web.storage.docs_db import DocMetadata

from app.backend.retrievers import MultiModalChromaRetriever
from app.backend.chats.docqa import DocumentsQAChat

DETILS_PAGE_URL = os.environ["UI_ROOT_URL"] + os.environ["DETAILS_PAGE_PATH"]

EXCHANGE_COLUMNS = [
    "Borsa Italiana",
    "London",
    "Stuttgart",
    "gettex",
    "Euronext Amsterdam",
    "Euronext Paris",
    "XETRA",
    "SIX Swiss Exchange",
    "Euronext Brussels",
]
COLUMNS_DISPLAY_NAME = {
    "ticker": "Ticker",
    "currency": "Currency",
    "dividends": "Dividends",
    "replication": "Replication",
    "asset": "Asset",
    "instrument": "Instrument",
    "region": "Region",
}

WELCOME_MESSAGE_DOC_QA = """Hi, I can help you in finding information in this document. Do you have any question?"""


def get_rand_str(n: int) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def load_etf_db() -> pd.DataFrame:
    conn = sqlite3.Connection(os.environ["ETF_DB"])
    etf_data_df = pd.read_sql(f"select * from {os.environ['DISPLAY_TABLE']}", con=conn)

    return etf_data_df


def make_isin_clickable(etf_df, base_url) -> pd.DataFrame:
    """Make etf isin clickable with a link to the corresponding ETF page"""
    link_template = base_url + "/?isin={isin}"
    isin_urls = [link_template.format(isin=t) for t in etf_df["isin"]]
    etf_df["isin"] = isin_urls


def display_table(ref, etf_df, height=None):
    table_config = {
        "isin": st.column_config.LinkColumn(
            "ISIN", display_text=DETILS_PAGE_URL + "/\?isin=(.*?$)"
        ),
        "name": st.column_config.Column("Name", width="medium", required=True),
        "domicile_country": st.column_config.Column(
            "Domicile", width="medium", required=True
        ),
        "strategy": st.column_config.Column("Strategy", width="medium", required=True),
        "index": st.column_config.Column("Index", width="medium", required=True),
        "inception_date": st.column_config.DateColumn("Inception Date"),
        "size": st.column_config.NumberColumn("Fund Size", format="%d"),
        "number_of_holdings": st.column_config.NumberColumn("Holdings", format="%d"),
        "ter": st.column_config.NumberColumn("TER(%)", format="%.2f"),
        "age_in_years": st.column_config.NumberColumn(
            "Age (years)", format="%.1f", width="small"
        ),
        "hedged": st.column_config.CheckboxColumn(
            "Hedged",
        ),
        "is_sustainable": st.column_config.CheckboxColumn("Sustainable"),
        "securities_lending": st.column_config.CheckboxColumn("Securities Lending"),
    }

    for n, r in COLUMNS_DISPLAY_NAME.items():
        table_config[n] = st.column_config.Column(r)

    for c in EXCHANGE_COLUMNS:
        table_config[c] = st.column_config.CheckboxColumn(c)

    ref.dataframe(
        data=etf_df,
        column_config=table_config,
        hide_index=True,
        height=height,
        column_order=[
            "isin",
            "ticker",
            "name",
            "index",
            "size",
            "ter",
            "region",
            "instrument",
            "asset",
            "dividends",
            "currency",
            "domicile_country",
            "replication",
            "strategy",
            "number_of_holdings",
            "inception_date",
            "age_in_years",
            "is_sustainable",
            "hedged",
            "securities_lending",
        ]
        + EXCHANGE_COLUMNS,
    )


def make_searchbar(etf_df: pd.DataFrame, name: str, go_new_page: bool = True):
    search_key = "searchbar_" + name + "_isin"
    if search_key not in st.session_state:
        st.session_state[search_key] = None

    options = etf_df["name"] + " - " + etf_df["isin"]

    def on_searchbar_change():
        selection = st.session_state["searchbar_" + name]
        isin = selection.split(" - ")[1] if selection is not None else None
        st.session_state[search_key] = isin

    st.text("Search an ETF by its Name or ISIN code:")

    csearch, cgo = st.columns([0.8, 0.2])

    with csearch:
        st.selectbox(
            label="Quick search ETF by ISIN code",
            label_visibility="collapsed",
            placeholder="Search...",
            options=options,
            index=None,
            key="searchbar_" + name,
            on_change=on_searchbar_change,
        )

    with cgo:
        if go_new_page:
            st.link_button(
                url=os.environ["UI_ROOT_URL"]
                + os.environ["DETAILS_PAGE_PATH"]
                + f"/?isin={st.session_state.get(search_key, '')}",
                disabled=st.session_state[search_key] is None,
                label="Go",
                use_container_width=True,
            )
        else:
            if st.button(label="Show", use_container_width=True):
                st.query_params["isin"] = st.session_state[search_key]
                st.rerun()


def create_doc_panel(
    doc_key: str, doc: Tuple[DocMetadata, bytes], collapsed: bool = False
):
    metadata, doc_view_data = doc
    cont = st.container(
        border=True,
    )
    with cont:
        if collapsed:

            st.text(f"📄 {metadata.name}")
            st.button(
                "Chat" if st.session_state.active_doc != doc_key else "Close",
                on_click=partial(on_chat_button_click, doc_id=doc_key),
                key="view" + str(doc_key),
                use_container_width=True,
                type=(
                    "primary" if st.session_state.active_doc == doc_key else "secondary"
                ),
            )
        else:
            st.write(f"📄 {metadata.name}")
            if metadata.description is not None and metadata.description != "":
                st.write(f"{metadata.description}")
            cdownload, cchat = st.columns(2)

            cdownload.download_button(
                "Download",
                use_container_width=True,
                key="download_doc" + str(doc_key),
                data="test",
            )
            cchat.button(
                "Chat" if st.session_state.active_doc != doc_key else "Close",
                on_click=partial(on_chat_button_click, doc_id=doc_key),
                key="view" + str(doc_key),
                use_container_width=True,
            )


def on_chat_button_click(doc_id):
    prev_doc = st.session_state.active_doc

    # Close current document
    if prev_doc == doc_id:
        st.session_state.doc_view_data = None
        st.session_state.doc_view_page = 1
        st.session_state.active_doc = None
        st.session_state.chat = None
        return

    doc_metadata, doc_view_data = st.session_state.documents[doc_id]
    doc_metadata: DocMetadata

    st.session_state.doc_view_data = doc_view_data
    st.session_state.doc_view_page = 1

    st.session_state.active_doc = doc_id
    st.session_state.chat_open = True

    retriever = MultiModalChromaRetriever(
        chroma_store=os.environ["RETRIEVER_VECTORSTORE_PATH"],
        local_store=os.environ["RETRIEVER_DOCSTORE_PATH"],
        collection=os.environ["RETRIEVER_VECTORSTORE_COLLECTION"],
        top_k=doc_metadata.top_k,
        source_id=doc_metadata.vectorstore_source_id,
    )
    chat = DocumentsQAChat(
        retriever=retriever.get_retriever(),
        combine_docs_func=retriever.combine_docs,
        filter_irrelevant_sources=doc_metadata.filter_sources,
    )
    logger.info(
        f"Initialized new chat on document {retriever.source_id} uising the {retriever.top_k} most relevant chunks."
    )

    st.session_state.chat = chat

    if doc_id not in st.session_state.conversations:
        st.session_state.conversations[doc_id] = []
    st.session_state.conversations[doc_id].append(("ai", WELCOME_MESSAGE_DOC_QA))


from dataclasses import dataclass


@dataclass
class DocQAMessage:
    role: str
    message: str
    sources: List
