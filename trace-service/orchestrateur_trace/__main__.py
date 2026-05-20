from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    host = os.getenv("TRACE_BIND_HOST", "127.0.0.1")
    port = int(os.getenv("TRACE_PORT", "8090"))
    uvicorn.run(
        "orchestrateur_trace.app:app",
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
