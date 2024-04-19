import os
import streamlit as st
from dotenv import load_dotenv
from functools import partial
from collections import OrderedDict
import pandas as pd

from app.web.utils import (
    load_etf_db,
    make_isin_clickable,
    DETILS_PAGE_URL,
    display_table,
)
from app.backend.chats.search import ETFSearchChat

WELCOME_MESSAGE = """Hi, I'm here to assist you in finding the right ETF for your needs!\nYou can start by describing what you are looking for"""


st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
load_dotenv(override=True)


if "search_chat" not in st.session_state:
    st.session_state.search_chat = ETFSearchChat()
    st.session_state.search_chat_history = [("ai", WELCOME_MESSAGE)]
    st.session_state.tables_history = OrderedDict()
    st.session_state.saved_filters = {}


etf_df = load_etf_db()
make_isin_clickable(etf_df, base_url=DETILS_PAGE_URL)


st.title("AI augmented ETF browser")


ctable, cchat = st.columns([0.75, 0.25])

with ctable:
    all_tab, results_tab = st.tabs(["Browse all ETFs", "ETF Selection Assistant"])

    with all_tab:
        display_table(ref=all_tab, etf_df=etf_df, height=600)

    with results_tab:

        def on_add_click(question):
            st.session_state.saved_filters[question] = st.session_state.tables_history[
                question
            ]

        n_tables = len(st.session_state.tables_history)

        cselection, cadd = st.columns([0.8, 0.2])
        question = cselection.selectbox(
            label="Results",
            label_visibility="collapsed",
            options=list(st.session_state.tables_history.keys()),
            index=n_tables - 1,
        )
        cadd.button(
            label="Add",
            use_container_width=True,
            disabled=n_tables == 0,
            on_click=partial(on_add_click, question=question),
        )

        if n_tables == 0:
            st.info("The ETFs selected by the assistant will be shown here!")
        else:
            display_table(ref=st, etf_df=st.session_state.tables_history[question])


with cchat:
    reset_button = st.button("Restart conversation", use_container_width=True)
    messages_container = st.container(border=True, height=650)
    question = st.chat_input()

    for message in st.session_state.search_chat_history:
        messages_container.chat_message(name=message[0]).write(message[1])

    if question:
        st.session_state.search_chat_history.append(("user", question))
        messages_container.chat_message(name="user").write(question)

        chat: ETFSearchChat = st.session_state.search_chat
        answer, etfs_filtered_df = chat.chat(question=question)
        make_isin_clickable(etfs_filtered_df, base_url=DETILS_PAGE_URL)

        st.session_state.search_chat_history.append(("ai", answer))
        st.session_state.tables_history[question] = etfs_filtered_df

        print(etfs_filtered_df["ticker"])
        print(st.session_state.tables_history[question]["ticker"])

        messages_container.chat_message(name="ai").write(answer)
        st.rerun()

    if reset_button:
        st.session_state.search_chat = ETFSearchChat()
        st.session_state.search_chat_history = [("ai", WELCOME_MESSAGE)]
        st.session_state.tables_history = OrderedDict()
        st.rerun()