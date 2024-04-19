import random
import string
import base64
import hashlib


def get_rand_str(n: int) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def encode_image(image_path):
    """Getting the base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def compute_file_digest(file_path: str) -> str:

    with open(file_path, "rb") as f:
        file_digest = hashlib.sha256(f.read()).hexdigest()

    return file_digest
