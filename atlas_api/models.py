from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from attrs import define, field, Factory
from cattrs import Converter
from cattrs.gen import make_dict_structure_fn


__all__ = ("Author", "FFNStory")


@define
class Author:
    """The basic metadata of a FanFiction.Net author.

    Attributes
    ----------
    id : :class:`int`
        The FFN id of the author.
    name : :class:`str`
        The name of the author.
    url : :class:`str`
        The url of the author's profile. Initializes based on their id.
    """

    id: int
    name: str
    url: str = field()
    @url.default
    def _url(self) -> str:
        return urljoin("https://www.fanfiction.net/u/", str(self.id))


@define
class FFNStory:
    """The metadata of a FanFiction.Net (FFN) fic, retrieved from Atlas.

    Attributes
    ----------
    id : :class:`int`
        The FFN id of the story.
    author : :class:`Author`
        Some of the author's FFN information.
    title : :class:`str`
        The story title.
    description : :class:`str`
        The description or summary.
    chapters : :class:`int`
        The number of chapters.
    published : :class:`datetime`
        The date and time when the story was published.
    is_complete : :class:`bool`
        Whether this story is complete.
    words : :class:`int`
        The number of words in the story.
    language : :class:`str`
        The language the story is written in.
    rating : :class:`str`
        The maturity rating of the story.
    is_crossover : :class:`bool`
        Whether this story is a crossover.
    reviews : :class:`int`
        The number of reviews this story has on FFN.
    favorites : :class:`int`
        The number of favorites this story has on FFN.
    follows : :class:`int`
        The number of follows this story has on FFN.
    url : :class:`str`
        The url of the work. Initializes based on the story's id.
    updated : :class:`datetime`, optional
        The date and time when the story was last updated. Can be absent.
    genres : list[:class:`str`]
        The declared genres for this story. Can be empty.
    characters : list[:class:`str`]
        The declared cast of characters. Can be empty.
    fandoms : list[:class:`str`]
        The fandom(s) this story occupies.
    fandom_ids : list[:class:`int` | None]
        The id(s) of the fandoms this story is in. Can be filled with None.
    """

    id: int
    author: Author
    title: str
    description: str
    chapters: int
    published: datetime
    is_complete: bool
    words: int
    language: str
    rating: str
    is_crossover: bool
    reviews: int
    favorites: int
    follows: int
    url: str = field()
    @url.default
    def _url(self) -> str:
        return urljoin("https://www.fanfiction.net/s/", str(self.id))
    updated: datetime | None = None
    genres: list[str] = Factory(list)
    characters: list[str] = Factory(list)
    fandoms: list[str] = Factory(list)
    fandom_ids: list[int | None] = Factory(list)


# Cattrs converter instantiation, hooks, and logic.
def _atlas_preprocessing(cls: type, c: Converter) -> None:
    """Registers a specific structuring hook to process the API response into a model properly."""

    handler = make_dict_structure_fn(cls, c)  # type: ignore

    def preprocessing_hook(val: dict[str, Any], _) -> Any:
        """Beats the dictionary into shape before structuring it."""
        new_val = {}

        for key in val:
            if "author" in key and (suffix := (key.split("_"))[1]):
                new_val.setdefault("author", {})[suffix] = val[key]
            elif "fandom_id" in key:
                new_val.setdefault("fandom_ids", []).append(val[key])
            elif "_count" in key:
                new_val[(key.split("_"))[0] + "s"] = val[key]

        if chars := val["raw_characters"]:
            new_val["characters"] = [ch for ch in chars.replace("[", ", ").replace("]", ", ").split(", ") if ch.strip()]
        if genres := val["raw_genres"]:
            new_val["genres"] = genres.split("/")
        if fandoms := val["raw_fandoms"]:
            split_fandoms = fandoms.split(" and ", 1)
            if len(split_fandoms) > 1:
                split_fandoms[-1] = split_fandoms[-1].removesuffix(" Crossovers")
            new_val["fandoms"] = split_fandoms
        return handler(val | new_val, _)

    c.register_structure_hook(cls, preprocessing_hook)


_meta_converter = Converter()
_meta_converter.register_structure_hook(datetime, lambda dt, _: datetime.fromisoformat(dt[:(-1 if "Z" in dt else 0)]))
_meta_converter.register_unstructure_hook(datetime, lambda dt: datetime.isoformat(dt[:(-1 if "Z" in dt else 0)]))
_atlas_preprocessing(FFNStory, _meta_converter)
