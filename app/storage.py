import sqlite3
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import email.utils
from pathlib import Path

class Storage:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    guid TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    link TEXT NOT NULL,
                    author TEXT,
                    source_feed TEXT,
                    description TEXT,
                    image_url TEXT,
                    pub_date TEXT NOT NULL,
                    pub_date_ts INTEGER NOT NULL,
                    first_seen_ts INTEGER NOT NULL,
                    raw_date_str TEXT,
                    title_tr TEXT,
                    summary_tr TEXT,
                    category_tr TEXT
                )
            """)
            for col in ["title_tr", "summary_tr", "category_tr", "is_turkey"]:
                try:
                    cursor.execute(f"ALTER TABLE items ADD COLUMN {col} TEXT")
                except sqlite3.OperationalError:
                    pass

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at INTEGER
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_pub_date_ts ON items (pub_date_ts DESC)")
            conn.commit()

    def save_items(self, items: List[Dict[str, Any]]) -> int:
        """
        Saves or updates items. Returns count of newly inserted items.
        Keeps original pub_date and first_seen_ts for existing items.
        """
        now_ts = int(time.time())
        new_count = 0

        with self._get_connection() as conn:
            cursor = conn.cursor()
            for it in items:
                guid = it["guid"]
                cursor.execute(
                    "SELECT guid, pub_date, pub_date_ts, first_seen_ts, title_tr, summary_tr, category_tr, image_url, is_turkey FROM items WHERE guid = ?",
                    (guid,)
                )
                existing = cursor.fetchone()

                title_tr = it.get("title_tr") or (existing["title_tr"] if existing else None)
                summary_tr = it.get("summary_tr") or (existing["summary_tr"] if existing else None)
                category_tr = it.get("category_tr") or (existing["category_tr"] if existing else None)
                
                # Determine image URL: prefer new valid image, keep existing resolved image if new is empty/camo
                img_url = (it.get("image_url") or "").strip()
                if existing and existing["image_url"]:
                    if not img_url or "inoreader.com/camo" in img_url:
                        img_url = existing["image_url"]

                is_val = it.get("is_turkey")
                if is_val is None and existing and "is_turkey" in existing.keys():
                    is_val = existing["is_turkey"]
                is_turkey_val = 1 if (str(is_val).strip() in ["1", "True", "true"] or is_val == 1) else 0

                if existing:
                    cursor.execute("""
                        UPDATE items SET
                            title = ?,
                            link = ?,
                            author = ?,
                            source_feed = ?,
                            description = ?,
                            image_url = ?,
                            raw_date_str = ?,
                            title_tr = ?,
                            summary_tr = ?,
                            category_tr = ?,
                            is_turkey = ?
                        WHERE guid = ?
                    """, (
                        it["title"],
                        it["link"],
                        it.get("author", ""),
                        it.get("source_feed", ""),
                        it.get("description", ""),
                        img_url,
                        it.get("raw_date_str", ""),
                        title_tr,
                        summary_tr,
                        category_tr,
                        is_turkey_val,
                        guid
                    ))
                else:
                    new_count += 1
                    pub_ts = it.get("pub_date_ts", now_ts)
                    pub_date_rfc = it.get("pub_date")
                    if not pub_date_rfc:
                        dt = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
                        pub_date_rfc = email.utils.format_datetime(dt)

                    cursor.execute("""
                        INSERT INTO items (
                            guid, title, link, author, source_feed,
                            description, image_url, pub_date, pub_date_ts,
                            first_seen_ts, raw_date_str,
                            title_tr, summary_tr, category_tr, is_turkey
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        guid,
                        it["title"],
                        it["link"],
                        it.get("author", ""),
                        it.get("source_feed", ""),
                        it.get("description", ""),
                        img_url,
                        pub_date_rfc,
                        pub_ts,
                        now_ts,
                        it.get("raw_date_str", ""),
                        title_tr,
                        summary_tr,
                        category_tr,
                        is_turkey_val
                    ))

            conn.commit()

        return new_count

    def update_item_translation(self, guid: str, title_tr: str, summary_tr: str, category_tr: str, is_turkey: int = 0):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE items SET
                    title_tr = ?,
                    summary_tr = ?,
                    category_tr = ?,
                    is_turkey = ?
                WHERE guid = ?
            """, (title_tr, summary_tr, category_tr, int(is_turkey), guid))
            conn.commit()

    def update_item_image(self, guid: str, image_url: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE items SET
                    image_url = ?
                WHERE guid = ?
            """, (image_url, guid))
            conn.commit()

    def get_items(self, limit: int = 150) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT guid, title, link, author, source_feed,
                       description, image_url, pub_date, pub_date_ts,
                       first_seen_ts, raw_date_str,
                       title_tr, summary_tr, category_tr, is_turkey
                FROM items
                ORDER BY pub_date_ts DESC, first_seen_ts DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            items_list = []
            seen_guids = set()
            for r in rows:
                d = dict(r)
                raw_tr = d.get("is_turkey")
                d["is_turkey"] = 1 if (str(raw_tr).strip() in ["1", "True", "true"] or raw_tr == 1) else 0
                items_list.append(d)
                seen_guids.add(d["guid"])

            # Türkiye haberlerinin her zaman portal ve manşet için çekilmesini garanti et
            cursor.execute("""
                SELECT guid, title, link, author, source_feed,
                       description, image_url, pub_date, pub_date_ts,
                       first_seen_ts, raw_date_str,
                       title_tr, summary_tr, category_tr, is_turkey
                FROM items
                WHERE is_turkey = 1 OR category_tr = 'Türkiye' OR guid LIKE 'tr_water:%'
                ORDER BY pub_date_ts DESC, first_seen_ts DESC
                LIMIT 35
            """)
            for tr_r in cursor.fetchall():
                d = dict(tr_r)
                if d["guid"] not in seen_guids:
                    d["is_turkey"] = 1
                    items_list.append(d)
                    seen_guids.add(d["guid"])

            return items_list

    def count_items(self) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM items")
            return cursor.fetchone()[0]

    def prune_items(self, max_items: int = 200):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM items
                WHERE guid NOT IN (
                    SELECT guid FROM items
                    ORDER BY pub_date_ts DESC, first_seen_ts DESC
                    LIMIT ?
                )
            """, (max_items,))
            conn.commit()

    def set_meta(self, key: str, value: str):
        now_ts = int(time.time())
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_meta (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at
            """, (key, value, now_ts))
            conn.commit()

    def get_meta(self, key: str) -> Optional[str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM sync_meta WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else None

    def get_sync_status(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value, updated_at FROM sync_meta")
            meta = {r["key"]: r["value"] for r in cursor.fetchall()}
            cursor.execute("SELECT COUNT(*) FROM items")
            total = cursor.fetchone()[0]

            return {
                "total_items": total,
                "last_sync_time": meta.get("last_sync_time"),
                "last_sync_status": meta.get("last_sync_status", "Never synced"),
                "last_error": meta.get("last_error", None),
                "feed_title": meta.get("feed_title", "SU"),
            }
