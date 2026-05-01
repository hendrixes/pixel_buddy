#!/usr/bin/env python
from app.main import app as flask_app, db

import app.auth.model  # noqa: F401
import app.pets.model  # noqa: F401


def main():
    with flask_app.app_context():
        db.create_all()

        tables = ", ".join(sorted(db.metadata.tables.keys()))
        print(f"Database initialized at: {flask_app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"Registered tables: {tables}")


if __name__ == "__main__":
    main()
