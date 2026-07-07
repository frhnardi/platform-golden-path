"""A minimal FastAPI service wired to the golden path.

Exposes two endpoints:

    GET /healthz  liveness/readiness probe (used by Kubernetes)
    GET /hello    demo endpoint; optional ?name= query parameter

Keep this file small: the point of the template is the paved road around it
(CI, scanning, signing, GitOps), not the business logic.
"""

import os

import uvicorn
from fastapi import FastAPI, Query

app = FastAPI()


@app.get("/healthz")
async def healthz():
    """Liveness probe. Deliberately dependency-free."""
    return {"status": "ok"}


@app.get("/hello")
async def hello(name: str = Query(default="world")):
    """Demo endpoint. Greets the caller; the name defaults to 'world'."""
    return {"message": f"hello, {name}"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
