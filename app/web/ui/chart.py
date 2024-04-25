import streamlit as st
from streamlit_echarts import st_echarts

from justetf_scraping import load_chart


def display_chart(ref: st, isin: str):
    try:
        with st.spinner():
            chart_data = load_chart(isin=isin)
    except:
        st.write("Failed fetch the chart data from JustETF!")
        return

    chart_data.reset_index(inplace=True)

    data = chart_data[["date", "quote"]].values.tolist()
    data = [(str(t[0]), t[1]) for t in data]
    highest = chart_data["quote"].max()

    with ref:
        st_echarts(
            options={
                "toolbox": {
                    "feature": {
                        "restore": {},
                    }
                },
                "xAxis": {"type": "time"},
                "yAxis": {
                    "type": "value",
                    "boundaryGap": [0, "100%"],
                    "name": "Quotes",
                    # "max": int(highest * 1.2),
                },
                "series": [
                    {
                        "data": data,
                        "type": "line",
                        "symbol": "none",
                        "color": "ligthblue",
                        "areaStyle": {"color": "lightblue"},
                    }
                ],
                "dataZoom": [
                    {
                        "type": "inside",
                        "startValue": data[0][0],
                    },
                    {
                        "type": "slider",
                        "startValue": data[0][0],
                    },
                ],
            },
            height="600px",
        )
