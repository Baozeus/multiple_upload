import argparse
import os
import socket
import threading
import traceback

from protocol import (
    CHUNK_SIZE,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    is_health_check,
    recv_exact,
    recv_json,
    send_json,
    validate_conflict_policy,
    validate_upload_header,
)
from duplicate_handler import abort_reserved_file, reserve_file_path
from upload_handler import save_reserved_file


UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")


class FileUploadServer:
    def __init__(self, host, port, upload_dir, max_concurrent=3):
        self.host = host
        self.port = port
        self.upload_dir = upload_dir
        self.sock = None
        self.running = True
        if max_concurrent < 1:
            raise ValueError("max_concurrent phai >= 1")
        self.max_concurrent = max_concurrent
        self.upload_limit = threading.BoundedSemaphore(max_concurrent)
        self._activity_lock = threading.Lock()
        self._active_uploads = 0
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)

    def on_chunk_received(self, filename, received, total):
        """No-op extension point used by deterministic slow/failure test servers."""

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(32)
        self.sock.settimeout(1.0)

        print("[SERVER] Listening on {}:{}".format(self.host, self.port))
        print("[SERVER] Lưu file vào: " + os.path.abspath(self.upload_dir))
        print("[SERVER] Bấm Ctrl+C để dừng.")

        try:
            while self.running:
                try:
                    conn, addr = self.sock.accept()
                except socket.timeout:
                    continue
                t = threading.Thread(target=self.handle_client, args=(conn, addr))
                t.daemon = True
                t.start()
        except KeyboardInterrupt:
            print("\n[SERVER] Dang tat...")
        finally:
            self.running = False
            if self.sock:
                self.sock.close()

    def handle_client(self, conn, addr):
        peer = "{}:{}".format(addr[0], addr[1])
        print("[SERVER] Connected: " + peer)
        permit_acquired = False
        reservation = None
        try:
            conn.settimeout(DEFAULT_TIMEOUT)

            try:
                header = recv_json(conn)
            except Exception as e:
                send_json(conn, {"status": "ERROR", "message": "Header loi: " + str(e)})
                return

            if is_health_check(header):
                with self._activity_lock:
                    active_uploads = self._active_uploads
                send_json(conn, {
                    "status": "HEALTHY",
                    "protocol": PROTOCOL_NAME,
                    "version": PROTOCOL_VERSION,
                    "can_accept_upload": active_uploads < self.max_concurrent,
                    "active_uploads": active_uploads,
                    "upload_limit": self.max_concurrent,
                })
                return

            try:
                filename, filesize = validate_upload_header(header)
                conflict = validate_conflict_policy(header)
            except ValueError as e:
                send_json(conn, {"status": "ERROR", "message": str(e)})
                print("[SERVER] Tu choi {}: {}".format(peer, e))
                return

            if not self.upload_limit.acquire(blocking=False):
                send_json(conn, {
                    "status": "REJECTED",
                    "message": "Server đã đủ {} file đang upload.".format(
                        self.max_concurrent
                    ),
                })
                return
            permit_acquired = True
            with self._activity_lock:
                self._active_uploads += 1

            reservation = reserve_file_path(
                self.upload_dir, filename, conflict=conflict
            )
            if reservation is None:
                status = "DUPLICATE" if conflict == "ask" else "SKIPPED"
                send_json(conn, {
                    "status": status,
                    "saved_as": filename,
                    "message": "Tệp đã tồn tại trên Server",
                })
                print("[SERVER] {} {}: {}".format(status, peer, filename))
                return

            send_json(conn, {
                "status": "OK",
                "saved_as": reservation["final_name"],
            })
            print("[SERVER] Nhan '{}' ({} byte)".format(filename, filesize))
            
            
            def data_stream():
                received = 0
                while received < filesize:
                    to_read = min(CHUNK_SIZE, filesize - received)
                    chunk = recv_exact(conn, to_read)
                    if chunk:
                        received += len(chunk)
                        self.on_chunk_received(filename, received, filesize)
                        yield chunk
                    else:
                        break
            
            
            try:
                owned_reservation = reservation
                reservation = None
                result = save_reserved_file(owned_reservation, data_stream())
                send_json(conn, {
                    "status": "SUCCESS",
                    "saved_as": result["final_name"],
                    "bytes": result["bytes_written"],
                })
                print("[SERVER] OK {}: luu {} ({} byte)".format(
                    peer, result["final_name"], result["bytes_written"]
                ))
                
            except Exception as e:
                print("[SERVER] ERROR {}: {}".format(peer, e))
                if not isinstance(e, (ConnectionError, socket.timeout)):
                    traceback.print_exc()
                send_json(conn, {"status": "ERROR", "message": str(e)})

        except Exception as e:
            print("[SERVER] ERROR {}: {}".format(peer, e))
            traceback.print_exc()
            try:
                send_json(conn, {"status": "ERROR", "message": str(e)})
            except Exception:
                pass

        finally:
            if reservation is not None:
                abort_reserved_file(reservation)
            if permit_acquired:
                with self._activity_lock:
                    self._active_uploads -= 1
                self.upload_limit.release()
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conn.close()
            print("[SERVER] Closed: " + peer)


def main():
    parser = argparse.ArgumentParser(description="File upload server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--dir", default=UPLOAD_DIR)
    args = parser.parse_args()

    if args.port < 1 or args.port > 65535:
        print("Port phai trong khoang 1-65535")
        return

    server = FileUploadServer(args.host, args.port, args.dir)
    server.start()


if __name__ == "__main__":
    main()
