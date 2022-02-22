"""
The genesis of this module was as follows:

- tokenize._tokenize was copied from CPython 3.10.2's standard lib and named `tokenize`
- all apparent Python source code specifics were remove from `tokenize`
- objects used within `tokenize` were copied into this module

"""

import re
from functools import lru_cache
from token import ENDMARKER, ERRORTOKEN, EXACT_TOKEN_TYPES, NAME, NUMBER, OP, STRING
from tokenize import TokenInfo

# patterns


@lru_cache
def _compile(expr):
    return re.compile(expr, re.UNICODE)


def _group(*choices):
    return "(" + "|".join(choices) + ")"


EXACT_TOKEN_TYPES = EXACT_TOKEN_TYPES.copy()


Name = r"\w+((-\w+)*\w+)?"
Decnumber = r"[0-9]+"
Special = _group(*map(re.escape, sorted(EXACT_TOKEN_TYPES, reverse=True)))
Whitespace = r"[ \f\t]*"

# FIXME plain Strings are missing
PseudoToken = Whitespace + _group(Decnumber, Special, Name)


#


def tokenize(expression: str):
    numchars = "0123456789"
    pos, _max = 0, len(expression)

    if not expression:
        raise RuntimeError  # TODO

    while pos < _max:
        pseudomatch = _compile(PseudoToken).match(expression, pos)
        if pseudomatch:  # scan for tokens
            start, end = pseudomatch.span(1)
            spos, epos, pos = (0, start), (0, end), end
            if start == end:
                continue
            token, initial = expression[start:end], expression[start]

            if initial in numchars:
                yield TokenInfo(NUMBER, token, spos, epos, 0)

            elif initial in ("'", '"'):
                yield TokenInfo(STRING, token, spos, epos, 0)

            # TODO also kebab-case
            elif initial.isidentifier():
                yield TokenInfo(NAME, token, spos, epos, 0)

            else:
                yield TokenInfo(OP, token, spos, epos, 0)

        else:
            yield TokenInfo(ERRORTOKEN, expression[pos], (0, pos), (0, pos + 1), 0)
            pos += 1

    yield TokenInfo(ENDMARKER, "", (0, 0), (0, 0), "")
