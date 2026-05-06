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
uv run python scripts/db.py agents
uv run python scripts/db.py events
uv run python scripts/db.py blocked-ips
```

Por padrao, os comandos usam `instance/database.db`.
Para usar outro arquivo:

```bash
uv run python scripts/db.py --db caminho/do/banco.db tables
```

Quando o modelo mudar durante desenvolvimento, recrie o banco explicitamente:

```bash
uv run python init_db.py --reset
```
