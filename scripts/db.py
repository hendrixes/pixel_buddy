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
            pets.energy,
            pets.curiosity,
            pets.network_xp,
            pets.mood,
            pets.last_tick_at,
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
            "energy",
            "curiosity",
            "network_xp",
            "mood",
            "last_tick_at",
            "created_at",
        ),
    )


def print_agents(connection):
    rows = connection.execute(
        """
        select
            agents.id,
            agents.name,
            agents.mode,
            agents.user_id,
            users.username as owner,
            agents.last_seen_at,
            agents.created_at
        from agents
        left join users on users.id = agents.user_id
        order by agents.created_at desc, agents.id desc
        """
    ).fetchall()

    print_rows(
        rows,
        (
            "id",
            "name",
            "mode",
            "user_id",
            "owner",
            "last_seen_at",
            "created_at",
        ),
    )


def print_events(connection):
    rows = connection.execute(
        """
        select
            firewall_events.id,
            firewall_events.user_id,
            users.username as owner,
            firewall_events.agent_id,
            agents.name as agent_name,
            firewall_events.source,
            firewall_events.event_type,
            firewall_events.source_ip,
            firewall_events.destination_port,
            firewall_events.packet_count,
            firewall_events.action,
            firewall_events.summary,
            firewall_events.created_at
        from firewall_events
        left join users on users.id = firewall_events.user_id
        left join agents on agents.id = firewall_events.agent_id
        order by firewall_events.created_at desc, firewall_events.id desc
        """
    ).fetchall()

    print_rows(
        rows,
        (
            "id",
            "user_id",
            "owner",
            "agent_id",
            "agent_name",
            "source",
            "event_type",
            "source_ip",
            "destination_port",
            "packet_count",
            "action",
            "summary",
            "created_at",
        ),
    )


def print_blocked_ips(connection):
    rows = connection.execute(
        """
        select
            blocked_ips.id,
            blocked_ips.user_id,
            users.username as owner,
            blocked_ips.agent_id,
            blocked_ips.ip_address,
            blocked_ips.reason,
            blocked_ips.source,
            blocked_ips.active,
            blocked_ips.created_at
        from blocked_ips
        left join users on users.id = blocked_ips.user_id
        order by blocked_ips.created_at desc, blocked_ips.id desc
        """
    ).fetchall()

    print_rows(
        rows,
        (
            "id",
            "user_id",
            "owner",
            "agent_id",
            "ip_address",
            "reason",
            "source",
            "active",
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
    subcommands.add_parser("agents", help="List registered agents.")
    subcommands.add_parser("events", help="List firewall events.")
    subcommands.add_parser("blocked-ips", help="List blocked IP records.")

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
        elif args.command == "agents":
            print_agents(connection)
        elif args.command == "events":
            print_events(connection)
        elif args.command == "blocked-ips":
            print_blocked_ips(connection)


if __name__ == "__main__":
    main(sys.argv[1:])
