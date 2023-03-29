"""
get_metadata_from_link.py: Get the metadata for a specific fic using its FFN url.
"""

import asyncio
import json

from aiohttp import ClientSession

from src.atlas_api.api import AtlasAPI


async def main():
    """Gets the metadata for one work of fanfic with its url."""

    test_link = "https://www.fanfiction.net/s/13912800/1/Magical-Marvel"
    print("Getting metadata from this link: ", test_link)

    async with ClientSession() as session:
        with open("../config.json", encoding="utf-8") as f:
            info = json.load(f)
        atlas_auth = tuple(info["atlas"])       # Or atlas_auth = ("login", "password")
        atlas = AtlasAPI(auth=atlas_auth, session=session)
        print("Set up Atlas connection.")

        atlas_ffn_spec_metadata = await atlas.get_story_metadata(atlas.extract_fic_id(test_link))
        print(f"FFN Specific Metadata:\n{atlas_ffn_spec_metadata}")

    print("Gracefully ending now...")
    await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
