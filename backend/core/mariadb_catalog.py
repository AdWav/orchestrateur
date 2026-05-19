from __future__ import annotations

import json
import os
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from core.contracts import AgentDefinition, WorkflowDefinition


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL est requis lorsque CATALOG_BACKEND=mariadb.")
    return url


def _parse_payload(raw: Any) -> dict[str, object]:
    if isinstance(raw, str):
        return json.loads(raw)
    if isinstance(raw, (bytes, bytearray)):
        return json.loads(raw.decode("utf-8"))
    if isinstance(raw, dict):
        return raw
    raise TypeError(f"Payload JSON inattendu: {type(raw)!r}")


def _connect() -> pymysql.connections.Connection:
    return pymysql.connect(
        **_connection_kwargs(_database_url()),
        cursorclass=DictCursor,
        autocommit=False,
    )


def _connection_kwargs(url: str) -> dict[str, Any]:
    """Parse mysql://user:pass@host:port/db (format courant pour MariaDB)."""
    if not url.startswith("mysql://"):
        raise ValueError("DATABASE_URL doit commencer par mysql:// pour MariaDB.")
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


class MariadbDefinitionCatalog:
    def list_agents(self) -> list[AgentDefinition]:
        with _connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT payload FROM agent_definitions ORDER BY id")
                rows = cursor.fetchall()
        return [AgentDefinition.model_validate(_parse_payload(row["payload"])) for row in rows]

    def get_agent(self, agent_id: str) -> AgentDefinition:
        with _connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT payload FROM agent_definitions WHERE id = %s",
                    (agent_id,),
                )
                row = cursor.fetchone()
        if row is None:
            raise KeyError(f"Unknown agent definition '{agent_id}'.")
        return AgentDefinition.model_validate(_parse_payload(row["payload"]))

    def save_agent(self, definition: AgentDefinition, overwrite: bool = False) -> AgentDefinition:
        payload = json.dumps(definition.model_dump(mode="json"))
        with _connect() as conn:
            with conn.cursor() as cursor:
                if not overwrite:
                    cursor.execute(
                        "SELECT 1 FROM agent_definitions WHERE id = %s",
                        (definition.id,),
                    )
                    if cursor.fetchone():
                        raise FileExistsError(f"Agent definition '{definition.id}' already exists.")
                cursor.execute(
                    """
                    INSERT INTO agent_definitions (id, payload)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE
                        payload = VALUES(payload),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (definition.id, payload),
                )
            conn.commit()
        return definition

    def list_workflows(self) -> list[WorkflowDefinition]:
        with _connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT payload FROM workflow_definitions ORDER BY id")
                rows = cursor.fetchall()
        return [WorkflowDefinition.model_validate(_parse_payload(row["payload"])) for row in rows]

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition:
        with _connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT payload FROM workflow_definitions WHERE id = %s",
                    (workflow_id,),
                )
                row = cursor.fetchone()
        if row is None:
            raise KeyError(f"Unknown workflow definition '{workflow_id}'.")
        return WorkflowDefinition.model_validate(_parse_payload(row["payload"]))

    def save_workflow(
        self,
        definition: WorkflowDefinition,
        overwrite: bool = False,
    ) -> WorkflowDefinition:
        known_agents = {agent.id for agent in self.list_agents()}
        unknown_agents = sorted(
            {
                step.agent_definition_id
                for step in definition.steps
                if step.agent_definition_id not in known_agents
            }
        )
        if unknown_agents:
            unknown = ", ".join(unknown_agents)
            raise ValueError(f"Workflow definition references unknown agents: {unknown}.")

        payload = json.dumps(definition.model_dump(mode="json"))
        with _connect() as conn:
            with conn.cursor() as cursor:
                if not overwrite:
                    cursor.execute(
                        "SELECT 1 FROM workflow_definitions WHERE id = %s",
                        (definition.id,),
                    )
                    if cursor.fetchone():
                        raise FileExistsError(f"Workflow definition '{definition.id}' already exists.")
                cursor.execute(
                    """
                    INSERT INTO workflow_definitions (id, payload)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE
                        payload = VALUES(payload),
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (definition.id, payload),
                )
            conn.commit()
        return definition
