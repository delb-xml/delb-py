# Copyright (C) 2018-'22  Frank Sachsenheim
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import operator
from functools import lru_cache
from typing import Iterator, List, Optional, Sequence, Union

from _delb.exceptions import XPathParsingError, XPathUnsupportedStandardFeature
from _delb.xpath.ast import (
    AnyValue,
    AttributeValue,
    Axis,
    BooleanOperator,
    EvaluationNode,
    Function,
    HasAttribute,
    LocationPath,
    LocationStep,
    NameMatchTest,
    NameStartTest,
    NodeTestNode,
    NodeTypeTest,
    ProcessingInstructionTest,
    XPathExpression,
)
from _delb.xpath.tokenizer import COMPLEMENTING_TOKEN_TYPES, TokenType, tokenize, Token


# TODO employ when released: https://github.com/python/mypy/pull/13297
TokenTree = Sequence[Union[Token, "TokenTree"]]  # type: ignore


NODE_TYPE_TEST_MAPPING = {
    "comment": "CommentNode",
    "node": "TagNode",
    "processing-instruction": "ProcessingInstructionNode",
    "text": "TextNode",
}
OPERATORS = {
    "<=": operator.le,
    "<": operator.lt,
    ">=": operator.ge,
    ">": operator.gt,
    "=": operator.eq,
    "!=": operator.ne,
    "and": operator.and_,
    "or": operator.or_,
}


def expand_axes(tokens: TokenTree) -> TokenTree:
    result: List[Token] = []

    for token in tokens:
        if isinstance(token, Token):
            if token.type is TokenType.SLASH_SLASH:
                result.extend(
                    (
                        Token(token.position, "/", TokenType.SLASH),
                        Token(token.position, "descendant-or-self", TokenType.NAME),
                        Token(token.position, "::", TokenType.AXIS_SEPARATOR),
                        Token(token.position, "node", TokenType.NAME),
                        Token(token.position, "(", TokenType.OPEN_PARENS),
                        Token(token.position, ")", TokenType.CLOSE_PARENS),
                        Token(token.position, "/", TokenType.SLASH),
                    )
                )
                continue
            if token.type is TokenType.DOT:
                result.extend(
                    (
                        Token(token.position, "self", TokenType.NAME),
                        Token(token.position, "::", TokenType.AXIS_SEPARATOR),
                        Token(token.position, "node", TokenType.NAME),
                        Token(token.position, "(", TokenType.OPEN_PARENS),
                        Token(token.position, ")", TokenType.CLOSE_PARENS),
                    )
                )
                continue
            if token.type is TokenType.DOT_DOT:
                result.extend(
                    (
                        Token(token.position, "parent", TokenType.NAME),
                        Token(token.position, "::", TokenType.AXIS_SEPARATOR),
                        Token(token.position, "node", TokenType.NAME),
                        Token(token.position, "(", TokenType.OPEN_PARENS),
                        Token(token.position, ")", TokenType.CLOSE_PARENS),
                    )
                )
                continue
        result.append(token)

    return result


def group_enclosed_expressions(tokens: TokenTree) -> TokenTree:
    result = []
    openers = []

    for i, token in enumerate(tokens):

        if token.type in (TokenType.OPEN_BRACKET, TokenType.OPEN_PARENS):
            openers.append((i, token))

        elif token.type in (TokenType.CLOSE_BRACKET, TokenType.CLOSE_PARENS):
            start_pos, start_token = openers.pop()

            if token.type is not COMPLEMENTING_TOKEN_TYPES[start_token.type]:
                raise XPathParsingError(
                    position=token.position,
                    message=f"Closing `{token.string}` doesn't match opening "
                    f"`{start_token.string}` at position {start_token.position}.",
                )

            if not openers:
                contents = group_enclosed_expressions(tokens[start_pos + 1 : i])
                if contents:
                    result.extend(
                        [
                            start_token,
                            contents,
                            token,
                        ]
                    )
                else:
                    result.extend((start_token, token))

        elif not openers:
            result.append(token)

    if openers:
        token = openers[-1][1]
        raise XPathParsingError(
            position=token.position, message=f"`{token.string}` is never closed."
        )

    return result


