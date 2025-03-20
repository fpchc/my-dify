from collections.abc import Generator
from io import BytesIO
from minio import Minio
from minio.error import S3Error

from configs import dify_config
from extensions.storage.base_storage import BaseStorage


class MinIOStorage(BaseStorage):
    def __init__(self):
        # 创建 MinIO 客户端实例
        self.client = Minio(
            endpoint=dify_config.MINIO_ENDPOINT,
            access_key=dify_config.MINIO_ACCESS_KEY,
            secret_key=dify_config.MINIO_SECRET_KEY,
            secure=dify_config.MINIO_SECURE,
        )

        self.bucket_name = dify_config.MINIO_BUCKET_NAME

        # 确保存储桶存在，如果不存在则创建
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)

    def save(self, filename: str, data: bytes) -> None:
        try:
            # 使用 put_object 上传文件
            file_like_object = BytesIO(data)
            self.client.put_object(self.bucket_name, filename, file_like_object, len(data))
        except S3Error as e:
            raise Exception(f"Failed to save file: {e}")

    def load_once(self, filename: str) -> bytes:
        try:
            # 下载对象并返回
            response = self.client.get_object(self.bucket_name, filename)
            return response.read()
        except S3Error as e:
            raise FileNotFoundError(f"File not found: {e}")

    def load_stream(self, filename: str) -> Generator:
        try:
            # 获取文件对象流
            response = self.client.get_object(self.bucket_name, filename)
            batch_size = 8192
            # 使用迭代器读取流数据
            for chunk in response.stream(batch_size):  # response.stream() 用于流式读取
                yield chunk
        except S3Error as e:
            raise FileNotFoundError(f"File not found: {filename} - {e}")

    def download(self, filename: str, target_filepath: str):
        try:
            # 下载文件到本地
            response = self.client.get_object(self.bucket_name, filename)
            with open(target_filepath, 'wb') as f:
                # 使用 response.stream() 来流式读取文件
                for chunk in response.stream(4096):  # 这里是逐块读取
                    f.write(chunk)
        except S3Error as e:
            raise FileNotFoundError(f"File not found: {e}")

    def exists(self, filename: str) -> bool:
        try:
            # 检查文件是否存在
            self.client.stat_object(self.bucket_name, filename)
            return True
        except S3Error as e:
            return False

    def delete(self, filename: str):
        try:
            # 删除文件
            self.client.remove_object(self.bucket_name, filename)
        except S3Error as e:
            raise FileNotFoundError(f"File not found: {e}")
