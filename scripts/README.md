# Scripts

Utilidades locais para inspecionar o SQLite do projeto.

Uso principal:

```bash
uv run python scripts/db.py tables
uv run python scripts/db.py schema
uv run python scripts/db.py schema users
uv run python scripts/db.py count
uv run python scripts/db.py count pets
uv run python scripts/db.py users
uv run python scripts/db.py pets
uv run python scripts/db.py events
```

Por padrao, os comandos usam `instance/database.db`.
Para usar outro arquivo:

```bash
uv run python scripts/db.py --db caminho/do/banco.db tables
```
