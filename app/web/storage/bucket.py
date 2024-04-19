import os
from minio import Minio
from io import BytesIO

from app.web.utils import get_rand_str


class BucketStorage:
    def __init__(self, url: str, key: str, secret: str) -> None:
        self.client = Minio(
            endpoint=url,
            access_key=key,
            secret_key=secret,
            secure=False,
        )

    def add_file(self, bucket, data: BytesIO) -> str:
        object_name = get_rand_str(n=12)

        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

        self.client.put_object(bucket, object_name, data, length=len(data.getvalue()))

        return object_name

    def get_file(self, bucket: str, filename: str, save_folder: str) -> str:
        output_file = os.path.join(save_folder, filename + ".pdf")

        self.client.fget_object(
            bucket_name=bucket, object_name=filename, file_path=output_file
        )

        return output_file

    def delete_file(self, bucket: str, filename: str) -> str:
        self.client.remove_object(bucket_name=bucket, object_name=filename)


if __name__ == "__main__":
    from dotenv import load_dotenv

    source_file = "data/test/documents/swda_factsheet.pdf"
    bucket = "etf-docs-test"

    load_dotenv()

    file = BytesIO(open(source_file, "rb").read())
    bucket_store = BucketStorage()
    object_id = bucket_store.add_file(bucket=bucket, data=file)
    bucket_store.get_file(
        bucket=bucket, filename=object_id, save_folder="tmp/documents"
    )
