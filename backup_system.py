import os
import logging
import sqlite3
import shutil
import datetime
import zipfile
from typing import Optional, List
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
            # Test connection
            try:
                self.s3_client.list_buckets()
            except Exception as e:
                logger.error(f"Unable to connect to S3: {str(e)}")
                self.s3_client = None
                raise
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except Exception as e:
            logger.error(f"S3 setup error: {str(e)}")
            raise

    def upload_to_s3(self, backup_file: str) -> bool:
        """Upload backup to S3."""
        if not self.s3_client or not hasattr(self, 'bucket_name'):
            logger.error("S3 client not initialized")
            return False
            
        try:
            file_name = os.path.basename(backup_file)
            
            # Upload with encryption
            self.s3_client.upload_file(
                backup_file,
                self.bucket_name,
                file_name,
                ExtraArgs={'ServerSideEncryption': 'AES256'}
            )
            
            logger.info(f"Backup uploaded to S3: {file_name}")
            return True
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            return False
        except Exception as e:
            logger.error(f"S3 upload error: {str(e)}")
            return False

    def download_from_s3(self, backup_name: str, target_dir: str) -> str:
        """Download backup from S3."""
        if not self.s3_client or not hasattr(self, 'bucket_name'):
            logger.error("S3 client not initialized")
            return ""
            
        try:
            local_path = os.path.join(target_dir, backup_name)
            self.s3_client.download_file(
                self.bucket_name,
                backup_name,
                local_path
            )
            logger.info(f"Downloaded backup from S3: {backup_name}")
            return local_path
            
        except Exception as e:
            logger.error(f"S3 download error: {str(e)}")
            return ""

    def cleanup_old_backups(self, max_age_days: int = 7) -> None:
        """Remove backups older than max_age_days."""
        try:
            current_time = datetime.datetime.now()
            min_age = current_time - datetime.timedelta(days=max_age_days)
            
            for file_name in os.listdir(self.backup_dir):
                if file_name.endswith('.zip'):
                    file_path = os.path.join(self.backup_dir, file_name)
                    file_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    if file_time < min_age:
                        try:
                            os.remove(file_path)
                            logger.info(f"Removed old backup: {file_name}")
                        except Exception as e:
                            logger.error(f"Error removing {file_name}: {str(e)}")
                            
        except Exception as e:
            logger.error(f"Backup cleanup error: {str(e)}")
            raise
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
