import os
import socket
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD

from protocol import (
    CHUNK_SIZE,
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    format_size,
    format_speed,
    recv_json,
    send_json,
)
from codelogic import QuanlyUpload

MAX_WORKERS = 3  

def upload_file(path, host, port, on_update):
    """
    Upload 1 file = 1 kết nối TCP.
    on_update(state, percent, speed, message) -> cập nhật GUI
    """
    name = os.path.basename(path)
    size = os.path.getsize(path)
    sock = None

    try:
        on_update("UPLOADING", 0, 0, "")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(DEFAULT_TIMEOUT)
        sock.connect((host, port))

        send_json(sock, {"filename": name, "filesize": size})
        reply = recv_json(sock)
        if reply.get("status") != "OK":
            raise Exception(reply.get("message", "Server từ chối"))

        sent = 0
        last_sent = 0
        last_t = time.time()

        f = open(path, "rb")
        try:
            while sent < size:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                sock.sendall(chunk)
                sent += len(chunk)

                now = time.time()
                if now - last_t >= 0.2 or sent >= size:
                    if now > last_t:
                        speed = (sent - last_sent) / (now - last_t)
                    else:
                        speed = 0
                    if size > 0:
                        percent = sent * 100.0 / size
                    else:
                        percent = 100
                    on_update("UPLOADING", percent, speed, "")
                    last_sent = sent
                    last_t = now
        finally:
            f.close()

        result = recv_json(sock)
        if result.get("status") != "SUCCESS":
            raise Exception(result.get("message", "Upload không thành công"))

        saved = result.get("saved_as", name)
        on_update("COMPLETED", 100, 0, saved)

    except Exception as e:
        on_update("ERROR", 0, 0, str(e))

    finally:
        if sock is not None:
            sock.close()


