from __future__ import annotations

import asyncio
import re
from datetime import datetime
from urllib.parse import urljoin

import aiohttp
from cattrs import Converter

from .models import FFNMetadata


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
    sema_limit : :class:`int`, default=5
        The limit on the number of requests that can be made at once asynchronously.
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
        self._headers = headers or {"User-Agent": f"Atlas API wrapper/v0.0.1+@Thanos"}
        self._session = session
        self._semaphore = asyncio.Semaphore(value=(sema_limit if (sema_limit is not None and sema_limit >= 1) else 5))

        self._converter = Converter()
        self._converter.register_structure_hook(datetime, lambda dt, _: datetime.fromisoformat(dt[:(-1 if "Z" in dt else 0)]))
        self._converter.register_unstructure_hook(datetime, lambda dt: datetime.isoformat(dt[:(-1 if "Z" in dt else 0)]))

    async def __aenter__(self) -> AtlasClient:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def start_session(self) -> None:
        """Start an HTTP session attached to this instance if necessary."""

        if (not self._session) or self._session.closed:
            self._session = aiohttp.ClientSession()

    async def close(self) -> None:
        """Close the HTTP session attached to this instance if necessary."""

        if self._session and (not self._session.closed):
            await self._session.close()

        self._session = None

    async def _get(self, endpoint: str, params: dict | None = None) -> int | dict | list[dict]:
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
        :class:`int` | dict | list[dict]
            The JSON data from the API's response.

        Raises
        ------
        AtlasException
            If there's a client response error.
        """

        await self.start_session()

        async with self._semaphore:
            try:
                url = urljoin(ATLAS_BASE_URL, endpoint)
                async with self._session.get(url, params=params, headers=self._headers, auth=self._auth) as response:
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

        update_id = await self._get("update_id")
        return update_id

    async def max_story_id(self) -> int:
        """Gets the maximum known FFN story `id`.

        Returns
        -------
        :class:`int`
            The story id.
        """

        ffn_story_id = await self._get("ffn/id")
        return ffn_story_id

    async def get_bulk_metadata(
            self,
            min_update_id: int | None = None,
            min_fic_id: int | None = None,
            title_ilike: str | None = None,
            description_ilike: str | None = None,
            raw_fandoms_ilike: str | None = None,
            author_id: int | None = None,
            limit: int | None = None
    ) -> list[FFNMetadata]:
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
        list[:class:`FFNMetadata`]
            A list of dicts containing metadata for individual fics.

        Raises
        ------
        ValueError
            If the `limit` parameter isn't between 1 and 10000.
        """

        query_params = {}

        if min_update_id:
            query_params["min_update_id"] = min_update_id
        if min_fic_id:
            query_params["min_fic_id"] = min_fic_id
        if title_ilike:
            query_params["title_ilike"] = title_ilike
        if description_ilike:
            query_params["description_ilike"] = description_ilike
        if raw_fandoms_ilike:
            query_params["raw_fandoms_ilike"] = raw_fandoms_ilike
        if author_id:
            query_params["author_id"] = author_id

        if limit:
            if 1 <= limit <= 100000:
                query_params["limit"] = limit
            else:
                raise ValueError("The results limit should between 1 and 10000, inclusive.")

        raw_metadata_list: list[dict] = await self._get("ffn/meta", params=query_params)
        metadata_list = self._converter.structure(raw_metadata_list, list[FFNMetadata])

        return metadata_list

    async def get_story_metadata(self, ffn_id: int) -> FFNMetadata:
        """Gets a specific FFN fic's metadata.

        Parameters
        ----------
        ffn_id : :class:`int`
            The FFN `id` to lookup.

        Returns
        -------
        metadata : :class:`FFNMetadata`
            The metadata of the queried fanfic.
        """

        raw_metadata: dict = await self._get(f"ffn/meta/{ffn_id}")
        metadata = self._converter.structure(raw_metadata, FFNMetadata)
        return metadata
