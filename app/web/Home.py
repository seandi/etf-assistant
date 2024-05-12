import streamlit as st
from dotenv import load_dotenv
import os

from app.web.utils import load_etf_db
from app.web.ui import make_searchbar


st.set_page_config(layout="centered")

load_dotenv(override=True)
with st.spinner():
    etf_df = load_etf_db()


# Init session


# UI layout
st.title("ETF Assistant")
make_searchbar(etf_df, name="home")
