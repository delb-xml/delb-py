from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Union

if TYPE_CHECKING:
    from _delb.xpath.ast import EvaluationContext


xpath_functions = {}


def register_xpath_function(arg: Union[Callable, str]) -> Callable:
    if isinstance(arg, str):

        def wrapper(func):
            xpath_functions[arg] = func
            return func

        return wrapper

    if callable(arg):
        xpath_functions[arg.__name__] = arg
        return arg


@register_xpath_function
def concat(*strings: str) -> str:
    return "".join(strings)


@register_xpath_function
def contains(_, string: str, substring: str) -> bool:
    return substring in string


@register_xpath_function
def boolean(_, value: Any) -> bool:
    return bool(value)


@register_xpath_function
def last(context: EvaluationContext) -> int:
    return context.size


@register_xpath_function("not")
def _not(_, value: Any) -> bool:
    return not value


@register_xpath_function
def position(context: EvaluationContext) -> int:
    return context.position


@register_xpath_function("starts-with")
def starts_with(_, string: str, prefix: str) -> bool:
    return string.startswith(prefix)
