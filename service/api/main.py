import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()
app.mount(
    "/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static"
)


@app.get("/")
async def root():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GIF Example</title>
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
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding-top: 50px;">
            <h1>💎 Welcome 💎</h1>
            <img src="/static/chopper.gif" style="border-radius: 5px" alt="chill gif">
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
