"""Database models and operations for media catalog caching."""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    select,
    text,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from pydantic import BaseModel

logger = logging.getLogger(__name__)

Base = declarative_base()


class MediaFileDB(Base):
    """Database model for media files."""

    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    size = Column(Integer, nullable=False)
    modified_time = Column(Float, nullable=False)
    file_type = Column(String, nullable=False)
    share_name = Column(String, nullable=False)
    cached_at = Column(DateTime, default=datetime.utcnow)


class PlaylistDB(Base):
    """Database model for playlists."""

    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    file_paths = Column(Text, nullable=False)  # JSON array of file paths
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Pydantic models for API
class MediaFileResponse(BaseModel):
    id: int
    path: str
    name: str
    size: int
    modified_time: float
    file_type: str
    share_name: str
    cached_at: datetime
    smb_url: str


class PlaylistCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    file_paths: List[str]


class PlaylistResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    file_paths: List[str]
    created_at: datetime
    updated_at: datetime


class DatabaseManager:
    """Manages database operations for the media catalog."""

    def __init__(self, database_url: str = "sqlite+aiosqlite:///./media_catalog.db"):
        self.database_url = database_url
        self.engine = create_async_engine(database_url, echo=False)
        self.async_session = async_sessionmaker(
            bind=self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self):
        """Initialize database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized")

    async def cache_media_files(self, media_files: List[Any], share_name: str):
        """Cache media files in the database."""
        async with self.async_session() as session:
            try:
                # Clear existing files for this share
                await session.execute(
                    text("DELETE FROM media_files WHERE share_name = :share_name"),
                    {"share_name": share_name},
                )

                # Add new files, avoiding duplicates
                db_files = []
                seen_paths = set()
                for file in media_files:
                    # Skip duplicate paths
                    if file.path in seen_paths:
                        logger.debug(f"Skipping duplicate path: {file.path}")
                        continue
                    seen_paths.add(file.path)
                    # Handle UPnPMediaFile objects
                    if hasattr(file, "url"):  # UPnPMediaFile
                        # Extract file extension from title or mime_type
                        file_type = self._get_file_type_from_mime(file.mime_type)

                        db_file = MediaFileDB(
                            path=file.path,  # UPnP URL
                            name=file.title,
                            size=file.size or 0,
                            modified_time=datetime.now().timestamp(),  # Convert to timestamp for SQLite
                            file_type=file_type,
                            share_name=share_name,
                        )
                    else:
                        # Handle legacy file objects (if any)
                        db_file = MediaFileDB(
                            path=file.path,
                            name=file.name,
                            size=file.size,
                            modified_time=file.modified_time,
                            file_type=file.file_type,
                            share_name=share_name,
                        )
                    db_files.append(db_file)

                session.add_all(db_files)
                await session.commit()
                logger.info(
                    f"Cached {len(db_files)} media files for share '{share_name}'"
                )

            except Exception as e:
                await session.rollback()
                logger.error(f"Error caching media files: {e}")
                raise

    def _get_file_type_from_mime(self, mime_type: str) -> str:
        """Extract file type from MIME type."""
        if not mime_type:
            return "unknown"

        if mime_type.startswith("video/"):
            return "video"
        elif mime_type.startswith("audio/"):
            return "audio"
        else:
            return "unknown"

    async def get_media_files(
        self,
        share_name: Optional[str] = None,
        file_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[MediaFileDB]:
        """Retrieve media files from cache with optional filters."""
        async with self.async_session() as session:
            query = select(MediaFileDB)

            if share_name:
                query = query.where(MediaFileDB.share_name == share_name)

            if file_type:
                query = query.where(MediaFileDB.file_type == file_type)

            if search:
                query = query.where(MediaFileDB.name.contains(search))

            result = await session.execute(query)
            return result.scalars().all()

    async def create_playlist(self, playlist_data: PlaylistCreate) -> PlaylistDB:
        """Create a new playlist."""
        async with self.async_session() as session:
            try:
                import json

                db_playlist = PlaylistDB(
                    name=playlist_data.name,
                    description=playlist_data.description,
                    file_paths=json.dumps(playlist_data.file_paths),
                )

                session.add(db_playlist)
                await session.commit()
                await session.refresh(db_playlist)

                logger.info(
                    f"Created playlist '{playlist_data.name}' with {len(playlist_data.file_paths)} files"
                )
                return db_playlist

            except Exception as e:
                await session.rollback()
                logger.error(f"Error creating playlist: {e}")
                raise

    async def get_playlists(self) -> List[PlaylistDB]:
        """Get all playlists."""
        async with self.async_session() as session:
            result = await session.execute(select(PlaylistDB))
            return result.scalars().all()

    async def get_playlist(self, playlist_id: int) -> Optional[PlaylistDB]:
        """Get a specific playlist by ID."""
        async with self.async_session() as session:
            result = await session.execute(
                select(PlaylistDB).where(PlaylistDB.id == playlist_id)
            )
            return result.scalar_one_or_none()

    async def delete_playlist(self, playlist_id: int) -> bool:
        """Delete a playlist."""
        async with self.async_session() as session:
            try:
                result = await session.execute(
                    select(PlaylistDB).where(PlaylistDB.id == playlist_id)
                )
                playlist = result.scalar_one_or_none()

                if playlist:
                    await session.delete(playlist)
                    await session.commit()
                    logger.info(f"Deleted playlist ID {playlist_id}")
                    return True
                return False

            except Exception as e:
                await session.rollback()
                logger.error(f"Error deleting playlist: {e}")
                raise

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about cached media files."""
        async with self.async_session() as session:
            # Count total files
            total_result = await session.execute("SELECT COUNT(*) FROM media_files")
            total_files = total_result.scalar()

            # Count by share
            share_result = await session.execute(
                "SELECT share_name, COUNT(*) FROM media_files GROUP BY share_name"
            )
            shares = dict(share_result.fetchall())

            # Count by file type
            type_result = await session.execute(
                "SELECT file_type, COUNT(*) FROM media_files GROUP BY file_type"
            )
            file_types = dict(type_result.fetchall())

            return {
                "total_files": total_files,
                "shares": shares,
                "file_types": file_types,
            }
