from __future__ import annotations

import asyncio
import re
from datetime import datetime
from importlib.metadata import version as im_version
from typing import TYPE_CHECKING, Any, List, TypedDict
from urllib.parse import urljoin

import aiohttp
import msgspec


if TYPE_CHECKING:
    from types import TracebackType

    from typing_extensions import Self
else:
    Self = Any


__all__ = ("ATLAS_BASE_URL", "AtlasException", "Author", "Story", "Client", "extract_fic_id")


_FFN_STORY_REGEX = re.compile(r"(https://|http://|)(www\.|m\.|)fanfiction\.net/s/(?P<id>\d+)")
_DECODER = msgspec.json.Decoder()

ATLAS_BASE_URL = "https://atlas.fanfic.dev/v0/"


class AtlasException(Exception):
    """The base exception for the Atlas API."""


class StoryMetadataPayload(TypedDict):
    id: int
    update_id: int
    web_id: int
    web_created: str
    author_id: int
    author_name: str
    title: str
    description: str
    published: str
    updated: str | None
    is_complete: bool
    rating: str
    language: str
    raw_genres: str | None
    chapter_count: int
    word_count: int
    review_count: int
    favorite_count: int
    follow_count: int
    raw_characters: str | None
    raw_fandoms: str | None
    is_crossover: bool
    fandom_id0: int | None
    fandom_id1: int | None


class Author(msgspec.Struct):
    """The basic metadata of a FanFiction.Net author.

    Attributes
    ----------
    id: :class:`int`
        The FFN id of the author.
    name: :class:`str`
        The name of the author.
    url: :class:`str`
        The url of the author's profile. Initializes based on their id.
    """

    id: int
    name: str

    @property
    def url(self) -> str:
        return f"https://www.fanfiction.net/u/{self.id}"


