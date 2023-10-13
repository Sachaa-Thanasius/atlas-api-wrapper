"""
get_metadata_from_link.py: Get the metadata for a specific fic using its FFN url.
"""

import asyncio
import json
import pathlib

import aiohttp

import atlas_api


# Import the authorization credentials from a config file.
# Note: This way of storing them isn't strictly necessary, but this wrapper doesn't come with the authorization 
# credentials.
with pathlib.Path("config.json").open(encoding="utf-8") as f:
    info = json.load(f)
atlas_auth = aiohttp.BasicAuth(*info.values())  # Or atlas_auth = aiohttp.BasicAuth(login="login", password="password")


async def get_metadata_from_link() -> None:
    """Gets the metadata for one FFN work with its url."""

    ffn_link = "https://www.fanfiction.net/s/13912800/1/Magical-Marvel"
    print(f"Getting metadata from this link: '{ffn_link}'")

    # Create a ClientSession in order to close it gracefully. Not strictly necessary, since the atlas client can create
    # its own session if it's used as an async context manager (i.e. async with).
    async with aiohttp.ClientSession() as session:
        client = atlas_api.Client(auth=atlas_auth, session=session)

        # Get the fic id (e.g. 14216823), then plug it into one of the client's get methods.
        ffn_id = atlas_api.extract_fic_id(ffn_link)
        assert ffn_id
        story_metadata = await client.get_story_metadata(ffn_id)
        print(f"FFN Specific Metadata:\n{story_metadata}")

    print("Exiting now...")
    await asyncio.sleep(0.25)


if __name__ == "__main__":
    asyncio.run(get_metadata_from_link())
