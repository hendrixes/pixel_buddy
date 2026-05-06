import argparse
from importlib import import_module

from app.main import app as flask_app, db


def build_parser():
    parser = argparse.ArgumentParser(description="Initialize the SQLite database.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all tables before creating the current schema.",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    import_module("app.auth.model")
    import_module("app.pets.model")
    import_module("app.firewall.model")

    with flask_app.app_context():
        if args.reset:
            db.drop_all()

        db.create_all()

        tables = ", ".join(sorted(db.metadata.tables.keys()))
        print(f"Database initialized at: {flask_app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"Registered tables: {tables}")
        if args.reset:
            print("Existing tables were dropped before initialization.")


if __name__ == "__main__":
    main()
