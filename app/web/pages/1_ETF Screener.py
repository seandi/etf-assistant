import streamlit as st
from dotenv import load_dotenv
from collections import OrderedDict

from app.web.ui import display_table
from app.web.utils import load_etf_db
from app.backend.chats.search import ETFSearchChat

WELCOME_MESSAGE = """Hi, I'm your ETF Screening Assistant ready to find the right ETF(s) for your needs!\nWhat you are looking for?"""


# Init page
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")
st.markdown(
    " <style> div[class^='block-container'] { padding-top: 2rem; } </style> ",
    unsafe_allow_html=True,
)
load_dotenv(override=True)

if "search_chat" not in st.session_state:
    st.session_state.search_chat = ETFSearchChat()
    st.session_state.search_chat_history = [("ai", WELCOME_MESSAGE)]
    st.session_state.tables_history = OrderedDict()
    st.session_state.saved_filters = {}


# UI
st.title("ETF Smart Screener")

ctable, cchat = st.columns([0.7, 0.3])

with ctable:
    all_tab, results_tab = st.tabs(["All ETFs", "ETFs selected by the Assistant"])

    display_table(ref=all_tab, etf_df=load_etf_db(), height=700)

    with results_tab:

        n_tables = len(st.session_state.tables_history)

        if n_tables == 0:
            st.info(
                "The ETFs selected by the assistant will be shown here! You can start by describing in the chat what you are looking for."
            )
        else:
            cselection, cadd = st.columns([0.8, 0.2])
            question = cselection.selectbox(
                label="Results",
                label_visibility="collapsed",
                options=list(st.session_state.tables_history.keys()),
                index=n_tables - 1,
            )
            add_button = cadd.button(
                label="Add",
                use_container_width=True,
                disabled=n_tables == 0,
                type="primary",
            )
            if add_button:
                st.session_state.saved_filters[question] = (
                    st.session_state.tables_history[question]
                )

            display_table(
                ref=st, etf_df=st.session_state.tables_history[question], height=500
            )

with cchat:
    messages_container = st.container(border=True, height=700)
    col_input, col_reset = st.columns([0.8, 0.2])
    question = col_input.chat_input()
    reset_button = col_reset.button(
        "Reset",
        use_container_width=True,
        type="primary",
        help="Reset the conversation",
    )


# Page Logic
for message in st.session_state.search_chat_history:
    messages_container.chat_message(name=message[0]).write(message[1])

if question:
    st.session_state.search_chat_history.append(("user", question))
    messages_container.chat_message(name="user").write(question)

    chat: ETFSearchChat = st.session_state.search_chat
    answer, etfs_filtered_df = chat.chat(question=question)

    st.session_state.search_chat_history.append(("ai", answer))
    if etfs_filtered_df is not None and len(etfs_filtered_df):
        st.session_state.tables_history[question] = etfs_filtered_df

    messages_container.chat_message(name="ai").write(answer)
    st.rerun()

if reset_button:
    st.session_state.search_chat = ETFSearchChat()
    st.session_state.search_chat_history = [("ai", WELCOME_MESSAGE)]
    st.session_state.tables_history = OrderedDict()
    st.rerun()
