from typing import List, Tuple, Any
import random
import string
import base64
import hashlib
import sqlite3
import pandas as pd


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


def query_db(
    db_path: str, query: str, return_df: bool = True
) -> Tuple[List[List[Any]], List[str]] | pd.DataFrame:
    db_conn = sqlite3.connect(database=db_path)
    cursor = db_conn.cursor()

    res = cursor.execute(query)
    rows = res.fetchall()
    column_names = [col[0] for col in cursor.description]

    db_conn.close()

    if return_df:
        return pd.DataFrame(data=rows, columns=column_names)
    else:
        return rows, column_names
