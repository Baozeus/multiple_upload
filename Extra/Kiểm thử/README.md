# Bộ kiểm thử QA mẫu

Runner này thực hiện kiểm thử qua các giao diện công khai của ứng dụng:

- UI PySide6 và tín hiệu kéo-thả tệp;
- TCP Client–Server trên `127.0.0.1`;
- file được Server lưu trên filesystem;
- stress/performance với hai mức tải mặc định: 5 và 20 Client đồng thời.

Chạy từ thư mục gốc repository:

```powershell
python -B Code\tests\qa\run_qa.py
```

Tùy chỉnh mức tải và dung lượng mỗi tệp:

```powershell
python -B Code\tests\qa\run_qa.py --clients 5 20 --file-size-mib 2
```

Mỗi lần chạy tạo một thư mục mới tại `docs/test-evidence/<timestamp>/` gồm báo
cáo Markdown, JSON/CSV kết quả, log Server, ảnh UI và manifest SHA-256.

Benchmark chạy trên loopback nên phản ánh hiệu năng phần mềm và filesystem của
máy chạy test, không đại diện cho độ trễ mạng LAN/Internet thực tế.
