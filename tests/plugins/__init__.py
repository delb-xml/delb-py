from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

from _delb.plugins import plugin_manager, DocumentMixinBase

if TYPE_CHECKING:
    from _delb.xpath import EvaluationContext


class PlaygroundDocumentExtension(DocumentMixinBase):
    @classmethod
    def _init_config(cls, config, kwargs):
        config.playground = SimpleNamespace(
            initialized=True, property=kwargs.pop("playground_property", None)
        )
        super()._init_config(config, kwargs)

    def playground_method(self):
        return self.config.playground.property.replace("o", "0")


@plugin_manager.register_xpath_function("is-last")
def is_last(context: EvaluationContext) -> bool:
    return context.position == context.size


@plugin_manager.register_xpath_function
def lowercase(_, string: str) -> str:
    return string.lower()
