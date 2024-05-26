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
original_title = '<p style="font-family:sans-serif; color:#006989; font-size: 60px; text-align:center; font-weight:bold;">ETF Assistant</p>'
st.markdown(original_title, unsafe_allow_html=True)

with st.container(border=True):
    make_searchbar(etf_df, name="home")
