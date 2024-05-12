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
                "tooltip": {
                    "trigger": "axis",
                },
                "xAxis": {"type": "time"},
                "yAxis": {
                    "type": "value",
                    "boundaryGap": ["20%", "10%"],
                    "scale": True,
                    "name": "Quotes",
                    "nameLocation": "center",
                    "nameGap": 30,
                    # "max": int(highest * 1.2),
                },
                "series": [
                    {
                        "name": "Quote",
                        "sampling": "lttb",
                        "data": data,
                        "type": "line",
                        "symbol": "none",
                        "color": st._config.get_option("theme.primaryColor"),
                        "areaStyle": {
                            "color": st._config.get_option(
                                "theme.secondaryBackgroundColor"
                            )
                        },
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
