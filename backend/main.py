import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app as application

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:application", host="0.0.0.0", port=port)
