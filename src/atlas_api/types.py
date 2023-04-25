from typing import TypedDict


class StoryMetadata(TypedDict):
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
