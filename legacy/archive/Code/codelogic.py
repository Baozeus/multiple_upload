from collections import deque 
import time 

class QuanlyUpload : 

    def __init__(self , so_file_toi_da = 3 ):
        self.so_file_toi_da = so_file_toi_da 
        
        self.queue = deque()
        
        self.uploading = [] 
        
        self.completed = []
        
        self.failed = []
        
    def add_file(self , file ) : 
        if len(self.uploading) < self.so_file_toi_da : 
          self.uploading.append(file) 
          print(f"{file} -> Đang tải ")
        else : 
          self.queue.append(file) 
          print(f"{file} -> Chờ ")
        

    def upload_success(self, file):

        if file in self.uploading:
            self.uploading.remove(file)

        self.completed.append(file)

        print(f"{file} -> HOÀN TẤT")

        self.process_queue()
        
    def upload_error(self, file):

        if file in self.uploading:
            self.uploading.remove(file)

        self.failed.append(file)

        print(f"{file} -> LỖI")

        self.process_queue()
        
    def process_queue(self):

        while (
            len(self.uploading) < self.so_file_toi_da
            and len(self.queue) > 0
        ):

            file = self.queue.popleft()

            self.uploading.append(file)

            print(f"{file} -> ĐANG TẢI")
        
    def show_status(self):

        print("\n===== TRẠNG THÁI =====")

        print("Đang tải:", self.uploading)

        print("Đang chờ:", list(self.queue))

        print("Hoàn tất:", self.completed)

        print("Lỗi:", self.failed)
        