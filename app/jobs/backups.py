import os
import subprocess
import datetime
import logging
from app.config import settings

logger = logging.getLogger(__name__)

def perform_backup():
    """
    Creates a database dump, encrypts it symmetrically, and prunes old backups.
    Runs synchronously (intended for a background thread/process).
    """
    db_url = settings.DATABASE_URL
    storage_path = settings.BACKUP_STORAGE_PATH
    passphrase = settings.BACKUP_PASSPHRASE
    
    os.makedirs(storage_path, exist_ok=True)
    
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    
    # 1. Dump database
    dump_path = os.path.join(storage_path, f"backup_{timestamp}.dump")
    encrypted_path = dump_path + ".gpg"
    
    try:
        if db_url.startswith("sqlite"):
            # sqlite+aiosqlite:///./lore.db -> ./lore.db
            db_file = db_url.split("///")[-1]
            if not os.path.exists(db_file):
                logger.error(f"Backup failed: SQLite DB file {db_file} not found.")
                return False
            # SQLite backup via simple file copy/dump using Python sqlite3 module
            import sqlite3
            src = sqlite3.connect(db_file)
            dst = sqlite3.connect(dump_path)
            src.backup(dst)
            src.close()
            dst.close()
        elif db_url.startswith("postgresql") or db_url.startswith("postgres"):
            # Use pg_dump
            # Convert postgresql+asyncpg:// to postgresql://
            pg_url = db_url.replace("+asyncpg", "")
            subprocess.run(["pg_dump", "-Fc", pg_url, "-f", dump_path], check=True)
        else:
            logger.error(f"Backup failed: Unsupported DB dialect in {db_url}")
            return False
            
        # 2. Encrypt
        # Using symmetric encryption with GPG (AES256)
        # Note: --batch and --yes prevent interactive prompts
        subprocess.run([
            "gpg", "--symmetric", "--cipher-algo", "AES256", 
            "--batch", "--yes", "--passphrase", passphrase,
            "-o", encrypted_path, dump_path
        ], check=True)
        
        # Remove the unencrypted dump
        if os.path.exists(dump_path):
            os.remove(dump_path)
            
        logger.info(f"Database backed up and encrypted successfully: {encrypted_path}")
        
        # 3. Prune old backups (>35 days)
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=35)
        for f in os.listdir(storage_path):
            if f.startswith("backup_") and f.endswith(".gpg"):
                f_path = os.path.join(storage_path, f)
                file_time = datetime.datetime.fromtimestamp(os.path.getmtime(f_path), tz=datetime.timezone.utc)
                if file_time < cutoff_date:
                    os.remove(f_path)
                    logger.info(f"Pruned old backup: {f_path}")
                    
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Backup process failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during backup: {e}")
        return False
