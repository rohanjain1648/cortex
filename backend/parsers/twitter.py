import json
import re
import zipfile
from datetime import datetime
from typing import Optional

from .base import BaseParser, ParsedContent

_SIGNAL_FILES = {"tweets.js", "tweet.js"}


class TwitterParser(BaseParser):
    source_name = "twitter"

    @classmethod
    def can_parse(cls, names: list[str]) -> bool:
        return any(n.lower().rsplit("/", 1)[-1] in _SIGNAL_FILES for n in names)

    def parse(self, zf: zipfile.ZipFile) -> list[ParsedContent]:
        tweets_file = next(
            (n for n in zf.namelist() if n.lower().rsplit("/", 1)[-1] in _SIGNAL_FILES),
            None,
        )
        if not tweets_file:
            return []

        raw = zf.read(tweets_file).decode("utf-8")
        raw = re.sub(r"^window\.[^=]+=\s*", "", raw.strip())

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []

        items = []
        for entry in data:
            tweet = entry.get("tweet", entry)
            text = tweet.get("full_text", tweet.get("text", "")).strip()

            if not text or len(text) < 10:
                continue
            if text.startswith("RT @"):
                continue
            if re.match(r"^(@\w+\s*)+$", text):
                continue

            items.append(ParsedContent(
                source="twitter",
                content_type="tweet",
                text=self._clean_text(text),
                timestamp=self._parse_date(tweet.get("created_at", "")),
                metadata={
                    "id": tweet.get("id_str", ""),
                    "likes": str(tweet.get("favorite_count", 0)),
                    "retweets": str(tweet.get("retweet_count", 0)),
                },
            ))
        return items

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%a %b %d %H:%M:%S +0000 %Y")
        except ValueError:
            return None

    @staticmethod
    def _clean_text(text: str) -> str:
        return re.sub(r"https://t\.co/\S+", "", text).strip()
