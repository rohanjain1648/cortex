import json
import re
import zipfile
from datetime import datetime
from typing import Optional

from .base import BaseParser, ParsedContent


class InstagramParser(BaseParser):
    source_name = "instagram"

    @classmethod
    def can_parse(cls, names: list[str]) -> bool:
        lower = [n.lower() for n in names]
        return any(
            "posts_1.json" in n or "personal_information.json" in n or
            ("content/" in n and n.endswith(".json"))
            for n in lower
        )

    def parse(self, zf: zipfile.ZipFile) -> list[ParsedContent]:
        author = self._get_author(zf)
        items: list[ParsedContent] = []

        for name in zf.namelist():
            lower = name.lower()
            basename = lower.rsplit("/", 1)[-1]
            if re.match(r"posts_\d+\.json", basename):
                items.extend(self._parse_posts(zf, name, author))
            elif "stories.json" in lower:
                items.extend(self._parse_stories(zf, name, author))
        return items

    def _get_author(self, zf: zipfile.ZipFile) -> str:
        for name in zf.namelist():
            if "personal_information.json" in name.lower():
                try:
                    data = json.loads(zf.read(name).decode("utf-8"))
                    if isinstance(data, dict):
                        pi = data.get("profile_user", [{}])
                        if pi:
                            entry = pi[0].get("string_map_data", {}).get("Name", {})
                            return entry.get("value", "Unknown")
                except Exception:
                    pass
        return "Unknown"

    def _parse_posts(self, zf: zipfile.ZipFile, path: str, author: str) -> list[ParsedContent]:
        try:
            data = json.loads(zf.read(path).decode("utf-8"))
        except Exception:
            return []

        posts = data if isinstance(data, list) else data.get("photos", [])
        items = []
        for post in posts:
            caption = self._extract_caption(post)
            if not caption or len(caption) < 10:
                continue
            items.append(ParsedContent(
                source="instagram", content_type="post",
                text=caption, author=author,
                timestamp=self._extract_timestamp(post),
            ))
        return items

    def _parse_stories(self, zf: zipfile.ZipFile, path: str, author: str) -> list[ParsedContent]:
        try:
            data = json.loads(zf.read(path).decode("utf-8"))
        except Exception:
            return []

        stories = data.get("ig_stories", data) if isinstance(data, dict) else data
        items = []
        for story in (stories if isinstance(stories, list) else []):
            caption = self._extract_caption(story)
            if not caption or len(caption) < 10:
                continue
            items.append(ParsedContent(
                source="instagram", content_type="story",
                text=caption, author=author,
                timestamp=self._extract_timestamp(story),
            ))
        return items

    @staticmethod
    def _extract_caption(item: dict) -> str:
        if not isinstance(item, dict):
            return ""
        if "media" in item:
            for media in item["media"]:
                t = media.get("title", "").strip()
                if t:
                    return t
        for d in item.get("data", []):
            p = d.get("post", "").strip()
            if p:
                return p
        return item.get("title", item.get("caption", "")).strip()

    @staticmethod
    def _extract_timestamp(item: dict) -> Optional[datetime]:
        ts = None
        if "media" in item and item["media"]:
            ts = item["media"][0].get("creation_timestamp")
        if ts is None:
            ts = item.get("creation_timestamp", item.get("timestamp"))
        if isinstance(ts, (int, float)):
            try:
                return datetime.fromtimestamp(ts)
            except Exception:
                pass
        return None
