import hashlib
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ParsedContent:
    source: str           # linkedin | twitter | instagram
    content_type: str     # post | article | profile | tweet | story | comment
    text: str
    author: str = ""
    timestamp: Optional[datetime] = None
    metadata: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        fingerprint = f"{self.source}:{self.content_type}:{self.text[:200]}"
        return hashlib.sha256(fingerprint.encode()).hexdigest()[:20]


class BaseParser:
    source_name: str = ""

    @classmethod
    def can_parse(cls, names: list[str]) -> bool:
        raise NotImplementedError

    def parse(self, zf: zipfile.ZipFile) -> list[ParsedContent]:
        raise NotImplementedError
