from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

END = date.today()
START = date.today() - timedelta(days=365)

st.set_page_config(layout="wide",
                   page_title="Stock Price Analysis")
st.title("Stock Price Analysis")

st.sidebar.title("Inputs")
ticker = st.sidebar.text_input("Enter stock ticker symbol")
col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("Start Date", START)
end_date = col2.date_input("End Date", END)
# CHANGED: one "Moving Average" slider became two, one per window
ma_short = st.sidebar.slider("Short Moving Average",
                             min_value=5,
                             max_value=200,
                             value=20)
ma_long = st.sidebar.slider("Long Moving Average",    # NEW
                            min_value=5,
                            max_value=200,
                            value=50)
run_analysis = st.sidebar.button("Run Analysis", type="primary")


def get_stock_date(ticker, start_date, end_date):
    try:
        data = yf.download(ticker, start_date, end_date)
        if data.empty:
            return None, f"No data for {ticker}"
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data, f"Successfully downloaded data {ticker}"
    except Exception as e:
        return None, f"Download failed due to {e}"


if run_analysis:
    with st.spinner("Downloading data..."):
        data, message = get_stock_date(ticker, start_date, end_date)

    if data is None:
        st.error(message)
    else:
        st.success(message)


        data['change'] = data['Close'] - data['Close'].shift(1)
        data['return'] = np.log(data['Close']).diff().round(4)
        data = data.dropna()

        data['MA_short'] = data['Close'].rolling(window=ma_short).mean()
        data['MA_long'] = data['Close'].rolling(window=ma_long).mean()   # NEW

        col1, col2, col3 = st.columns(3)
        col1.metric("Last Close", f"${data['Close'].iloc[-1]:,.2f}")
        col2.metric("Cumulative Return", f"{data['return'].sum():.2%}")
        col3.metric("Trading Days", len(data))


        fig = px.line(data,
                      y=['Close', 'MA_short', 'MA_long'],
                      title=f"{ticker} close with {ma_short}- and {ma_long}-day moving averages",
                      labels={'value': 'Price', 'variable': 'Series'})
        st.plotly_chart(fig)

        performance = data['return'].cumsum()
        fig = px.line(x=performance.index,
                      y=performance.values,
                      title=f"Performance of {ticker}",
                      labels={'x': 'Date', 'y': 'Cum Return'})
        st.plotly_chart(fig)

        fig = px.histogram(data['return'],
                           nbins=35,
                           title=f"Distribution of daily returns for {ticker}")
        st.plotly_chart(fig)

        st.dataframe(data['return'].describe())
