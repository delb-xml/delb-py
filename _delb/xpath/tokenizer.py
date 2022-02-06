from enum import Enum
from functools import lru_cache
from typing import NamedTuple, Sequence


TokenType = Enum("TokenType", "TODO")


class Token(NamedTuple):
    index: int
    string: str
    type: TokenType


@lru_cache(64)  # TODO? configurable
def tokenize(expression: str) -> Sequence[Token]:
    raise NotImplementedError


__all__ = (tokenize.__name__,)
