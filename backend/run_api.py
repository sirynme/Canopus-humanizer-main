"""FastAPI application launcher."""

import os
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
src_dir = backend_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from canopus_humanizer.api.routes import router as api_router
from canopus_humanizer.config import GLOBAL_CONFIG

app = FastAPI(
    title="canopus-humanizer API",
    description="Text humanization API",
    version=GLOBAL_CONFIG.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


# Serve frontend UI directly from docs/
docs_dir = backend_dir.parent / "docs"
if docs_dir.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=str(docs_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("API_PORT", 8080))
    print(f"\n========================================================")
    print(f"  Frontend UI:  http://localhost:{port}")
    print(f"  API Docs:     http://localhost:{port}/docs")
    print(f"========================================================\n")
    uvicorn.run("run_api:app", host="0.0.0.0", port=port, reload=False, app_dir=str(backend_dir))
