import os
import logging
import sqlite3
import shutil
import datetime
import zipfile
from typing import Optional
import boto3
from botocore.exceptions import NoCredentialsError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackupSystem:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
        self.s3_client = None
        self.initialize_backup_dir()

    def initialize_backup_dir(self):
        """Create backup directory if it doesn't exist."""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

    def create_backup(self) -> str:
        """Create a backup of the database."""
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = os.path.join(self.backup_dir, f'backup_{timestamp}.db')
            
            # Create backup
            conn = sqlite3.connect(self.db_path)
            backup_conn = sqlite3.connect(backup_file)
            conn.backup(backup_conn)
            backup_conn.close()
            conn.close()
            
            # Create zip archive
            zip_file = os.path.join(self.backup_dir, f'backup_{timestamp}.zip')
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(backup_file, os.path.basename(backup_file))
            
            # Clean up
            os.remove(backup_file)
            
            logger.info(f"Backup created successfully: {zip_file}")
            return zip_file
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return ""

    def restore_backup(self, backup_file: str) -> bool:
        """Restore from a backup file."""
        try:
            # Extract backup
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                zipf.extractall(self.backup_dir)
            
            # Get extracted file
            extracted_file = os.path.join(self.backup_dir, os.path.basename(backup_file).replace('.zip', '.db'))
            
            # Replace current database
            shutil.copy2(extracted_file, self.db_path)
            
            # Clean up
            os.remove(extracted_file)
            
            logger.info(f"Backup restored successfully from: {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Error restoring backup: {str(e)}")
            return False

    def list_backups(self) -> List[str]:
        """List available backup files."""
        try:
            backups = []
            for file in os.listdir(self.backup_dir):
                if file.endswith('.zip'):
                    backups.append(file)
            return sorted(backups, reverse=True)
        except Exception as e:
            logger.error(f"Error listing backups: {str(e)}")
            return []

    def setup_s3(self, aws_access_key: str, aws_secret_key: str, bucket_name: str):
        """Setup S3 client for cloud backups."""
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )
            self.bucket_name = bucket_name
            logger.info("S3 client setup successfully")
        except NoCredentialsError:
            logger.error("AWS credentials not found")
        except Exception as e:
            logger.error(f"Error setting up S3: {str(e)}")

    def upload_to_s3(self, backup_file: str) -> bool:
        """Upload backup to S3."""
        if not self.s3_client:
            return False
            
        try:
            filename = os.path.basename(backup_file)
            self.s3_client.upload_file(
                backup_file,
                self.bucket_name,
                filename,
                ExtraArgs={'ServerSideEncryption': 'AES256'}
            )
            logger.info(f"Backup uploaded to S3: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            return False

    def download_from_s3(self, filename: str, target_path: str) -> bool:
        """Download backup from S3."""
        if not self.s3_client:
            return False
            
        try:
            self.s3_client.download_file(
                self.bucket_name,
                filename,
                target_path
            )
            logger.info(f"Backup downloaded from S3: {filename}")
            return True
        except Exception as e:
            logger.error(f"Error downloading from S3: {str(e)}")
            return False
