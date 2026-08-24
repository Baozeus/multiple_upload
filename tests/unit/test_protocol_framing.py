from __future__ import annotations

import socket
import unittest

from udm10.protocol import ProtocolError, receive_message, send_message


class ProtocolFramingTests(unittest.TestCase):
    def test_round_trip_preserves_vietnamese_unicode(self) -> None:
        sender, receiver = socket.socketpair()
        self.addCleanup(sender.close)
        self.addCleanup(receiver.close)

        send_message(sender, {"type": "health.check", "label": "Kiểm tra"})

        self.assertEqual(
            receive_message(receiver),
            {"type": "health.check", "label": "Kiểm tra"},
        )

    def test_rejects_payload_over_configured_limit(self) -> None:
        sender, receiver = socket.socketpair()
        self.addCleanup(sender.close)
        self.addCleanup(receiver.close)

        with self.assertRaises(ProtocolError):
            send_message(sender, {"data": "x" * 32}, max_payload_bytes=8)
