#!/usr/bin/env python3
"""
SMB CLI Tool for NAS Media Catalog
Provides commands to scan SMB shares, manage media files, and generate VLC playlists.
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from typing import List, Optional
import argparse
from datetime import datetime

# Add the API source to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from nas_media_catalog.config import settings
    from nas_media_catalog.database import DatabaseManager, MediaFileDB
    from nas_media_catalog.playlist_generator import PlaylistGenerator, create_vlc_compatible_url
    from nas_media_catalog.upnp_client import UPnPClient
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you're running from the API directory")
    sys.exit(1)

# Try to import SMB library
try:
    from smb.SMBConnection import SMBConnection
    from smb.base import SharedFile
    SMB_AVAILABLE = True
except ImportError:
    print("Warning: pysmb library not installed. Install with: uv add pysmb")
    SMB_AVAILABLE = False


class SMBScanner:
    """SMB share scanner and media file discoverer."""
    
    def __init__(self, hostname: str, username: str, password: str, share_name: str = ""):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.share_name = share_name
        self.connection = None
    
    def connect(self) -> bool:
        """Connect to SMB server."""
        if not SMB_AVAILABLE:
            print("SMB library not available. Please install pysmb: uv add pysmb")
            return False
        
        print(f"🔌 Attempting to connect to SMB server: {self.hostname}")
        print(f"   Username: {self.username}")
        
        # Try different connection methods
        connection_methods = [
            {"use_ntlm_v2": True, "domain": ""},
            {"use_ntlm_v2": False, "domain": ""},
            {"use_ntlm_v2": True, "domain": "WORKGROUP"},
            {"use_ntlm_v2": False, "domain": "WORKGROUP"},
        ]
        
        for i, method in enumerate(connection_methods):
            try:
                print(f"   Trying method {i+1}: NTLM_v2={method['use_ntlm_v2']}, Domain='{method['domain']}'")
                
                self.connection = SMBConnection(
                    self.username, 
                    self.password, 
                    "nas-media-catalog",  # client machine name
                    self.hostname,        # server name
                    domain=method.get("domain", ""),
                    use_ntlm_v2=method["use_ntlm_v2"]
                )
                
                # Try connecting to server
                connected = self.connection.connect(self.hostname, 445, timeout=10)
                if connected:
                    print(f"✅ Connected to SMB server: {self.hostname}")
                    return True
                else:
                    print(f"   Method {i+1} failed: Connection returned False")
                    
            except Exception as e:
                print(f"   Method {i+1} failed: {e}")
                continue
        
        print(f"❌ All connection methods failed for SMB server: {self.hostname}")
        return False
    
    def list_shares(self) -> List[str]:
        """List available SMB shares."""
        if not self.connection:
            return []
        
        try:
            shares = self.connection.listShares()
            share_names = []
            
            print("\n📁 Available SMB shares:")
            for share in shares:
                if not share.isSpecial:  # Skip special shares like IPC$, ADMIN$
                    share_names.append(share.name)
                    print(f"  • {share.name} - {share.comments}")
            
            return share_names
            
        except Exception as e:
            print(f"❌ Error listing shares: {e}")
            return []
    
    def scan_media_files(self, share_name: str, path: str = "/", max_depth: int = 3) -> List[dict]:
        """Scan SMB share for media files."""
        if not self.connection:
            print("❌ Not connected to SMB server")
            return []
        
        media_files = []
        media_extensions = {
            '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v',
            '.mp3', '.flac', '.wav', '.aac', '.ogg', '.wma', '.m4a'
        }
        
        def scan_directory(dir_path: str, current_depth: int = 0):
            if current_depth >= max_depth:
                return
            
            try:
                files = self.connection.listPath(share_name, dir_path)
                
                for file in files:
                    if file.filename in ['.', '..']:
                        continue
                    
                    full_path = f"{dir_path.rstrip('/')}/{file.filename}"
                    
                    if file.isDirectory:
                        # Recursively scan subdirectories
                        print(f"  📁 Scanning directory: {full_path}")
                        scan_directory(full_path, current_depth + 1)
                    else:
                        # Check if it's a media file
                        file_ext = Path(file.filename).suffix.lower()
                        if file_ext in media_extensions:
                            file_type = "video" if file_ext in {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'} else "audio"
                            
                            # Create SMB path for VLC
                            smb_path = f"//{share_name}{full_path}"
                            smb_url = create_vlc_compatible_url(
                                smb_path, self.username, self.password, self.hostname
                            )
                            
                            media_files.append({
                                'name': file.filename,
                                'path': full_path,
                                'size': file.file_size,
                                'modified_time': file.last_write_time,
                                'file_type': file_type,
                                'share_name': share_name,
                                'smb_url': smb_url
                            })
                            
                            print(f"  📄 Found: {file.filename} ({file_type})")
                            
            except Exception as e:
                print(f"⚠️  Error scanning {dir_path}: {e}")
        
        print(f"\n🔍 Scanning SMB share '{share_name}' for media files...")
        scan_directory(path)
        
        print(f"✅ Found {len(media_files)} media files")
        return media_files
    
    def disconnect(self):
        """Disconnect from SMB server."""
        if self.connection:
            self.connection.close()
            print("🔌 Disconnected from SMB server")


class MediaCLI:
    """CLI interface for media management."""
    
    def __init__(self):
        self.db_manager = None
    
    async def init_database(self, db_path: str = "media_catalog.db"):
        """Initialize database connection."""
        db_url = f"sqlite+aiosqlite:///{db_path}"
        self.db_manager = DatabaseManager(db_url)
        await self.db_manager.init_db()
        print(f"📊 Database initialized: {db_path}")
    
    async def scan_smb_command(self, hostname: str, username: str, password: str, 
                              share_name: str = "", max_depth: int = 3):
        """Scan SMB share and cache media files."""
        scanner = SMBScanner(hostname, username, password, share_name)
        
        if not scanner.connect():
            return False
        
        try:
            # If no share specified, list available shares
            if not share_name:
                shares = scanner.list_shares()
                if not shares:
                    print("❌ No shares found")
                    return False
                
                print(f"\nℹ️  Use --share option to scan a specific share")
                return True
            
            # Scan the specified share
            media_files = scanner.scan_media_files(share_name, max_depth=max_depth)
            
            if not media_files:
                print("❌ No media files found")
                return False
            
            # Cache files in database
            if self.db_manager:
                print(f"💾 Caching {len(media_files)} files in database...")
                
                # Convert to UPnP-like objects for compatibility with existing cache method
                class MockMediaFile:
                    def __init__(self, file_data):
                        self.title = file_data['name']
                        self.path = file_data['smb_url']  # Use SMB URL as primary path
                        self.size = file_data['size']
                        self.mime_type = self._get_mime_type(file_data['file_type'])
                        self.url = file_data['smb_url']  # Mark as UPnP-like object
                        self.smb_url = file_data['smb_url']
                    
                    def _get_mime_type(self, file_type):
                        return f"{file_type}/mp4" if file_type == "video" else f"{file_type}/mpeg"
                
                mock_files = [MockMediaFile(f) for f in media_files]
                await self.db_manager.cache_media_files(mock_files, share_name)
                print(f"✅ Successfully cached {len(mock_files)} files")
            
            return True
            
        finally:
            scanner.disconnect()
    
    async def list_files_command(self, share_name: str = "", file_type: str = ""):
        """List cached media files."""
        if not self.db_manager:
            print("❌ Database not initialized")
            return
        
        files = await self.db_manager.get_media_files(
            share_name=share_name if share_name else None,
            file_type=file_type if file_type else None
        )
        
        if not files:
            print("📭 No media files found")
            return
        
        print(f"\n📋 Found {len(files)} media files:")
        print("-" * 80)
        
        for file in files:
            size_mb = file.size / (1024 * 1024)
            print(f"📄 {file.name}")
            print(f"   Share: {file.share_name} | Type: {file.file_type} | Size: {size_mb:.1f} MB")
            if hasattr(file, 'smb_url') and file.smb_url:
                print(f"   SMB: {file.smb_url}")
            else:
                print(f"   Path: {file.path}")
            print()
    
    async def create_playlist_command(self, name: str, description: str = "", 
                                    share_name: str = "", file_type: str = "",
                                    output_file: str = ""):
        """Create a VLC playlist from cached media files."""
        if not self.db_manager:
            print("❌ Database not initialized")
            return
        
        # Get media files based on filters
        files = await self.db_manager.get_media_files(
            share_name=share_name if share_name else None,
            file_type=file_type if file_type else None
        )
        
        if not files:
            print("❌ No media files found matching criteria")
            return
        
        print(f"🎵 Creating playlist '{name}' with {len(files)} files")
        
        # Create playlist in database
        from nas_media_catalog.database import PlaylistCreate
        
        # Use SMB URLs if available, otherwise fall back to path
        file_paths = []
        for f in files:
            if hasattr(f, 'smb_url') and f.smb_url:
                file_paths.append(f.smb_url)
            else:
                file_paths.append(f.path)
        
        playlist_data = PlaylistCreate(
            name=name,
            description=description,
            file_paths=file_paths
        )
        
        playlist_db = await self.db_manager.create_playlist(playlist_data)
        
        # Generate M3U file
        upnp_client = UPnPClient()  # Mock client, not used for SMB playlists
        playlist_gen = PlaylistGenerator(upnp_client)
        
        if not output_file:
            safe_name = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_")).rstrip()
            output_file = f"{safe_name}.m3u"
        
        m3u_content = playlist_gen.generate_m3u_content(playlist_db, files)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(m3u_content)
        
        print(f"✅ Playlist saved: {output_file}")
        print(f"📊 Playlist ID: {playlist_db.id}")
        
        # Show preview of playlist
        print("\n📋 Playlist preview:")
        print("-" * 50)
        lines = m3u_content.split('\n')
        preview_lines = []
        for line in lines:
            if line.strip():
                preview_lines.append(line)
                if len(preview_lines) >= 10:
                    break
        
        for line in preview_lines:
            print(line)
        
        if len([l for l in lines if l.strip()]) > 10:
            print("... (truncated)")
    
    async def list_playlists_command(self):
        """List all playlists in database."""
        if not self.db_manager:
            print("❌ Database not initialized")
            return
        
        playlists = await self.db_manager.get_playlists()
        
        if not playlists:
            print("📭 No playlists found")
            return
        
        print(f"\n🎵 Found {len(playlists)} playlists:")
        print("-" * 60)
        
        for playlist in playlists:
            file_paths = json.loads(playlist.file_paths)
            print(f"🎵 {playlist.name} (ID: {playlist.id})")
            print(f"   Description: {playlist.description or 'No description'}")
            print(f"   Files: {len(file_paths)} | Created: {playlist.created_at.strftime('%Y-%m-%d %H:%M')}")
            print()


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SMB CLI Tool for NAS Media Catalog",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List SMB shares
  python smb_cli.py scan --hostname 192.168.1.100 --username nas --password mypass
  
  # Scan specific share
  python smb_cli.py scan --hostname 192.168.1.100 --username nas --password mypass --share Media
  
  # List cached files
  python smb_cli.py list --share Media --type video
  
  # Create playlist
  python smb_cli.py playlist "My Movies" --description "All my movies" --type video
  
  # List playlists
  python smb_cli.py playlists
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scan command
    scan_parser = subparsers.add_parser('scan', help='Scan SMB share for media files')
    scan_parser.add_argument('--hostname', required=True, help='SMB server hostname or IP')
    scan_parser.add_argument('--username', required=True, help='SMB username')
    scan_parser.add_argument('--password', required=True, help='SMB password')
    scan_parser.add_argument('--share', help='SMB share name (if not provided, lists shares)')
    scan_parser.add_argument('--depth', type=int, default=3, help='Max directory depth to scan')
    scan_parser.add_argument('--db', default='media_catalog.db', help='Database file path')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List cached media files')
    list_parser.add_argument('--share', help='Filter by share name')
    list_parser.add_argument('--type', help='Filter by file type (video/audio)')
    list_parser.add_argument('--db', default='media_catalog.db', help='Database file path')
    
    # Playlist command
    playlist_parser = subparsers.add_parser('playlist', help='Create VLC playlist')
    playlist_parser.add_argument('name', help='Playlist name')
    playlist_parser.add_argument('--description', default='', help='Playlist description')
    playlist_parser.add_argument('--share', help='Filter files by share name')
    playlist_parser.add_argument('--type', help='Filter files by type (video/audio)')
    playlist_parser.add_argument('--output', help='Output M3U file path')
    playlist_parser.add_argument('--db', default='media_catalog.db', help='Database file path')
    
    # Playlists command
    playlists_parser = subparsers.add_parser('playlists', help='List all playlists')
    playlists_parser.add_argument('--db', default='media_catalog.db', help='Database file path')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    async def run_command():
        cli = MediaCLI()
        
        # Initialize database for commands that need it
        if args.command in ['scan', 'list', 'playlist', 'playlists']:
            await cli.init_database(args.db)
        
        if args.command == 'scan':
            await cli.scan_smb_command(
                args.hostname, args.username, args.password,
                args.share or "", args.depth
            )
        elif args.command == 'list':
            await cli.list_files_command(args.share or "", args.type or "")
        elif args.command == 'playlist':
            await cli.create_playlist_command(
                args.name, args.description, args.share or "", 
                args.type or "", args.output or ""
            )
        elif args.command == 'playlists':
            await cli.list_playlists_command()
    
    try:
        asyncio.run(run_command())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
