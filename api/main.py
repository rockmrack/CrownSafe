"""Main entry point for Docker - imports main_crownsafe."""

from api.main_crownsafe import app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
