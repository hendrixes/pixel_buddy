#!/usr/bin/env python
from importlib import import_module

from app.main import app as flask_app, db


def main():
    import_module("app.auth.model")
    import_module("app.pets.model")

    with flask_app.app_context():
        db.create_all()

        tables = ", ".join(sorted(db.metadata.tables.keys()))
        print(f"Database initialized at: {flask_app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"Registered tables: {tables}")


if __name__ == "__main__":
    main()
