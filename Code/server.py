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
    validate_conflict_policy,
    validate_upload_header,
)
from upload_handler import save_incoming_file


UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")


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
                conflict = validate_conflict_policy(header)
            except ValueError as e:
                send_json(conn, {"status": "ERROR", "message": str(e)})
                print("[SERVER] Tu choi {}: {}".format(peer, e))
                return

            
            if conflict == "skip" and os.path.exists(
                os.path.join(self.upload_dir, filename)
            ):
                send_json(conn, {
                    "status": "SKIPPED",
                    "saved_as": filename,
                    "message": "Tệp đã tồn tại trên Server",
                })
                print("[SERVER] SKIP {}: {}".format(peer, filename))
                return

            send_json(conn, {"status": "OK", "saved_as": filename})
            print("[SERVER] Nhan '{}' ({} byte)".format(filename, filesize))
            
            
            def data_stream():
                received = 0
                while received < filesize:
                    to_read = min(CHUNK_SIZE, filesize - received)
                    chunk = recv_exact(conn, to_read)
                    if chunk:
                        received += len(chunk)
                        yield chunk
                    else:
                        break
            
            
            try:
                result = save_incoming_file(
                    self.upload_dir, filename, data_stream(), conflict=conflict
                )

                if result.get("skipped"):
                    send_json(conn, {
                        "status": "SKIPPED",
                        "saved_as": filename,
                        "message": "Tệp đã tồn tại trên Server",
                    })
                    return
                
                
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
