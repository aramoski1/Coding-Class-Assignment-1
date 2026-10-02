
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from stock import Stock

END = date.today()
START = END - timedelta(days=365)

st.set_page_config(layout="wide", page_title="Stock Analysis")
st.title("Stock Analysis")




@st.cache_data(show_spinner=False, ttl=3600)
def load_stock(ticker, start, end, ma_window, ma_long_window):
    """Creating a Stock IS the data fetch, so this is the one place a download happens.
    Cached on its arguments: the same ticker/dates/windows are not downloaded twice."""
    return Stock(ticker, start, end, ma_window, ma_long_window)


def zero_based_cum_return(stock):
    """Cumulative log return that starts at exactly 0.0 on the first day in stock.data."""
    returns = stock.data['return'].copy()
    returns.iloc[0] = 0.0  # the first day is the starting point, so it has no return yet
    return returns.cumsum()


def parse_tickers(text):
    """'aapl, msft,, goog' -> ['AAPL', 'MSFT', 'GOOG'] (no blanks, no duplicates)."""
    tickers = [t.strip().upper() for t in text.split(",") if t.strip()]
    return list(dict.fromkeys(tickers))




st.sidebar.title("Inputs")
ticker = st.sidebar.text_input("Ticker symbol", "AAPL")
col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("Start date", START)
end_date = col2.date_input("End date", END)
ma_short = st.sidebar.slider("Short moving average (days)",
                             min_value=5, max_value=200, value=20)
ma_long = st.sidebar.slider("Long moving average (days)",
                            min_value=5, max_value=200, value=50)
run_analysis = st.sidebar.button("Run Analysis", type="primary")


if run_analysis:
    st.session_state["single"] = {"ticker": ticker.strip().upper(),
                                  "start": start_date,
                                  "end": end_date,
                                  "ma_short": ma_short,
                                  "ma_long": ma_long}

tab1, tab2 = st.tabs(["Single Stock Analysis", "Portfolio Comparison"])




def show_single_stock(stock):
    data = stock.data


    last = data.iloc[-1]
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Last Close", f"${last['Close']:,.2f}", f"{last['change']:+,.2f}")
    m2.metric("Cumulative Return", f"{data['return'].sum():.2%}")
    m3.metric("Trading Days", len(data))
    m4.metric("Daily Volatility", f"{data['return'].std():.2%}")


    short_label = f"MA {stock.ma_window}"
    long_label = f"MA {stock.ma_long_window}"
    price = data[['Close', 'MA', 'MA_long']].rename(
        columns={'MA': short_label, 'MA_long': long_label})
    fig = px.line(price,
                  y=['Close', short_label, long_label],
                  title=f"{stock.symbol} close with {short_label} and {long_label}",
                  labels={'value': 'Price ($)', 'variable': 'Series',
                          'Date': 'Date', 'index': 'Date'})
    fig.update_layout(hovermode='x unified')
    st.plotly_chart(fig)


    for window in (stock.ma_window, stock.ma_long_window):
        if window > len(data):
            st.warning(f"Only {len(data)} trading days in this range, but MA {window} "
                       f"needs at least {window}, so that line is empty. "
                       f"Pick an earlier start date or a smaller window.")
    st.caption(f"Each moving average needs a full window of prices, so {short_label} "
               f"starts on trading day {stock.ma_window} and {long_label} on "
               f"trading day {stock.ma_long_window}.")


    left, right = st.columns(2)
    left.plotly_chart(stock.plot_performance())
    right.plotly_chart(stock.plot_return_dist())


    st.subheader("Daily return statistics")
    st.dataframe(data['return'].describe().to_frame("Daily log return"))


with tab1:
    params = st.session_state.get("single")
    if params is None:
        st.info("Enter a ticker in the sidebar and click **Run Analysis**.")
    elif not params["ticker"]:
        st.warning("Enter a ticker symbol in the sidebar.")
    elif params["start"] >= params["end"]:
        st.error("The start date must be before the end date.")
    elif params["ma_short"] >= params["ma_long"]:
        st.error("The short moving average must be smaller than the long one.")
    else:
        with st.spinner(f"Fetching {params['ticker']}..."):
            stock = load_stock(params["ticker"], params["start"], params["end"],
                               params["ma_short"], params["ma_long"])
        if stock.data is None:
            st.error(stock.message)
        else:
            st.success(stock.message)
            show_single_stock(stock)




with tab2:
    tickers_text = st.text_input("Ticker symbols (comma-separated)", "AAPL, MSFT, GOOG")
    compare = st.button("Compare", type="primary")
    st.caption("Uses the start and end dates from the sidebar.")

    if compare:
        st.session_state["portfolio"] = {"tickers": parse_tickers(tickers_text),
                                         "start": start_date,
                                         "end": end_date}

    portfolio = st.session_state.get("portfolio")
    if portfolio is None:
        st.info("Enter two or more tickers and click **Compare**.")
    elif not portfolio["tickers"]:
        st.warning("Enter at least one ticker symbol.")
    elif portfolio["start"] >= portfolio["end"]:
        st.error("The start date must be before the end date.")
    else:
        lines = {}
        returns = {}
        with st.spinner("Fetching portfolio data..."):
            for symbol in portfolio["tickers"]:

                stock = load_stock(symbol, portfolio["start"], portfolio["end"], 20, 50)
                if stock.data is None:
                    st.error(stock.message)
                    continue
                lines[symbol] = zero_based_cum_return(stock)
                returns[symbol] = stock.data['return']

        if not lines:
            st.warning("None of the tickers returned data.")
        else:
            cumulative = pd.DataFrame(lines)
            fig = px.line(cumulative,
                          y=list(cumulative.columns),
                          title="Cumulative performance (each line starts at 0)",
                          labels={'value': 'Cumulative return', 'variable': 'Ticker',
                                  'Date': 'Date', 'index': 'Date'})
            fig.add_hline(y=0, line_dash='dash', line_color='black', opacity=0.7)
            fig.update_layout(yaxis_tickformat='.1%', hovermode='x unified')
            st.plotly_chart(fig)

            with st.expander("Data behind the chart"):
                st.write("Cumulative return (the first row should be 0.0 for every ticker)")
                st.dataframe(cumulative)
                st.write("Daily log returns")
                st.dataframe(pd.DataFrame(returns))
