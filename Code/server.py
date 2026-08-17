import argparse
import os
import socket
import threading
import traceback

from protocol import (
    CHUNK_SIZE,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    recv_exact,
    recv_json,
    send_json,
    unique_path,
    validate_upload_header,
)


class FileUploadServer:
    def __init__(self, host, port, upload_dir):
        self.host = host
        self.port = port
        self.upload_dir = upload_dir
        self.sock = None
        self.running = True
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)

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
        temp_path = None
        peer = "{}:{}".format(addr[0], addr[1])
        print("[SERVER] Connected: " + peer)

        try:
            conn.settimeout(DEFAULT_TIMEOUT)
            try:
                header = recv_json(conn)
            except Exception as e:
                send_json(conn, {"status": "ERROR", "message": "Header loi: " + str(e)})
                return

            try:
                filename, filesize = validate_upload_header(header)
            except ValueError as e:
                send_json(conn, {"status": "ERROR", "message": str(e)})
                print("[SERVER] Tu choi {}: {}".format(peer, e))
                return

            final_path = unique_path(self.upload_dir, filename)
            saved_name = os.path.basename(final_path)
            temp_path = final_path + ".part"

            send_json(conn, {"status": "OK", "saved_as": saved_name})
            print("[SERVER] Nhan '{}' ({} byte) -> {}".format(
                filename, filesize, saved_name
            ))
            received = 0
            out = open(temp_path, "wb")
            try:
                while received < filesize:
                    to_read = min(CHUNK_SIZE, filesize - received)
                    chunk = recv_exact(conn, to_read)
                    out.write(chunk)
                    received += len(chunk)
            finally:
                out.close()
            os.replace(temp_path, final_path)
            temp_path = None

            send_json(conn, {
                "status": "SUCCESS",
                "saved_as": saved_name,
                "bytes": received,
            })
            print("[SERVER] OK {}: luu {} ({} byte)".format(
                peer, saved_name, received
            ))

        except Exception as e:
            print("[SERVER] ERROR {}: {}".format(peer, e))
            traceback.print_exc()
            try:
                send_json(conn, {"status": "ERROR", "message": str(e)})
            except Exception:
                pass
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    print("[SERVER] Da xoa file tam: " + temp_path)
                except OSError:
                    pass
        finally:
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
    parser.add_argument("--dir", default="uploads")
    args = parser.parse_args()

    if args.port < 1 or args.port > 65535:
        print("Port phai trong khoang 1-65535")
        return

    server = FileUploadServer(args.host, args.port, args.dir)
    server.start()


if __name__ == "__main__":
    main()
