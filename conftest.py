"""Root conftest — registra apenas o marker do Stack360.

Não altera nada do comportamento legado de testes.
"""


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "pg: exige Postgres real do Stack360 (docker compose -f docker-compose.stack360.yml up -d)"
    )
