from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

import aiohttp

from . import __version__
from .models import _meta_converter, FFNStory

if TYPE_CHECKING:
    from .types import StoryMetadata as StoryMetadataPayload


__all__ = ("ATLAS_BASE_URL", "extract_fic_id", "AtlasException", "AtlasClient")


ATLAS_BASE_URL = "https://atlas.fanfic.dev/v0/"


def extract_fic_id(text: str) -> int | None:
    """Extract the fic id from the first valid FFN url in a string.

    Parameters
    ----------
    text : :class:`str`
        The string to parse for an FFN url.

    Returns
    -------
    fic_id : :class:`int` | None
        The id of the first found fanfiction url in the string, if present.
    """

    re_ffn_url = re.compile(r"(https://|http://|)(www\.|m\.|)fanfiction\.net/s/(\d+)")
    fic_id = int(result.group(3)) if (result := re.search(re_ffn_url, text)) else None
    return fic_id


class AtlasException(Exception):
    """The base exception for the Atlas API."""

    pass


class AtlasClient:
    """A small async wrapper for accessing Iris's Atlas API.

    Parameters
    ----------
    session : :class:`aiohttp.ClientSession`, optional
        The asynchronous HTTP session to make requests with. If not passed in, automatically generated. Closing it is
        not handled automatically by the class.
    auth : :class:`BasicAuth`, optional
        The HTTP authentication details to use the API.
    headers : dict, optional
        The HTTP headers to send with any requests.
    sema_limit : :class:`int`
        The limit on the number of requests that can be made at once asynchronously. If not between 1 and 3, defaults to 3.


    """

    def __init__(
            self,
            *,
            auth: tuple[str, str] | None = None,
            headers: dict | None = None,
            session: aiohttp.ClientSession | None = None,
            sema_limit: int | None = None
    ) -> None:
        self._auth = aiohttp.BasicAuth(login=auth[0], password=auth[1]) if auth is not None else auth
        self.headers = headers or {"User-Agent": f"Atlas API wrapper/v{__version__}+@Thanos"}
        self.session = session
        self._semaphore = asyncio.Semaphore(value=(sema_limit if (sema_limit and 1 <= sema_limit <= 3) else 2))
        self._sema_limit = sema_limit

        # Use pre-structured converter to convert json responses to models.
        self._converter = _meta_converter

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
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
            raise ValueError("To prevent hitting the Atlas API too much, this limit has to be between 1 and 3 inclusive.")

    async def start_session(self) -> None:
        """Start an HTTP session attached to this instance if necessary."""

        if (not self.session) or self.session.closed:
            self.session = aiohttp.ClientSession()

    async def close(self) -> None:
        """Close the HTTP session attached to this instance if necessary."""

        if self.session and (not self.session.closed):
            await self.session.close()

    async def _get(self, endpoint: str, params: dict | None = None) -> Any:
        """Gets FFN data from the Atlas API.

        This restricts the number of simultaneous requests.

        Parameters
        ----------
        endpoint : :class:`str`
            The path parameters for the endpoint.
        params : dict, optional
            The query parameters to request from the endpoint.

        Returns
        -------
        Any
            The JSON data from the API response.

        Raises
        ------
        AtlasException
            If there's a client response error.
        """

        # TODO: Implement caching mechanism.
        await self.start_session()

        async with self._semaphore:
            try:
                url = urljoin(ATLAS_BASE_URL, endpoint)
                async with self.session.get(url, params=params, headers=self.headers, auth=self._auth) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data

            except aiohttp.ClientResponseError as exc:
                raise AtlasException(f"HTTP {exc.status}: {exc.message}")

    async def max_update_id(self) -> int:
        """Gets the maximum `update_id` currently in use.

        Returns
        -------
        :class:`int`
            The update id.
        """

        update_id: int = await self._get("update_id")
        return update_id

    async def max_story_id(self) -> int:
        """Gets the maximum known FFN story `id`.

        Returns
        -------
        :class:`int`
            The story id.
        """

        story_id: int = await self._get("ffn/id")
        return story_id

    async def get_bulk_metadata(
            self,
            min_update_id: int | None = None,
            min_fic_id: int | None = None,
            title_ilike: str | None = None,
            description_ilike: str | None = None,
            raw_fandoms_ilike: str | None = None,
            author_id: int | None = None,
            limit: int | None = None
    ) -> list[FFNStory]:
        """Gets a block of FFN story metadata.

        Parameters
        ----------
        min_update_id : :class:`int`, optional
            The minimum `update_id` used to filter results.
        min_fic_id : :class:`int`, optional
            The minimum FFN fic `id` used to filter results.
        title_ilike : :class:`str`, optional
            A sql `ilike` query applied to `title` to filter results. SQL-style percent and underscore operators allowed.
        description_ilike : :class:`str`, optional
            A sql `ilike` query applied to `description` to filter results. SQL-style percent and underscore operators allowed.
        raw_fandoms_ilike : :class:`str`, optional
            A sql `ilike` query applied to `raw_fandoms` to filter results. SQL-style percent and underscore operators allowed.
        author_id : :class:`int`, optional
            The `author_id` used to filter results.
        limit : :class:`int`, optional
            The maximum number of results to return. The upper limit is 10000.

        Returns
        -------
        list[:class:`FFNStory`]
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
                raise ValueError("The results limit should between 1 and 10000, inclusive.")
            query["limit"] = limit

        payload: list[StoryMetadataPayload] = await self._get("ffn/meta", params=query)
        metadata_list = self._converter.structure(payload, list[FFNStory])
        return metadata_list

    async def get_story_metadata(self, ffn_id: int) -> FFNStory:
        """Gets a specific FFN fic's metadata.

        Parameters
        ----------
        ffn_id : :class:`int`
            The FFN `id` to lookup.

        Returns
        -------
        metadata : :class:`FFNStory`
            The metadata of the queried fanfic.
        """

        payload: StoryMetadataPayload = await self._get(f"ffn/meta/{ffn_id}")
        metadata = self._converter.structure(payload, FFNStory)
        return metadata