class Story(msgspec.Struct):
    """The metadata of a FanFiction.Net (FFN) fic, retrieved from Atlas.

    Attributes
    ----------
    id: :class:`int`
        The FFN id of the story.
    author: :class:`Author`
        Some of the author's FFN information.
    title: :class:`str`
        The story title.
    description: :class:`str`
        The description or summary.
    chapters: :class:`int`
        The number of chapters.
    published: :class:`datetime`
        The date and time when the story was published.
    is_complete: :class:`bool`
        Whether this story is complete.
    words: :class:`int`
        The number of words in the story.
    language: :class:`str`
        The language the story is written in.
    rating: :class:`str`
        The maturity rating of the story.
    is_crossover: :class:`bool`
        Whether this story is a crossover.
    reviews: :class:`int`
        The number of reviews this story has on FFN.
    favorites: :class:`int`
        The number of favorites this story has on FFN.
    follows: :class:`int`
        The number of follows this story has on FFN.
    url: :class:`str`
        The url of the work. Initializes based on the story's id.
    updated: :class:`datetime`, optional
        The date and time when the story was last updated. Can be absent.
    genres: list[:class:`str`]
        The declared genres for this story. Can be empty.
    characters: list[:class:`str`]
        The declared cast of characters. Can be empty.
    fandoms: list[:class:`str`]
        The fandom(s) this story occupies.
    fandom_ids: list[:class:`int` | None]
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
    updated: datetime | None = None
    genres: list[str] = msgspec.field(default_factory=list)
    characters: list[str] = msgspec.field(default_factory=list)
    fandoms: list[str] = msgspec.field(default_factory=list)
    fandom_ids: list[int | None] = msgspec.field(default_factory=list)

    @property
    def url(self) -> str:
        return f"https://www.fanfiction.net/s/{self.id}"


def shape_data(data: dict[str, Any]) -> dict[str, Any]:
    # TODO: See if this can be optimized.
    updated: dict[str, Any] = {}
    for key in data:
        if "author" in key and (suffix := (key.split("_"))[1]):
            updated.setdefault("author", {})[suffix] = data[key]
        elif "fandom_id" in key:
            updated.setdefault("fandom_ids", []).append(data[key])
        elif "_count" in key:
            updated[(key.split("_"))[0] + "s"] = data[key]
    if chars := data["raw_characters"]:
        updated["characters"] = [ch for ch in chars.replace("[", ", ").replace("]", ", ").split(", ") if ch.strip()]
    if genres := data["raw_genres"]:
        updated["genres"] = genres.split("/")
    if fandoms := data["raw_fandoms"]:
        split_fandoms = fandoms.split(" and ", 1)
        if len(split_fandoms) > 1:
            split_fandoms[-1] = split_fandoms[-1].removesuffix(" Crossovers")
        updated["fandoms"] = split_fandoms
    data.update(updated)
    return data


def parse_story(data: bytes | str) -> Story:
    obj = _DECODER.decode(data)
    obj = shape_data(obj)
    return msgspec.convert(obj, type=Story)


def parse_story_list(data: bytes | str) -> list[Story]:
    objs = _DECODER.decode(data)
    objs = [shape_data(obj) for obj in objs]
    return msgspec.convert(objs, type=List[Story])


class Client:
    """A client for interacting with the Atlas API.

    Parameters
    ----------
    session: :class:`aiohttp.ClientSession`, optional
        The asynchronous HTTP session to make requests with. If not passed in, automatically generated. Closing it is
        not handled automatically by the class.
    auth: :class:`BasicAuth`, optional
        The HTTP authentication details to use the API.
    headers: dict, optional
        The HTTP headers to send with any requests.
    sema_limit: :class:`int`
        The limit on the number of requests that can be made at once asynchronously. If not between 1 and 3, defaults
        to 3.
    """

    def __init__(
        self,
        *,
        auth: aiohttp.BasicAuth | None = None,
        headers: dict[str, Any] | None = None,
        session: aiohttp.ClientSession | None = None,
        sema_limit: int | None = None,
    ) -> None:
        self._auth = auth
        self.headers = headers or {"User-Agent": f"Atlas API wrapper/v{im_version('atlas_api')}+@Thanos"}
        self.session = session
        self._sema_limit = sema_limit if (sema_limit and 1 <= sema_limit <= 3) else 2
        self._semaphore = asyncio.Semaphore(value=self._sema_limit)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    @property
    def sema_limit(self) -> int:
        """:class:`int`: The counter limit for the number of simultaneous requests."""

        return self._sema_limit

    @sema_limit.setter
    def sema_limit(self, value: int) -> None:
        if 1 <= value <= 3:
            self._sema_limit = value
            self._semaphore = asyncio.Semaphore(value)
        else:
            msg = "To prevent hitting the Atlas API too much, this limit has to be between 1 and 3 inclusive."
            raise ValueError(msg)

    async def start_session(self) -> None:
        """Start an HTTP session attached to this instance if necessary."""

        if (not self.session) or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self) -> None:
        """Close the HTTP session attached to this instance if necessary."""

        if self.session and (not self.session.closed):
            await self.session.close()

    async def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> bytes:
        """Gets FFN data from the Atlas API.

        This restricts the number of simultaneous requests.

        Parameters
        ----------
        endpoint: :class:`str`
            The path parameters for the endpoint.
        params: dict, optional
            The query parameters to request from the endpoint.

        Returns
        -------
        bytes
            The data from the API response.

        Raises
        ------
        AtlasException
            If there's a client response error.
        """

        # TODO: Implement caching mechanism.
        await self.start_session()
        assert self.session

        async with self._semaphore:
            try:
                url = urljoin(ATLAS_BASE_URL, endpoint)
                async with self.session.get(url, params=params, headers=self.headers, auth=self._auth) as response:
                    response.raise_for_status()
                    return await response.read()
            except aiohttp.ClientResponseError as exc:
                msg = f"HTTP {exc.status}: {exc.message}"
                raise AtlasException(msg) from None

    async def max_update_id(self) -> int:
        """Gets the maximum `update_id` currently in use.

        Returns
        -------
        :class:`int`
            The update id.
        """

        update_id: int = msgspec.json.decode(await self._get("update_id"))
        return update_id

    async def max_story_id(self) -> int:
        """Gets the maximum known FFN story `id`.

        Returns
        -------
        :class:`int`
            The story id.
        """

        story_id: int = msgspec.json.decode(await self._get("ffn/id"))
        return story_id

    async def get_bulk_metadata(
        self,
        min_update_id: int | None = None,
        min_fic_id: int | None = None,
        title_ilike: str | None = None,
        description_ilike: str | None = None,
        raw_fandoms_ilike: str | None = None,
        author_id: int | None = None,
        limit: int | None = None,
    ) -> list[Story]:
        """Gets a block of FFN story metadata.

        Parameters
        ----------
        min_update_id: :class:`int`, optional
            The minimum `update_id` used to filter results.
        min_fic_id: :class:`int`, optional
            The minimum FFN fic `id` used to filter results.
        title_ilike: :class:`str`, optional
            A sql `ilike` query applied to `title` to filter results. SQL-style percent and underscore operators
            allowed.
        description_ilike: :class:`str`, optional
            A sql `ilike` query applied to `description` to filter results. SQL-style percent and underscore operators
            allowed.
        raw_fandoms_ilike: :class:`str`, optional
            A sql `ilike` query applied to `raw_fandoms` to filter results. SQL-style percent and underscore operators
            allowed.
        author_id: :class:`int`, optional
            The `author_id` used to filter results.
        limit: :class:`int`, optional
            The maximum number of results to return. The upper limit is 10000.

        Returns
        -------
        list[:class:`Story`]
            A list of objects containing metadata for individual fics.

        Raises
        ------
        ValueError
            If the `limit` parameter isn't between 1 and 10000.
        """

        query = {}

        if min_update_id:
            query["min_update_id"] = min_update_id
        if min_fic_id:
            query["min_fic_id"] = min_fic_id
        if title_ilike:
            query["title_ilike"] = title_ilike
        if description_ilike:
            query["description_ilike"] = description_ilike
        if raw_fandoms_ilike:
            query["raw_fandoms_ilike"] = raw_fandoms_ilike
        if author_id:
            query["author_id"] = author_id
        if limit:
            if limit < 1 or limit > 10000:
                msg = "The results limit should between 1 and 10000, inclusive."
                raise ValueError(msg)
            query["limit"] = limit

        return parse_story_list(await self._get("ffn/meta/", params=query))

    async def get_story_metadata(self, ffn_id: int) -> Story:
        """Gets a specific FFN fic's metadata.

        Parameters
        ----------
        ffn_id: :class:`int`
            The FFN `id` to lookup.

        Returns
        -------
        metadata: :class:`Story`
            The metadata of the queried fanfic.
        """

        return parse_story(await self._get(f"ffn/meta/{ffn_id}"))


def extract_fic_id(text: str) -> int | None:
    """Extract the fic id from the first valid FFN url in a string.

    Parameters
    ----------
    text: :class:`str`
        The string to parse for an FFN url.

    Returns
    -------
    :class:`int` | None
        The id of the first found fanfiction url in the string, if present.
    """

    return int(result.group("id")) if (result := _FFN_STORY_REGEX.search(text)) else None
