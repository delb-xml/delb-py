from types import SimpleNamespace

import pluggy


class TestDocumentExtension:
    def _init_config(self, config):
        self.config.test = SimpleNamespace(
            initialized=True, property=config.pop("test_property")
        )
        super()._init_config(config)


@pluggy.HookimplMarker("delb")
def get_document_extensions():
    return TestDocumentExtension