class App:
    def __init__(self):
        self.root = TkinterDnD.Tk()
        self.root.title("File Upload Client")
        self.root.geometry("850x550")

        self.host_var = tk.StringVar(value="127.0.0.1")
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        self.status_var = tk.StringVar(value="Chưa kết nối")

        # Sử dụng QuanlyUpload để quản lý hàng đợi
        self.upload_manager = QuanlyUpload(so_file_toi_da=MAX_WORKERS)
        self.file_infos = []  # Lưu thông tin các file để cập nhật GUI
        self.lock = threading.Lock()

        self.build_ui()

    def build_ui(self):
        top = ttk.LabelFrame(self.root, text="Cau hinh mang", padding=8)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Label(top, text="IP Server:").pack(side="left")
        ttk.Entry(top, textvariable=self.host_var, width=18).pack(side="left", padx=5)
        ttk.Label(top, text="Port:").pack(side="left")
        ttk.Entry(top, textvariable=self.port_var, width=8).pack(side="left", padx=5)
        ttk.Button(top, text="Connect / Check", command=self.check_connect).pack(
            side="left", padx=8
        )
        ttk.Label(top, textvariable=self.status_var).pack(side="left", padx=5)

        mid = ttk.LabelFrame(self.root, text="Them file", padding=8)
        mid.pack(fill="x", padx=10, pady=4)

        self.drop = tk.Label(
            mid,
            text="Bấm nút bên dưới để chọn nhiều file upload",
            height=3,
            relief="ridge",
            bd=2,
            bg="#f5f5f5",
        )
        self.drop.pack(fill="x")

        self.drop.drop_target_register(DND_FILES)
        self.drop.dnd_bind("<<Drop>>", self.on_drop)

        self.drop.dnd_bind("<<DragEnter>>", self.on_drag_enter)
        self.drop.dnd_bind("<<DragLeave>>", self.on_drag_leave)

        btns = ttk.Frame(mid)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Chọn file...", command=self.chon_file).pack(side="left")

        bot = ttk.LabelFrame(self.root, text="Danh sach file", padding=8)
        bot.pack(fill="both", expand=True, padx=10, pady=8)

        cols = ("name", "size", "state", "progress", "speed")
        self.tree = ttk.Treeview(bot, columns=cols, show="headings", height=12)
        self.tree.heading("name", text="Ten file")
        self.tree.heading("size", text="Kich thuoc")
        self.tree.heading("state", text="Trang thai")
        self.tree.heading("progress", text="Tien do")
        self.tree.heading("speed", text="Toc do")

        self.tree.column("name", width=260)
        self.tree.column("size", width=90)
        self.tree.column("state", width=100)
        self.tree.column("progress", width=100)
        self.tree.column("speed", width=100)
        self.tree.pack(fill="both", expand=True)

        ttk.Label(
            self.root,
            text="Tôi đã upload {} file đồng thời | mỗi file = 1 TCP".format(MAX_WORKERS),
        ).pack(anchor="w", padx=12, pady=4)

    def check_connect(self):
        host = self.host_var.get().strip()
        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            messagebox.showerror("Loi", "Port không hợp lệ")
            return

        def probe():
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(DEFAULT_TIMEOUT)
            try:
                s.connect((host, port))
                msg = "OK: {}:{}".format(host, port)
            except Exception as e:
                msg = "Loi: {}".format(e)
            finally:
                s.close()

            def set_msg():
                self.status_var.set(msg)

            self.root.after(0, set_msg)

        self.status_var.set("Dang kiem tra...")
        t = threading.Thread(target=probe)
        t.daemon = True
        t.start()

    def on_drag_enter(self, event):
        self.drop.config(bg="#e0f0ff")
        return event.action

    def on_drag_leave(self, event):
        self.drop.config(
            text="Kéo và thả file vào đây\nhoặc bấm nút bên dưới để chọn nhiều file",
            bg="#f5f5f5",
        )

    def on_drop(self, event):
        self.drop.config(
            text="Kéo và thả file vào đây\nhoặc bấm nút bên dưới để chọn nhiều file",
            bg="#f5f5f5",
        )
        paths = self.root.tk.splitlist(event.data)

        if paths:
            self.add_files(paths)
    
    def chon_file(self):
        paths = filedialog.askopenfilenames()
        if paths:
            self.add_files(paths)

    def add_files(self, paths):
        """Thêm file vào danh sách và hàng đợi"""
        host = self.host_var.get().strip()
        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            messagebox.showerror("Loi", "Port không hợp lệ")
            return

        for path in paths:
            path = os.path.normpath(path)
            if not os.path.isfile(path):
                continue

            info = {
                "path": path,
                "name": os.path.basename(path),
                "size": os.path.getsize(path),
                "state": "PENDING",
                "row": None,
            }
            
            
            row = self.tree.insert(
                "",
                "end",
                values=(
                    info["name"],
                    format_size(info["size"]),
                    "PENDING",
                    "0%",
                    "-",
                ),
            )
            info["row"] = row
            self.file_infos.append(info)
            
            self.upload_manager.add_file(info)

        self.start_uploads(host, port)

    def update_row(self, info, state, percent, speed, message):
        """Cập nhật dòng trong Treeview"""
        info["state"] = state
        name = info["name"]
        if state == "COMPLETED" and message and message != name:
            name = info["name"] + " -> " + message
        if state == "ERROR" and message:
            name = info["name"] + " (" + message[:35] + ")"

        if speed > 0:
            speed_text = format_speed(speed)
        else:
            speed_text = "-"

        self.tree.item(
            info["row"],
            values=(
                name,
                format_size(info["size"]),
                state,
                "{:.0f}%".format(percent),
                speed_text,
            ),
        )

    def start_uploads(self, host, port):
        """Khởi động upload cho các file đang chờ trong hàng đợi"""
        self.lock.acquire()
        try:
        
            while (len(self.upload_manager.uploading) < self.upload_manager.so_file_toi_da 
                   and len(self.upload_manager.queue) > 0):
                
                
                info = self.upload_manager.queue.popleft()
                self.upload_manager.uploading.append(info)
                
            
                info["state"] = "UPLOADING"
                self.update_row(info, "UPLOADING", 0, 0, "")
                
              
                t = threading.Thread(target=self.worker, args=(info, host, port))
                t.daemon = True
                t.start()
        finally:
            self.lock.release()

    def worker(self, info, host, port):
        """Worker thread upload một file"""
        def on_update(state, percent, speed, message):
            def do_update(s=state, p=percent, sp=speed, m=message):
                self.update_row(info, s, p, sp, m)
                
                if s == "COMPLETED":
                    if info in self.upload_manager.uploading:
                        self.upload_manager.uploading.remove(info)
                    self.upload_manager.completed.append(info)
                elif s == "ERROR":
                    if info in self.upload_manager.uploading:
                        self.upload_manager.uploading.remove(info)
                    self.upload_manager.failed.append(info)
                    
               
                if s in ["COMPLETED", "ERROR"]:
                    self.root.after(0, lambda: self.start_uploads(host, port))
                    
            self.root.after(0, do_update)

       
        upload_file(info["path"], host, port, on_update)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
