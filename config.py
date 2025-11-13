import pyodbc

SERVER = r'localhost\SQLEXPRESS'
DATABASE = 'KioskoDB'
TRUSTED = True
USER = 'sa'
PASSWORD = 'yourStrong(!)Password'

_DRIVERS = [
    '{ODBC Driver 18 for SQL Server}',
    '{ODBC Driver 17 for SQL Server}',
    '{SQL Server Native Client 11.0}',
    '{SQL Server}'
]

def _connect(database: str) -> pyodbc.Connection:
    last_error = None
    for drv in _DRIVERS:
        try:
            if TRUSTED:
                conn_str = f'DRIVER={drv};SERVER={SERVER};DATABASE={database};Trusted_Connection=yes;Encrypt=no;'
            else:
                conn_str = f'DRIVER={drv};SERVER={SERVER};DATABASE={database};UID={USER};PWD={PASSWORD};Encrypt=no;'
            return pyodbc.connect(conn_str, timeout=5)
        except Exception as e:
            last_error = e
            continue
    raise RuntimeError(f"No se pudo conectar a SQL Server. Último error: {last_error}")

def get_connection() -> pyodbc.Connection:
    return _connect(DATABASE)
