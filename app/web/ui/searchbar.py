import streamlit as st
import pandas as pd
import os



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

