"""pytest 共享 fixture。"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """一个独立的 FastAPI 测试客户端。"""
    app = create_app()
    with TestClient(app) as c:
        yield c
