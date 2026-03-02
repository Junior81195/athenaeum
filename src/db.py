"""Shared database connection for API routes and MCP server."""

import psycopg2
from config.settings import DATABASE_URL


def get_connection():
    """Return a new psycopg2 connection to the athenaeum database."""
    return psycopg2.connect(DATABASE_URL)