def parse_location_path(tokens: TokenTree) -> LocationPath:
    if not tokens:
        raise XPathParsingError(message="Missing location path.")

    tokens = expand_axes(tokens)
    absolute = tokens[0].type is TokenType.SLASH

    return LocationPath(
        [
            parse_location_step(x)
            for x in partition_tokens(
                TokenType.SLASH,
                tokens,
            )
        ],
        absolute=absolute,
    )


def parse_location_step(tokens: TokenTree) -> LocationStep:  # noqa: C901
    def start_matches(*pattern: Optional[TokenType]) -> bool:
        return len(tokens) >= len(pattern) and all(
            x.type is y for x, y in zip(tokens, pattern) if y is not None
        )

    node_test: NodeTestNode
    all_tokens = tuple(tokens)

    # axis

    if start_matches(TokenType.NAME, TokenType.AXIS_SEPARATOR):
        try:
            axis = Axis(tokens[0].string)
        except XPathParsingError as e:
            e.position = tokens[0].position
            raise e
        tokens = tokens[2:]
    else:
        axis = Axis("child")

    if not tokens:
        last_token = all_tokens[-1]
        raise XPathParsingError(
            message="Missing node test.",
            position=last_token.position + len(last_token.string),
        )

    # name test's prefix

    if start_matches(TokenType.NAME, TokenType.COLON, TokenType.NAME):
        prefix = tokens[0].string
        tokens = tokens[2:]
    else:
        prefix = None

    # node test

    if start_matches(
        TokenType.NAME, TokenType.OPEN_PARENS, None, TokenType.CLOSE_PARENS
    ):
        assert tokens[0].string == "processing-instruction"
        target_name = tokens[2][0]
        assert isinstance(target_name, Token)
        node_test = ProcessingInstructionTest(target_name.string[1:-1])
        tokens = tokens[4:]

    elif start_matches(TokenType.NAME, TokenType.OPEN_PARENS, TokenType.CLOSE_PARENS):
        node_test = NodeTypeTest(NODE_TYPE_TEST_MAPPING[tokens[0].string])
        tokens = tokens[3:]

    elif start_matches(TokenType.NAME, TokenType.ASTERISK):
        node_test = NameStartTest(prefix, tokens[0].string)
        tokens = tokens[2:]

    elif start_matches(TokenType.ASTERISK):
        node_test = NameStartTest(prefix, "")
        tokens = tokens[1:]

    elif start_matches(TokenType.NAME):
        node_test = NameMatchTest(prefix, tokens[0].string)
        tokens = tokens[1:]

    # other

    elif start_matches(TokenType.STRUDEL, TokenType.NAME):
        raise XPathUnsupportedStandardFeature(
            position=tokens[0].position,
            feature_description="Attribute lookup",
        )

    else:
        raise XPathParsingError(
            message="Unrecognized node test.", position=tokens[0].position
        )

    # predicates

    predicates = []
    while tokens:
        if start_matches(TokenType.OPEN_BRACKET, None, TokenType.CLOSE_BRACKET):
            predicate = parse_evaluation_expression(tokens[1])
            if isinstance(predicate, AnyValue) and isinstance(predicate.value, int):
                predicate = BooleanOperator(
                    OPERATORS["="], Function("position", ()), predicate
                )
            predicates.append(predicate)
            tokens = tokens[3:]
        else:
            raise XPathParsingError(
                position=tokens[-1].position, message="Unrecognized expression."
            )

    return LocationStep(axis=axis, node_test=node_test, predicates=predicates)


