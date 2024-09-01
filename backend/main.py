import uvicorn
import os

uvicorn.run("server:app", host="0.0.0.0", port=int(os.environ.get("SERVER_PORT", 8085)))
