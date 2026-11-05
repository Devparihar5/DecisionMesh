"""Durable agent definitions, including a one-time starter catalog seed."""
from backend.app.schemas.agents import AgentDefinition
from backend.app.storage.database import Database


class AgentRepository:
    def __init__(self, database: Database):
        self.database = database

    def seed(self, defaults: list[AgentDefinition]) -> None:
        with self.database.connection() as connection:
            if connection.execute("SELECT 1 FROM metadata WHERE key='agents_seeded'").fetchone():
                return
            connection.executemany('INSERT OR IGNORE INTO agents VALUES (?, ?)',
                                   [(agent.id, agent.model_dump_json()) for agent in defaults])
            connection.execute("INSERT INTO metadata VALUES ('agents_seeded', '1')")

    def list_agents(self) -> list[AgentDefinition]:
        with self.database.connection() as connection:
            return [AgentDefinition.model_validate_json(row['definition'])
                    for row in connection.execute('SELECT definition FROM agents ORDER BY rowid')]

    def save(self, agent: AgentDefinition) -> None:
        with self.database.connection() as connection:
            connection.execute('INSERT INTO agents VALUES (?, ?) ON CONFLICT(id) DO UPDATE SET definition=excluded.definition',
                               (agent.id, agent.model_dump_json()))

    def delete(self, agent_id: str) -> None:
        with self.database.connection() as connection:
            connection.execute('DELETE FROM agents WHERE id=?', (agent_id,))
