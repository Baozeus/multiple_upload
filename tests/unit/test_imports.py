from __future__ import annotations

import importlib
import unittest


class ImportTests(unittest.TestCase):
    def test_core_modules_import_without_optional_runtime_connections(self) -> None:
        modules = (
            "udm10",
            "udm10.client",
            "udm10.client.application",
            "udm10.server",
            "udm10.server.application",
            "udm10.domain",
            "udm10.protocol",
            "udm10.persistence",
            "udm10.config",
            "udm10.utils",
            "run_client",
            "run_server",
        )
        for module_name in modules:
            with self.subTest(module=module_name):
                importlib.import_module(module_name)
