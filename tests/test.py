"""
test.py: A small "test" for the Atlas API wrapper.
"""

import asyncio
import json
import pathlib

import aiohttp

import atlas_api


with pathlib.Path("config.json").open(encoding="utf-8") as f:
    info = json.load(f)
atlas_auth = aiohttp.BasicAuth(*info.values())


async def test() -> None:
    async with aiohttp.ClientSession() as session:
        client = atlas_api.Client(auth=atlas_auth, session=session)
        max_update_id = await client.max_update_id()
        print(f"Max Update ID: {max_update_id}\n")

        max_story_id = await client.max_story_id()
        print(f"Max Story ID: {max_story_id}\n")

        # Search all FFN works in the Atlas API for a title with a specific phrase.
        test_title_query = "%Ashes of Chaos%"
        bulk_metadata = await client.get_bulk_metadata(title_ilike=test_title_query, limit=5)
        print(f"FFN Bulk Metadata (search query: '{test_title_query}')")
        print("\n".join(f"    {fic.id}: {fic.title}\n        {fic.description}" for fic in bulk_metadata), "\n")

        # Get the metadata for a specific work.
        test_url_1 = "https://www.fanfiction.net/s/13912800/1/Magical-Marvel"
        ffn_id = atlas_api.extract_fic_id(test_url_1)
        assert ffn_id
        print(f"{ffn_id=}")
        story_metadata = await client.get_story_metadata(ffn_id)
        print(f"Story Metadata (link: '{test_url_1}')")
        print(f"    {story_metadata.id}: {story_metadata.title}\n        {story_metadata.description}", "\n")

        # Get the metadata for another specific work.
        test_url_2 = "https://www.fanfiction.net/s/14182918/1/"
        ffn_id = atlas_api.extract_fic_id(test_url_2)
        assert ffn_id
        print(f"{ffn_id=}")
        story_metadata2 = await client.get_story_metadata(ffn_id)
        print(f"Story Metadata 2 (link: '{test_url_2}')")
        print(f"    {story_metadata2.id}: {story_metadata2.title}\n        {story_metadata2.description}", "\n")

    print("Exiting now...")
    await asyncio.sleep(0.25)


if __name__ == "__main__":
    asyncio.run(test())