def parse_evaluation_expression(tokens: TokenTree) -> EvaluationNode:  # noqa: C901
    def all_matches(*pattern: Optional[TokenType]) -> bool:
        return len(pattern) == token_count and all(
            x.type is y for x, y in zip(tokens, pattern) if y is not None
        )

    token_count = len(tokens)

    if all_matches(TokenType.NUMBER):
        return AnyValue(int(tokens[0].string))

    if all_matches(TokenType.STRING):
        return AnyValue(tokens[0].string[1:-1])

    if all_matches(TokenType.STRUDEL, TokenType.NAME):
        return HasAttribute(prefix=None, local_name=tokens[1].string)

    if all_matches(TokenType.STRUDEL, TokenType.NAME, TokenType.COLON, TokenType.NAME):
        return HasAttribute(prefix=tokens[1].string, local_name=tokens[3].string)

    if all_matches(TokenType.NAME, TokenType.OPEN_PARENS, None, TokenType.CLOSE_PARENS):
        arguments: List[EvaluationNode] = []
        for argument in (
            parse_evaluation_expression(x)
            for x in partition_tokens(TokenType.COMMA, tokens[2])
        ):
            if isinstance(argument, HasAttribute):
                arguments.append(
                    AttributeValue(prefix=argument.prefix, name=argument.local_name)
                )
            else:
                arguments.append(argument)
        try:
            return Function(tokens[0].string, arguments)
        except XPathParsingError as e:
            e.position = tokens[0].position
            raise e

    if all_matches(TokenType.NAME, TokenType.OPEN_PARENS, TokenType.CLOSE_PARENS):
        return Function(tokens[0].string, ())

    if all_matches(TokenType.OPEN_PARENS, None, TokenType.CLOSE_PARENS):
        return parse_evaluation_expression(tokens[1])

    for _operator in (
        (TokenType.NAME, "or"),
        (TokenType.NAME, "and"),
        (TokenType.OTHER_OPS, "="),
        (TokenType.OTHER_OPS, "!="),
        (TokenType.OTHER_OPS, "<="),
        (TokenType.OTHER_OPS, "<"),
        (TokenType.OTHER_OPS, ">="),
        (TokenType.OTHER_OPS, ">"),
    ):
        for i, token in enumerate(tokens):
            if not isinstance(token, Token):
                assert isinstance(token, list)
                continue

            if (token.type, token.string) == _operator:
                assert 0 < i < len(tokens) - 1
                left = parse_evaluation_expression(tokens[:i])
                right = parse_evaluation_expression(tokens[i + 1 :])

                if token.string not in ("and", "or"):
                    if isinstance(left, HasAttribute):
                        left = AttributeValue(left.prefix, left.local_name)
                    if isinstance(right, HasAttribute):
                        right = AttributeValue(right.prefix, right.local_name)

                return BooleanOperator(
                    OPERATORS[token.string],
                    left,
                    right,
                )

    raise XPathParsingError(
        position=tokens[0].position, message="Unrecognized predicate expression."
    )


def partition_tokens(
    separator: TokenType,
    tokens: TokenTree,
) -> Iterator[Sequence[Union[Token, TokenTree]]]:
    current_partition: List[Union[Token, TokenTree]] = []

    for token in tokens:
        if isinstance(token, Token) and token.type is separator:
            if current_partition:
                yield current_partition
                current_partition = []
        else:
            current_partition.append(token)

    yield current_partition


@lru_cache(64)  # TODO? configurable
def parse(expression: str) -> XPathExpression:
    try:
        tokens = group_enclosed_expressions(tokenize(expression))
        if TokenType.PASEQ in (x.type for x in tokens if isinstance(x, Token)):
            return XPathExpression(
                [
                    parse_location_path(x)
                    for x in partition_tokens(TokenType.PASEQ, tokens)
                ]
            )
        else:
            return XPathExpression([parse_location_path(tokens)])
    except XPathParsingError as e:
        e.expression = expression
        if e.position is None:
            e.position = 0
        raise e


__all__ = (parse.__name__,)  # type: ignore
