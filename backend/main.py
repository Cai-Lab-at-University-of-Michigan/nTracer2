#!/usr/bin/env python3

import uvicorn
import os

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.environ.get("SERVER_PORT", 8085)))
