from uuid import uuid4


def generate_ids(namespace: str) -> str:
    return namespace + uuid4().hex[:8]
