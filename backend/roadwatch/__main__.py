from __future__ import annotations

import os

import uvicorn


if __name__ == "__main__":
    host = "0.0.0.0" if os.getenv("ROADWATCH_ALLOW_LAN", "0") == "1" else "127.0.0.1"
    uvicorn.run("roadwatch.api:app", host=host, port=8000, reload=False)

