import os
import io
import json

import pandas as pd
import yfinance as yf
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Response, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

matplotlib.use("Agg")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=f"{BASE_DIR}/templates")

# Default cookie values
DEFAULT_STATE = {"stocks": ["MSFT"], "period": "1y", "scale": "log"}

app = FastAPI()
app.mount(
    "/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static"
)


@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    state = get_state_from_cookie(request)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "stocks": state["stocks"],
            "period": state["period"],
            "scale": state["scale"],
        },
    )


@app.get("/welcome", response_class=HTMLResponse)
async def root():

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hello</title>
        <style>

            @font-face {
                font-family: 'Caveat';
                src: url('/static/Caveat/static/Caveat-Bold.ttf') format('truetype');
                font-weight: bold;
                font-style: normal;
            }

            body {
                padding: 0;
                margin: 0;
                background-color: black;
                font-family: 'Caveat', cursive;
                color: white;
            }
        </style>
    </head>
    <body>
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding-top: 150px;">
            <h1> Welcome </h1>
            <img src="/static/chopper.gif" style="border-radius: 5px" alt="chill gif">
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


def save_state_in_cookie(response: Response, state: dict):
    """Save state as cookie."""
    response.set_cookie(
        key="stock_state",
        value=json.dumps(state),
        httponly=True,
        samesite="lax",
    )


def _get_stock_data(ticker: str, period: str, interval: str):
    # Download stock data
    data = yf.download(ticker, period=period, interval=interval, progress=False)
    if data.empty:
        return None, None, None  # Indicate no data

    df = data.copy()
    df.index = pd.to_datetime(df.index)

    # x-axis: days since start
    x = (df.index - df.index[0]).days.values.astype(float)
    y = df["Close"].values

    return df, x, y


INTERVAL_DESCR = """
Data interval options:
<ul>
<li>1m  1 minute</li>
<li>2m  2 minutes</li>
<li>5m  5 minutes</li>
<li>15m 15 minutes</li>
<li>30m 30 minutes</li>
<li>60m 60 minutes</li>
<li>90m 90 minutes</li>
<li>1h  1 hour</li>
<li>1d  1 day</li>
<li>5d  5 days</li>
<li>1wk 1 week</li>
<li>1mo 1 month</li>
<li>3mo 3 months</li>
</ul>
"""


@app.get("/trend/{ticker}")
async def get_trend(  # pylint: disable=R0914
    ticker: str,
    period: str = "7d",
    interval: str = Query("1d", description=INTERVAL_DESCR),
    scale: str = "linear",  # <-- now "linear" or "log"
):
    # Download stock data
    df, x, y = _get_stock_data(ticker, period, interval)
    if df is None:
        return Response(content=b"No data available", media_type="text/plain")

    # Least-squares fit on log-price
    y_log = np.log(y)
    slope_ls, intercept_ls = np.polyfit(x, y_log, 1)
    trend_ls = np.exp(intercept_ls + slope_ls * x)  # back to price space

    # steady growth rate
    ## fix shape
    y = df["Close"].to_numpy(dtype=float).reshape(-1)

    x0, x1 = x[0], x[-1]
    y0 = y[0]

    # Total area under actual curve
    area_actual = np.trapezoid(y, x)

    # The straight line: y_line = y0 + m * (x - x0)
    # Its area = ∫(y0 + m*(x - x0)) dx from x0 to x1
    #          = y0*(x1 - x0) + m * (x1 - x0)^2 / 2
    # Solve for slope m such that area_line = area_actual
    m = (2 * (area_actual - y0 * (x1 - x0))) / ((x1 - x0) ** 2)

    avg_growth = y0 + m * (x - x0)

    fig, ax = plt.subplots(figsize=(20, 12))
    ax.plot(df.index, y, label=f"{ticker}", color="red")
    ax.plot(df.index, avg_growth, linestyle="--", color="green", label="Average Growth")
    ax.plot(df.index, trend_ls, linestyle="--", color="blue", label="Trend")

    # Apply y-axis scale
    if scale == "log":
        ax.set_yscale("log", base=2)
        ax.set_ylabel("Price (log scale)")
    else:
        ax.set_yscale("linear")
        ax.set_ylabel("Price")

    # Format y-axis ticks to show actual values
    ax.yaxis.set_major_formatter(mticker.ScalarFormatter())
    ax.yaxis.set_minor_formatter(mticker.NullFormatter())

    ax.set_title(f"{ticker} Stock Price with Trend")
    ax.set_xlabel("Date")
    ax.legend()
    ax.grid(True, which="major", ls="--", alpha=0.7)

    # Save to memory
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    return Response(content=buf.getvalue(), media_type="image/png")


def get_state_from_cookie(request: Request):
    cookie = request.cookies.get("stock_state")
    if cookie:
        try:
            return json.loads(cookie)
        except json.JSONDecodeError:
            pass
    # defaults
    return {"stocks": [], "period": "6mo", "scale": "linear", "interval": "1d"}


@app.post("/add")
async def add_stock(request: Request, ticker: str = Form(...)):
    state = get_state_from_cookie(request)
    ticker = ticker.upper()
    if ticker not in state["stocks"]:
        state["stocks"].append(ticker)

    response = RedirectResponse(url="/", status_code=303)
    save_state_in_cookie(response, state)
    return response


@app.post("/remove")
async def remove_stock(request: Request, ticker: str = Form(...)):
    state = get_state_from_cookie(request)
    ticker = ticker.upper()
    if ticker in state["stocks"]:
        state["stocks"].remove(ticker)

    response = RedirectResponse(url="/", status_code=303)
    save_state_in_cookie(response, state)
    return response


@app.post("/set_options")
async def set_options(
    request: Request, period: str = Form(...), scale: str = Form(...)
):
    state = get_state_from_cookie(request)
    state["period"] = period
    state["scale"] = scale

    response = RedirectResponse(url="/", status_code=303)
    save_state_in_cookie(response, state)
    return response
