"""Environment configuration. Local development deliberately needs no cloud service."""

import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./forecast.db")
ALLOWED_ORIGINS = {
    value.strip()
    for value in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5177,http://127.0.0.1:5177,http://localhost:8084,http://127.0.0.1:8084,http://localhost:8004,http://127.0.0.1:8004",
    ).split(",")
    if value.strip()
}
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
SESSION_SECONDS = 60 * 60 * 24 * 7
STATIC_DIR = Path(os.getenv("STATIC_DIR", "../frontend/dist"))
