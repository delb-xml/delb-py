from types import SimpleNamespace

from _delb.plugins import plugin_manager
from _delb.xpath import EvaluationContext


@plugin_manager.register_document_mixin
class TestDocumentExtension:
    @classmethod
    def _init_config(cls, config, kwargs):
        config.test = SimpleNamespace(
            initialized=True, property=kwargs.pop("test_property", None)
        )
        super()._init_config(config, kwargs)


@plugin_manager.register_xpath_function("is-last")
def is_last(context: EvaluationContext) -> bool:
    return context.position == context.size


@plugin_manager.register_xpath_function
def lowercase(_, string: str) -> str:
    return string.lower()
