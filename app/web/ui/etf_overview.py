import streamlit as st
from datetime import datetime
import pandas as pd


def display_overview_table(ref: st, etf_data: pd.Series):
    properties_mapping = {
        "name": "Name",
        "index": "Index",
        "size": "Fund Size",
        "ter": "TER",
        "region": "Geographical region",
        "instrument": "Instrument",
        "asset": "Asset",
        "dividends": "Dividends",
        "currency": "Currency",
        "domicile_country": "Domicile",
        "replication": "Replication Method",
        "strategy": "Strategy",
        "number_of_holdings": "Holdings",
        "inception_date": "Inception Date",
    }
    properties_display, values = [], []
    for k, v in properties_mapping.items():
        properties_display.append(v)

        if k == "ter":
            values.append(f"{etf_data[k]}%")
        elif k == "size":
            values.append(f"{etf_data[k]:,.0f} Milions")
        elif k == "number_of_holdings":
            values.append(f"{etf_data[k]:.0f}")
        elif k == "inception_date":
            d = datetime.strptime(etf_data[k], "%Y-%m-%d %H:%M:%S")
            values.append(f"{d.strftime('%B %d, %Y')}")
        else:
            values.append(f"{etf_data[k]}")

    ref.text("")  # padding
    ref.dataframe(
        pd.DataFrame({"Property": properties_display, "Value": values}),
        column_config={
            "Property": st.column_config.Column(width="small"),
            "Value": st.column_config.Column(width="medium"),
        },
        hide_index=True,
        use_container_width=True,
        height=527,
    )
