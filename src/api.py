"""
api.py: A small asynchronous wrapper for iris's Atlas FanFiction.Net (or FFN) metadata API.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import ClassVar

from aiohttp import BasicAuth, ClientSession, client_exceptions
from cattrs import Converter

from models import FFNMetadata


class AtlasException(Exception):
    """The base exception for the Atlas API module."""

    pass


class AtlasAPI:
    """A small async wrapper for iris's Atlas FanFiction.Net (or FFN) API.

    Parameters
    ----------
    auth : :class:`BasicAuth`
        The HTTP authentication details to use the API.
    session: :class:`ClientSession`
        The asynchronous HTTP session to make requests with. If not passed in, automatically generated. Closing it is
        not handled automatically by the class.
    """

    ATLAS_BASE_URL: ClassVar[str] = "https://atlas.fanfic.dev/v0/"

    def __init__(self, *, auth: BasicAuth | None = None, session: ClientSession | None = None) -> None:
        self._auth = auth
        self._session = session or ClientSession()
        self._headers = {"User-Agent": "Atlas API wrapper"}
        self._semaphore = asyncio.Semaphore(value=5)

        self.converter = Converter()
        self.converter.register_structure_hook(datetime, lambda dt, _: datetime.fromisoformat(dt[:(-1 if "Z" in dt else 0)]))
        self.converter.register_unstructure_hook(datetime, lambda dt: datetime.isoformat(dt[:(-1 if "Z" in dt else 0)]))

    @property
    def auth(self) -> BasicAuth:
        """:class:`BasicAuth`: The authentication details needed to use the Atlas API."""

        return self._auth

    @auth.setter
    def auth(self, value: BasicAuth) -> None:
        self._auth = value

    def close_session(self):
        """Close the HTTP session attached to this instance."""

        self._session.close()

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

        async with self._semaphore:
            try:
                async with self._session.get(
                    url=self.ATLAS_BASE_URL + endpoint,
                    headers=self._headers,
                    params=params,
                    auth=self._auth
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data

            except client_exceptions.ClientResponseError as exc:
                raise AtlasException(f"{exc.status}: {exc.message}")

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
            if limit >= 1 and limit <= 100000:
                query_params["limit"] = limit
            else:
                raise ValueError("The results limit should between 1 and 10000, inclusive.")

        raw_metadata_list: list[dict] = await self._get("ffn/meta", params=query_params)
        metadata_list = self.converter.structure(raw_metadata_list, list[FFNMetadata])

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
        metadata = self.converter.structure(raw_metadata, FFNMetadata)
        return metadata

    @staticmethod
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
