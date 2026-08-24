# Manifest 07_mysql_database

Không file nào được phép ghi đè mặc định. Leader phải so sánh trước khi chép.

| File nguồn | Vị trí trong gói | Vị trí khi ghép | Phụ thuộc | Có thể ghi đè? |
|---|---|---|---|---|
| D:\UDM\.env.example | .env.example | .env.example | 00_shared_contracts; mysql-connector-python | Không |
| D:\UDM\database\migrations\001_create_upload_history.sql | database/migrations/001_create_upload_history.sql | database/migrations/001_create_upload_history.sql | 00_shared_contracts; mysql-connector-python | Không |
| D:\UDM\database\README.md | database/README.md | database/README.md | 00_shared_contracts; mysql-connector-python | Không |
| D:\UDM\database\seeds\README.md | database/seeds/README.md | database/seeds/README.md | 00_shared_contracts; mysql-connector-python | Không |
| Tài liệu/công cụ bàn giao | requirements.txt | requirements.txt | 00_shared_contracts; mysql-connector-python | Không |
| D:\UDM\src\udm10\persistence\mysql_repository.py | src/udm10/persistence/mysql_repository.py | src/udm10/persistence/mysql_repository.py | 00_shared_contracts; mysql-connector-python | Không |
| Test/fake bàn giao | tests/test_mysql_package.py | Không ghép production; chạy trong test | 00_shared_contracts; mysql-connector-python | Không |
