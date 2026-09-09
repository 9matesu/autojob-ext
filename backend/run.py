"""Run the resuMe FastAPI server."""
import os

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("RESUME_PORT", "8322"))
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False, log_level="info")
