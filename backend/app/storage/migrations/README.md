# Migrations

This directory is reserved for Alembic migration files.

The scaffold uses `Base.metadata.create_all()` during startup so the app can run immediately.
When persistence behavior is implemented, replace startup table creation with Alembic-managed migrations.

