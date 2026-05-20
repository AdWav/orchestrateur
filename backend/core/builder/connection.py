from __future__ import annotations

import os
from typing import Any

import pymysql
from pymysql.cursors import DictCursor


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL est requis pour le module builder (MariaDB).")
    return url


def connection_kwargs(url: str) -> dict[str, Any]:
    if not url.startswith("mysql://"):
        raise ValueError("DATABASE_URL doit commencer par mysql://")
    without_scheme = url[len("mysql://") :]
    credentials, remainder = without_scheme.split("@", 1)
    user, password = credentials.split(":", 1)
    host_port, database = remainder.split("/", 1)
    if ":" in host_port:
        host, port_str = host_port.split(":", 1)
        port = int(port_str)
    else:
        host = host_port
        port = 3306
    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": database,
        "charset": "utf8mb4",
    }


def connect() -> pymysql.connections.Connection:
    return pymysql.connect(
        **connection_kwargs(database_url()),
        cursorclass=DictCursor,
        autocommit=False,
    )
