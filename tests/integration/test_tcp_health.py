from __future__ import annotations

import socket
import threading
import unittest

from udm10.config import TcpSettings
from udm10.protocol import receive_message, send_message
from udm10.server import create_server


class TcpHealthIntegrationTests(unittest.TestCase):
    def test_server_answers_health_check(self) -> None:
        settings = TcpSettings(
            bind_host="127.0.0.1",
            client_host="127.0.0.1",
            port=0,
            max_control_message_bytes=1024,
        )
        server = create_server(settings)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        with socket.create_connection(server.server_address, timeout=2) as connection:
            send_message(connection, {"type": "health.check"})
            response = receive_message(connection)

        self.assertEqual(response["type"], "health.ok")
        self.assertEqual(response["service"], "udm10-server")
