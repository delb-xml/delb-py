from types import SimpleNamespace

from _delb.plugins import plugin_manager


@plugin_manager.register_document_mixin
class TestDocumentExtension:
    @classmethod
    def _init_config(cls, config, kwargs):
        config.test = SimpleNamespace(
            initialized=True, property=kwargs.pop("test_property", None)
        )
        super()._init_config(config, kwargs)
