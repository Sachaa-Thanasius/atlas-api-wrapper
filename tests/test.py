"""
test.py: A small "test" for the Atlas API wrapper.
"""

import asyncio
import json

from src.atlas_api import AtlasAPI


with open("../config.json", encoding="utf-8") as f:
    info = json.load(f)
atlas_auth = tuple(info["atlas"])  # Or atlas_auth = ("login", "password")


async def test():
    """Tests the Atlas API wrapper with different queries.

    TODO: Make actual unit tests.
    """

    print("-----------------Atlas Testing-----------------")

    ffn_test_url_1 = "https://www.fanfiction.net/s/13912800/1/Magical-Marvel"
    ffn_test_url_2 = "https://www.fanfiction.net/s/14182918/7/6"

    atlas = AtlasAPI(auth=atlas_auth)
    print("Set up Atlas connection.")

    max_update_id = await atlas.max_update_id()
    print(f"Max Update ID: {max_update_id}")

    max_ffn_story_id = await atlas.max_story_id()
    print(f"Max FFN ID: {max_ffn_story_id}")

    bulk_metadata = await atlas.get_bulk_metadata(title_ilike="%Ashes of Chaos", limit=5)
    print(f"FFN Bulk Metadata:")
    for fic in bulk_metadata:
        print(f"    {fic.id}: {fic.title}")
        print(f"        {fic.description}")

    story_metadata = await atlas.get_story_metadata(atlas.extract_fic_id(ffn_test_url_1))
    print(f"FFN Specific Metadata:")
    print(f"    {story_metadata.id}: {story_metadata.title}")
    print(f"        {story_metadata.description}")

    story_metadata2 = await atlas.get_story_metadata(atlas.extract_fic_id(ffn_test_url_2))
    print(f"FFN Specific Metadata 2:")
    print(f"    {story_metadata2.id}: {story_metadata2.title}")
    print(f"        {story_metadata2.description}")

    print("Exiting now...")
    await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(test())
