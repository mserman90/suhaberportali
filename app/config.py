import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Inoreader Target Stream URL
INOREADER_URL = os.getenv(
    "INOREADER_URL",
    "https://www.inoreader.com/stream/user/1006125058/tag/SU/view/html?cs=m"
)

# Fetch interval in minutes
FETCH_INTERVAL_MINUTES = int(os.getenv("FETCH_INTERVAL_MINUTES", "15"))

# Maximum items to keep in history
MAX_STORED_ITEMS = int(os.getenv("MAX_STORED_ITEMS", "350"))

# SQLite database path
DB_PATH = Path(os.getenv("DB_PATH", DATA_DIR / "feed_items.db"))

# Server settings
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Feed metadata
FEED_TITLE = os.getenv("FEED_TITLE", "SU - Inoreader Akışı")
FEED_DESCRIPTION = os.getenv(
    "FEED_DESCRIPTION",
    "Inoreader SU etiketli yayınların otomatik RSS 2.0 / Atom akışı"
)
FEED_LANGUAGE = os.getenv("FEED_LANGUAGE", "tr")

# Optional public base URL (e.g. https://my-feed.example.com)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
