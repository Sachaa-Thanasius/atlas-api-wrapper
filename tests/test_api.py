# TODO: Switch to tests that don't ping the API.
import asyncio
import json
import pathlib

import aiohttp
import pytest

import atlas_api


# Can't access the API without authorization credentials.
with pathlib.Path("config.json").open(encoding="utf-8") as f:
    info = json.load(f)
atlas_auth = aiohttp.BasicAuth(*info.values())


@pytest.mark.parametrize(
    "test_url,expected",
    [
        ("https://www.fanfiction.net/s/13912800/1/Magical-Marvel", 13912800),
        ("https://www.fanfiction.net/s/14182918/1/", 14182918),
        ("https://www.fanfiction.net/s/asdfasdfasdf", None),
        (
            "https://www.fanfiction.net/Naruto-and-High-School-DxD-%E3%83%8F%E3%82%A4%E3%82%B9%E3%82%AF%E3%83%BC%E3%83%ABD-D-Crossovers/1402/9502/",
            None,
        ),
    ],
)
def test_extract_fic_id(test_url, expected):
    assert atlas_api.extract_fic_id(test_url) == expected


def test_parse_story():
    test_data = """\
{
    "id": 14174230,
    "update_id": 446518576,
    "web_id": 151645549,
    "web_created": "2023-06-10T06:15:58.105Z",
    "author_id": 424665,
    "author_name": "megamatt09",
    "title": "Parselking",
    "description": "In Madam Malkin's Robes for All Occasions, Harry meets a young witch named Lyra Malfoy. \
    Everything changes. AU. Dark!Harry. Slytherin!Harry. Fem!Draco. Eventual Harry/Lyra/Others, but that's in \
    the future. On Hiatus for the summer.",
    "published": "2022-12-18T23:18:25Z",
    "updated": "2023-05-21T21:04:53Z",
    "is_complete": false,
    "rating": "M",
    "language": "English",
    "raw_genres": "Drama/Supernatural",
    "chapter_count": 13,
    "word_count": 114913,
    "review_count": 216,
    "favorite_count": 878,
    "follow_count": 1073,
    "raw_characters": null,
    "raw_fandoms": "Harry Potter",
    "is_crossover": false,
    "fandom_id0": 224,
    "fandom_id1": null
}
    """
    story = atlas_api.parse_story(test_data)
    assert story.chapters == 13
    assert story.words == 114913
    assert story.reviews == 216
    assert story.favorites == 878
    assert story.follows == 1073
    assert story.fandoms == ("Harry Potter",)
    assert story.genres == ("Drama", "Supernatural")


@pytest.mark.asyncio
async def test_max_update_id():
    async with atlas_api.Client(auth=atlas_auth) as client:
        max_update_id = await client.max_update_id()
    assert isinstance(max_update_id, int)


@pytest.mark.asyncio
async def test_max_story_id():
    async with atlas_api.Client(auth=atlas_auth) as client:
        max_story_id = await client.max_story_id()
    assert isinstance(max_story_id, int)


@pytest.mark.parametrize(
    "test_title_query",
    ["%Ashes of Chaos%"],
)
@pytest.mark.asyncio
async def test_get_bulk_metadata(test_title_query):
    async with atlas_api.Client(auth=atlas_auth) as client:
        with pytest.raises(TimeoutError):  # NOTE: This endpoint is currently dead.
            bulk_metadata = await asyncio.wait_for(
                client.get_bulk_metadata(title_ilike=test_title_query, limit=5),
                10.0,
            )
            assert test_title_query
            for fic in bulk_metadata:
                assert fic
                assert fic.id
                assert fic.title


@pytest.mark.parametrize(
    "test_url",
    ["https://www.fanfiction.net/s/13912800/1/Magical-Marvel", "https://www.fanfiction.net/s/14182918/1/"],
)
@pytest.mark.asyncio
async def test_get_story_metadata(test_url):
    async with atlas_api.Client(auth=atlas_auth) as client:
        ffn_id = atlas_api.extract_fic_id(test_url)
        story_metadata = await client.get_story_metadata(ffn_id)
        assert story_metadata
        assert isinstance(story_metadata.id, int)
        assert story_metadata.title and isinstance(story_metadata.title, str)
        assert story_metadata.description and isinstance(story_metadata.description, str)
