"""Token counting with the same tokenizer family as the reader (o200k for gpt-4o-mini / gpt-4.1-mini)."""

from functools import lru_cache

import tiktoken


@lru_cache(maxsize=1)
def _enc():
    return tiktoken.get_encoding("o200k_base")


def count_tokens(text: str) -> int:
    return len(_enc().encode(text, disallowed_special=()))  # treat "<|endoftext|>" etc. in data as plain text
