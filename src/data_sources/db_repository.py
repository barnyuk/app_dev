"""SQLite repository for base-station data."""

import sqlite3

from config.settings import root_path

DEFAULT_DATABASE = root_path / 'src' / 'data_sources' / 'database.sqlite3'


def get_data_from_db(operator: str, bsn_id: str, database=None) -> tuple:
    """Fetch (address, plan) for a base station from the local SQLite database."""
    if database is None:
        database = DEFAULT_DATABASE
    connection = sqlite3.connect(str(database))
    try:
        cursor = connection.cursor()
        cursor.execute(
            f'SELECT address, plan FROM {operator} WHERE bsn_id = ?',
            (str(bsn_id),),
        )
        result = cursor.fetchone()
    finally:
        connection.close()
    if result is None:
        raise ValueError(f'Base station {bsn_id} not found for operator {operator}.')
    return result
