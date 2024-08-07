from sqlite3 import Cursor
from typing import Tuple, Dict, Union, Callable
from uuid import uuid4

def generate_ids(namespace: str) -> str:
    return namespace + uuid4().hex[:8]


def dict_factory(cursor: Cursor, row: Tuple) -> Dict:
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def linear_func(x: float, a: float, b: float) -> float:
    return a * x + b