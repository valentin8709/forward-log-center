import sqlite3
import logging
import socket

from datetime import datetime
from logging import handlers
from pathlib import Path
from glob import glob

logger = logging.getLogger("ReadLogCenter")

# Add syslog configuration
syslogHandler = handlers.SysLogHandler(address=("SYSLOG_SERVER", 514))
logger.addHandler(syslogHandler)
logging.basicConfig(format='%(message)s', level=logging.INFO)

print("\n====================================================")
print("Forward Synology Log Center logs to Syslog server :)")
print("====================================================\n")
print("Running...")

# Log locations
log_dirs = [
    "/volume1/@appdata/WebStation/log/*",
    "/volume1/logs/*",
    "/volume1/logs/*/*",
]

# Database configuration
STD_DB: str = ".DB"
CONNECTION_DB: str = "_CON"
SYSTEM_DB: str = "_SYS"
ACCESS_DB: str = "_access.db"
ERR_ACCESS_DB: str = "_error.db"

sql_request: str = ""

# Read logs in SQLite format
for log_dir in log_dirs:
    for log_path in glob(log_dir):
        # Check for DB structure
        if Path(log_path).is_file() and log_path.endswith(CONNECTION_DB):
            print(f"Found connection type database {log_path}")
            sql_request = "SELECT host, llevel, prog, utcsec, luser, msg FROM connection_log WHERE utcsec > strftime('%s', 'now') - 3600;"
        elif Path(log_path).is_file() and log_path.endswith(SYSTEM_DB):
            print(f"Found system type database {log_path}")
            sql_request = "SELECT host, llevel, prog, utcsec, luser, msg FROM general_log WHERE utcsec > strftime('%s', 'now') - 3600;"
        elif Path(log_path).is_file() and log_path.endswith(ACCESS_DB):
            print(f"Found access log type database {log_path}")
            sql_request = "SELECT time, level, client, message FROM log WHERE time > strftime('%s', 'now') - 3600;"
        elif Path(log_path).is_file() and log_path.endswith(ERR_ACCESS_DB):
            print(f"Found error access log type database {log_path}")
            sql_request = "SELECT time, level, client, message FROM log WHERE time > strftime('%s', 'now') - 3600;"
        elif Path(log_path).is_file() and log_path.endswith(STD_DB):
            print(f"Found standard type database {log_path}")
            sql_request = "SELECT host, ip, llevel, utcsec, prog, msg FROM logs WHERE utcsec > strftime('%s', 'now') - 3600;"
        else:
            # If not a known log database, skip to the next one
            continue

        # Get logs from SQLite database
        conn = sqlite3.connect(log_path)
        cursor = conn.cursor()
        cursor.execute(sql_request)

        # Parse database lines and send them Syslog
        if log_path.endswith(CONNECTION_DB) or log_path.endswith(SYSTEM_DB):
            logs = cursor.fetchall()
            for row in logs:
                host = row[0]
                level = row[1]
                prog = row[2]
                timestamp = datetime.utcfromtimestamp(row[3]).strftime('%Y-%m-%d %H:%M:%S')
                user = row[4]
                logline = row[5]
                message = f"{host} {prog}: {level} {user} {logline}"
                logger.info(f"{timestamp} {message}")

        elif log_path.endswith(ACCESS_DB) or log_path.endswith(ERR_ACCESS_DB):
            logs = cursor.fetchall()
            for row in logs:
                timestamp = datetime.utcfromtimestamp(row[0]).strftime('%Y-%m-%d %H:%M:%S')
                level = row[1] if log_path.endswith(ACCESS_DB) else "error"
                ip = row[2]
                logline = row[3]
                prog = "WebStation"
                host = socket.gethostname()
                message = f"{host} {prog}: {level} {ip} {logline}"
                logger.info(f"{timestamp} {message}")

        elif log_path.endswith(STD_DB):
            logs = cursor.fetchall()
            for row in logs:
                host = row[0]
                ip = row[1]
                level = row[2]
                timestamp = datetime.utcfromtimestamp(row[3]).strftime('%Y-%m-%d %H:%M:%S')
                prog = row[4]
                logline = row[5]
                message = f"{host} {prog}: {level} {ip} {logline}"
                logger.info(f"{timestamp} {message}")

        conn.close()

print("\nSuccessfuly read Log Center !\n")
