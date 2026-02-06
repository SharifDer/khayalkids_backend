from hcloud import Client
from datetime import datetime
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class SnapshotService:
    def __init__(self, api_token: str, server_name: str):
        self.client = Client(token=api_token)
        self.server_name = server_name
        self.last_check_file = "last_snapshot_time.txt"
    
    def has_changes(self):
        """Check if data/ or stories/ folders changed since last snapshot"""
        try:
            if not os.path.exists(self.last_check_file):
                logger.info("First run - no previous snapshot timestamp found")
                return True
            
            with open(self.last_check_file) as f:
                last_snapshot_time = float(f.read().strip())
            
            # Check data and stories folders
            data_mtime = os.path.getmtime("data")
            stories_mtime = os.path.getmtime("stories")
            latest_change = max(data_mtime, stories_mtime)
            
            if latest_change > last_snapshot_time:
                logger.info("Changes detected in data/ or stories/")
                return True
            else:
                logger.info("No changes detected")
                return False
                
        except Exception as e:
            logger.error(f"Error checking changes: {e}")
            return False
    
    def create_snapshot(self):
        """Create server snapshot with timestamp name"""
        try:
            server = self.client.servers.get_by_name(self.server_name)
            if not server:
                logger.error(f"Server '{self.server_name}' not found")
                return False
            
            snapshot_name = f"khayalkids_{datetime.now().strftime('%Y-%m-%d_%H-%M')}"
            
            logger.info(f"Creating snapshot: {snapshot_name}")
            server.create_image(description=snapshot_name, type="snapshot")
            
            # Update last snapshot time
            with open(self.last_check_file, "w") as f:
                f.write(str(datetime.now().timestamp()))
            
            logger.info(f"✅ Snapshot created: {snapshot_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Snapshot creation failed: {e}")
            return False
    
    def cleanup_old_snapshots(self, keep=3):
        """Delete snapshots older than the newest 'keep' snapshots"""
        try:
            # Get all images
            all_images = self.client.images.get_all()
            
            # Filter snapshots for this project
            snapshots = [
                img for img in all_images 
                if img.type == "snapshot" 
                and img.description 
                and img.description.startswith("khayalkids_")
            ]
            
            if len(snapshots) <= keep:
                logger.info(f"Only {len(snapshots)} snapshots exist, keeping all")
                return
            
            # Sort by creation date (newest first)
            snapshots.sort(key=lambda x: x.created, reverse=True)
            
            # Delete old ones
            deleted_count = 0
            for old_snapshot in snapshots[keep:]:
                logger.info(f"🗑️ Deleting old snapshot: {old_snapshot.description}")
                old_snapshot.delete()
                deleted_count += 1
            
            logger.info(f"✅ Kept {keep} newest snapshots, deleted {deleted_count} old ones")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
    
    def backup_job(self):
        """Main backup job - checks changes and creates snapshot if needed"""
        logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running backup check...")
        
        if self.has_changes():
            if self.create_snapshot():
                self.cleanup_old_snapshots(keep=3)
        else:
            logger.info("Skipping snapshot - no changes")
