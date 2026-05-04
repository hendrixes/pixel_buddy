#!/usr/bin/env python3
import argparse
import sqlite3
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT_DIR / "instance" / "database.db"


def connect(db_path):
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def print_rows(rows, columns):
    if not rows:
        print("No rows found.")
        return

    def format_value(value):
        return "" if value is None else str(value)

    widths = {
        column: max(len(column), *(len(format_value(row[column])) for row in rows))
        for column in columns
    }

    header = "  ".join(column.ljust(widths[column]) for column in columns)
    separator = "  ".join("-" * widths[column] for column in columns)
    print(header)
    print(separator)

    for row in rows:
        print("  ".join(format_value(row[column]).ljust(widths[column]) for column in columns))


def fetch_tables(connection):
    rows = connection.execute(
        """
        select name
        from sqlite_master
        where type = 'table'
          and name not like 'sqlite_%'
        order by name
        """
    ).fetchall()

    return [row[0] for row in rows]


def print_tables(connection):
    tables = fetch_tables(connection)

    if not tables:
        print("No tables found.")
        return

    for table in tables:
        print(table)


def print_schema(connection, table_name=None):
    params = ()
    table_filter = ""

    if table_name:
        table_filter = "and name = ?"
        params = (table_name,)

    rows = connection.execute(
        f"""
        select name, sql
        from sqlite_master
        where type = 'table'
          and name not like 'sqlite_%'
          {table_filter}
        order by name
        """,
        params,
    ).fetchall()

    if not rows:
        target = table_name or "tables"
        print(f"No schema found for {target}.")
        return

    for name, sql in rows:
        print(f"-- {name}")
        print(sql + ";")


def print_counts(connection, table_name=None):
    tables = [table_name] if table_name else fetch_tables(connection)

    if not tables:
        print("No tables found.")
        return

    for table in tables:
        try:
            count = connection.execute(f'select count(*) from "{table}"').fetchone()[0]
        except sqlite3.OperationalError as exc:
            raise SystemExit(f"Could not count table {table}: {exc}") from exc

        print(f"{table}: {count}")


def print_users(connection):
    rows = connection.execute(
        """
        select
            id,
            username,
            length(password_hash) as password_hash_len
        from users
        order by id
        """
    ).fetchall()

    print_rows(rows, ("id", "username", "password_hash_len"))


def print_pets(connection):
    rows = connection.execute(
        """
        select
            pets.id,
            pets.name,
            pets.user_id,
            users.username as owner,
            pets.hunger,
            pets.happiness,
            pets.energy,
            pets.curiosity,
            pets.network_xp,
            pets.mood,
            pets.last_network_action_at,
            pets.created_at
        from pets
        left join users on users.id = pets.user_id
        order by pets.id
        """
    ).fetchall()

    print_rows(
        rows,
        (
            "id",
            "name",
            "user_id",
            "owner",
            "hunger",
            "happiness",
            "energy",
            "curiosity",
            "network_xp",
            "mood",
            "last_network_action_at",
            "created_at",
        ),
    )


def print_events(connection):
    rows = connection.execute(
        """
        select
            network_events.id,
            network_events.pet_id,
            pets.name as pet_name,
            network_events.event_type,
            network_events.target,
            network_events.success,
            network_events.summary,
            network_events.created_at
        from network_events
        left join pets on pets.id = network_events.pet_id
        order by network_events.created_at desc, network_events.id desc
        """
    ).fetchall()

    print_rows(
        rows,
        (
            "id",
            "pet_id",
            "pet_name",
            "event_type",
            "target",
            "success",
            "summary",
            "created_at",
        ),
    )


def build_parser():
    parser = argparse.ArgumentParser(description="Inspect the local SQLite database.")
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"SQLite database path. Default: {DEFAULT_DB_PATH}",
    )

    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("tables", help="List database tables.")

    schema_parser = subcommands.add_parser("schema", help="Show table schema.")
    schema_parser.add_argument("table", nargs="?", help="Optional table name.")

    count_parser = subcommands.add_parser("count", help="Show row counts.")
    count_parser.add_argument("table", nargs="?", help="Optional table name.")

    subcommands.add_parser("users", help="List created users.")
    subcommands.add_parser("pets", help="List created pets.")
    subcommands.add_parser("events", help="List network events.")

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    db_path = args.db.expanduser().resolve()

    with connect(db_path) as connection:
        if args.command == "tables":
            print_tables(connection)
        elif args.command == "schema":
            print_schema(connection, args.table)
        elif args.command == "count":
            print_counts(connection, args.table)
        elif args.command == "users":
            print_users(connection)
        elif args.command == "pets":
            print_pets(connection)
        elif args.command == "events":
            print_events(connection)


if __name__ == "__main__":
    main(sys.argv[1:])
