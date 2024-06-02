import streamlit as st
import pandas as pd
from app.web.config import UI_ROOT_URL, ANALYTICS_PAGE_PATH

DETILS_PAGE_URL = UI_ROOT_URL + ANALYTICS_PAGE_PATH

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


def display_table(ref, etf_df: pd.DataFrame, height=None):

    if len(etf_df) and DETILS_PAGE_URL not in etf_df["isin"].values[0]:
        link_isin_to_page(etf_df=etf_df)

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


def link_isin_to_page(etf_df: pd.DataFrame) -> None:
    """Make etf isin clickable with a link to the corresponding page describing the ETF"""
    link_template = DETILS_PAGE_URL + "/?isin={isin}"
    isin_urls = [link_template.format(isin=t) for t in etf_df["isin"]]
    etf_df["isin"] = isin_urls
