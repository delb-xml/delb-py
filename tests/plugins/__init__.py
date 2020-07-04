from types import SimpleNamespace

from _delb.plugins import plugin_manager


@plugin_manager.register_document_extension
class TestDocumentExtension:
    def _init_config(self, config):
        self.config.test = SimpleNamespace(
            initialized=True, property=config.pop("test_property", None)
        )
        super()._init_config(config)
