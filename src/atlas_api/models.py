from __future__ import annotations

from datetime import datetime
from urllib.parse import urljoin

from attrs import define


__all__ = ("FFNStory",)

from cattrs import Converter


@define
class FFNStory:
    """The metadata of a FanFiction.Net (FFN) fic, retrieved from Atlas."""

    id: int
    author_id: int
    author_name: str
    title: str
    description: str
    published: datetime
    is_complete: bool
    rating: str
    language: str
    chapter_count: int
    word_count: int
    review_count: int
    favorite_count: int
    follow_count: int
    is_crossover: bool
    updated: datetime | None = None
    raw_genres: str | None = None
    raw_characters: str | None = None
    raw_fandoms: str | None = None
    fandom_id0: int | None = None
    fandom_id1: int | None = None

    @property
    def story_url(self) -> str:
        """:class:`str`: The url for the story on FFN."""

        return urljoin("https://www.fanfiction.net/s/", str(self.id))

    @property
    def author_url(self) -> str:
        """:class:`str`: The url for the author's FFN profile."""

        return urljoin("https://www.fanfiction.net/u/", str(self.author_id))


_meta_converter = Converter()
_meta_converter.register_structure_hook(datetime, lambda dt, _: datetime.fromisoformat(dt[:(-1 if "Z" in dt else 0)]))
_meta_converter.register_unstructure_hook(datetime, lambda dt: datetime.isoformat(dt[:(-1 if "Z" in dt else 0)]))