import csv
import io
import zipfile
from datetime import datetime
from typing import Optional

from .base import BaseParser, ParsedContent

_SIGNAL_FILES = {"profile.csv", "posts.csv", "connections.csv", "articles.csv"}


class LinkedInParser(BaseParser):
    source_name = "linkedin"

    @classmethod
    def can_parse(cls, names: list[str]) -> bool:
        lower = {n.lower().rsplit("/", 1)[-1] for n in names}
        return bool(lower & _SIGNAL_FILES)

    def parse(self, zf: zipfile.ZipFile) -> list[ParsedContent]:
        name_map = {n.lower().rsplit("/", 1)[-1]: n for n in zf.namelist()}
        author = self._get_author(zf, name_map)
        items: list[ParsedContent] = []
        items.extend(self._parse_profile(zf, name_map, author))
        items.extend(self._parse_posts(zf, name_map, author))
        items.extend(self._parse_articles(zf, name_map, author))
        items.extend(self._parse_comments(zf, name_map, author))
        return items

    def _get_author(self, zf: zipfile.ZipFile, name_map: dict) -> str:
        if "profile.csv" not in name_map:
            return "Unknown"
        for row in self._read_csv(zf, name_map["profile.csv"]):
            first = row.get("First Name", "")
            last = row.get("Last Name", "")
            return f"{first} {last}".strip() or "Unknown"
        return "Unknown"

    def _parse_profile(self, zf: zipfile.ZipFile, name_map: dict, author: str) -> list[ParsedContent]:
        if "profile.csv" not in name_map:
            return []
        items = []
        for row in self._read_csv(zf, name_map["profile.csv"]):
            for field_key, field_name in [("Headline", "headline"), ("Summary", "summary")]:
                text = row.get(field_key, "").strip()
                if text:
                    items.append(ParsedContent(
                        source="linkedin", content_type="profile",
                        text=text, author=author, metadata={"field": field_name},
                    ))
        return items

    def _parse_posts(self, zf: zipfile.ZipFile, name_map: dict, author: str) -> list[ParsedContent]:
        if "posts.csv" not in name_map:
            return []
        items = []
        for row in self._read_csv(zf, name_map["posts.csv"]):
            text = row.get("ShareCommentary", "").strip()
            if not text or len(text) < 10:
                continue
            items.append(ParsedContent(
                source="linkedin", content_type="post", text=text, author=author,
                timestamp=self._parse_date(row.get("Date", "")),
                metadata={"url": row.get("SharedUrl", "")},
            ))
        return items

    def _parse_articles(self, zf: zipfile.ZipFile, name_map: dict, author: str) -> list[ParsedContent]:
        if "articles.csv" not in name_map:
            return []
        items = []
        for row in self._read_csv(zf, name_map["articles.csv"]):
            title = row.get("Title", "").strip()
            body = row.get("Body", "").strip()
            text = f"{title}\n\n{body}".strip() if body else title
            if not text or len(text) < 10:
                continue
            items.append(ParsedContent(
                source="linkedin", content_type="article", text=text, author=author,
                timestamp=self._parse_date(row.get("Published", "") or row.get("LastModified", "")),
                metadata={"url": row.get("Url", "")},
            ))
        return items

    def _parse_comments(self, zf: zipfile.ZipFile, name_map: dict, author: str) -> list[ParsedContent]:
        if "comments.csv" not in name_map:
            return []
        items = []
        for row in self._read_csv(zf, name_map["comments.csv"]):
            text = row.get("Message", "").strip()
            if not text or len(text) < 20:
                continue
            items.append(ParsedContent(
                source="linkedin", content_type="comment", text=text, author=author,
                timestamp=self._parse_date(row.get("Date", "")),
            ))
        return items

    @staticmethod
    def _read_csv(zf: zipfile.ZipFile, path: str) -> list[dict]:
        try:
            content = zf.read(path).decode("utf-8-sig")
            return list(csv.DictReader(io.StringIO(content)))
        except Exception:
            return []

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%b %d, %Y"):
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        return None
