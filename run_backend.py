"""Entry point to start the Real Estate CRM API server."""
import uvicorn
from backend.config import API_HOST, API_PORT

if __name__ == "__main__":
    print(f"Starting Real Estate CRM API on {API_HOST}:{API_PORT}")
    uvicorn.run("backend.main:app", host=API_HOST, port=API_PORT, reload=True)
