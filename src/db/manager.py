"""
Database Manager
Handles all SQLite database operations for caching
"""

import sqlite3
import json
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import threading

from ..models.data import Chat, Message, Handle
from .models import ChatRecord, MessageRecord, HandleRecord

class DatabaseManager:
    """Manages SQLite database operations for BlueBubbles data caching."""
    
    def __init__(self, db_path: str = None):
        """Initialize the database manager."""
        if db_path is None:
            # Use XDG config directory or fallback to home
            try:
                from os import environ
                config_dir = environ.get('XDG_CONFIG_HOME', Path.home() / '.config')
                app_dir = Path(config_dir) / 'bluebubbles-gtk'
                app_dir.mkdir(parents=True, exist_ok=True)
                db_path = str(app_dir / 'cache.db')
            except Exception:
                db_path = str(Path.home() / '.bluebubbles_cache.db')
        
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(self.db_path)
            self._local.connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        return self._local.connection
    
    def _init_db(self):
        """Initialize the database schema."""
        conn = self._get_connection()
        
        # Create tables
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS handles (
            id INTEGER PRIMARY KEY,
            original_rowid INTEGER UNIQUE NOT NULL,
            address TEXT NOT NULL,
            country TEXT,
            uncanonicalizedId TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY,
            original_rowid INTEGER UNIQUE NOT NULL,
            guid TEXT UNIQUE NOT NULL,
            chat_identifier TEXT NOT NULL,
            style INTEGER NOT NULL,
            is_archived BOOLEAN DEFAULT FALSE,
            is_filtered BOOLEAN DEFAULT FALSE,
            display_name TEXT,
            group_id TEXT,
            last_message_date INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            original_rowid INTEGER UNIQUE NOT NULL,
            guid TEXT UNIQUE NOT NULL,
            text TEXT,
            handle_id INTEGER,
            chat_guid TEXT NOT NULL,
            date_created INTEGER NOT NULL,
            date_read INTEGER,
            date_delivered INTEGER,
            is_from_me BOOLEAN DEFAULT FALSE,
            is_delayed BOOLEAN DEFAULT FALSE,
            is_auto_reply BOOLEAN DEFAULT FALSE,
            is_system_message BOOLEAN DEFAULT FALSE,
            is_service_message BOOLEAN DEFAULT FALSE,
            is_forward BOOLEAN DEFAULT FALSE,
            is_archived BOOLEAN DEFAULT FALSE,
            is_audio_message BOOLEAN DEFAULT FALSE,
            has_dd_results BOOLEAN DEFAULT FALSE,
            item_type INTEGER DEFAULT 0,
            group_title TEXT,
            group_action_type INTEGER DEFAULT 0,
            is_expired BOOLEAN DEFAULT FALSE,
            balloon_bundle_id TEXT,
            associated_message_guid TEXT,
            associated_message_type TEXT,
            expressive_send_style_id TEXT,
            time_expressive_send_style_id TEXT,
            attachments_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (handle_id) REFERENCES handles (original_rowid),
            FOREIGN KEY (chat_guid) REFERENCES chats (guid)
        );
        
        CREATE TABLE IF NOT EXISTS chat_participants (
            chat_guid TEXT NOT NULL,
            handle_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (chat_guid, handle_id),
            FOREIGN KEY (chat_guid) REFERENCES chats (guid),
            FOREIGN KEY (handle_id) REFERENCES handles (original_rowid)
        );
        
        -- Indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_messages_chat_guid ON messages (chat_guid);
        CREATE INDEX IF NOT EXISTS idx_messages_date_created ON messages (date_created);
        CREATE INDEX IF NOT EXISTS idx_messages_handle_id ON messages (handle_id);
        CREATE INDEX IF NOT EXISTS idx_chats_last_message_date ON chats (last_message_date);
        CREATE INDEX IF NOT EXISTS idx_handles_address ON handles (address);
        """)
        
        conn.commit()
    
    def save_handle(self, handle_data: Dict[str, Any]) -> int:
        """Save a handle to the database."""
        conn = self._get_connection()
        
        cursor = conn.execute("""
        INSERT OR REPLACE INTO handles 
        (original_rowid, address, country, uncanonicalizedId, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            handle_data.get('originalROWID'),
            handle_data.get('address'),
            handle_data.get('country'),
            handle_data.get('uncanonicalizedId')
        ))
        
        conn.commit()
        return cursor.lastrowid
    
    def save_chat(self, chat_data: Dict[str, Any]) -> str:
        """Save a chat to the database."""
        conn = self._get_connection()
        
        # Extract last message date for sorting
        last_message_date = None
        if chat_data.get('lastMessage') and chat_data['lastMessage'].get('dateCreated'):
            last_message_date = chat_data['lastMessage']['dateCreated']
        
        cursor = conn.execute("""
        INSERT OR REPLACE INTO chats 
        (original_rowid, guid, chat_identifier, style, is_archived, is_filtered, 
         display_name, group_id, last_message_date, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            chat_data.get('originalROWID'),
            chat_data.get('guid'),
            chat_data.get('chatIdentifier'),
            chat_data.get('style', 0),
            chat_data.get('isArchived', False),
            chat_data.get('isFiltered', False),
            chat_data.get('displayName'),
            chat_data.get('groupId'),
            last_message_date
        ))
        
        # Save participants
        if chat_data.get('participants'):
            # Clear existing participants
            conn.execute("DELETE FROM chat_participants WHERE chat_guid = ?", 
                        (chat_data.get('guid'),))
            
            # Add new participants
            for participant in chat_data['participants']:
                self.save_handle(participant)
                conn.execute("""
                INSERT OR IGNORE INTO chat_participants (chat_guid, handle_id)
                VALUES (?, ?)
                """, (chat_data.get('guid'), participant.get('originalROWID')))
        
        conn.commit()
        return chat_data.get('guid')
    
    def save_message(self, message_data: Dict[str, Any], chat_guid: str) -> str:
        """Save a message to the database."""
        conn = self._get_connection()
        
        # Save handle if present
        handle_id = None
        if message_data.get('handle'):
            self.save_handle(message_data['handle'])
            handle_id = message_data['handle'].get('originalROWID')
        
        # Serialize attachments
        attachments_json = None
        if message_data.get('attachments'):
            attachments_json = json.dumps(message_data['attachments'])
        
        cursor = conn.execute("""
        INSERT OR REPLACE INTO messages 
        (original_rowid, guid, text, handle_id, chat_guid, date_created, date_read, 
         date_delivered, is_from_me, is_delayed, is_auto_reply, is_system_message,
         is_service_message, is_forward, is_archived, is_audio_message, has_dd_results,
         item_type, group_title, group_action_type, is_expired, balloon_bundle_id,
         associated_message_guid, associated_message_type, expressive_send_style_id,
         time_expressive_send_style_id, attachments_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            message_data.get('originalROWID'),
            message_data.get('guid'),
            message_data.get('text'),
            handle_id,
            chat_guid,
            message_data.get('dateCreated'),
            message_data.get('dateRead'),
            message_data.get('dateDelivered'),
            message_data.get('isFromMe', False),
            message_data.get('isDelayed', False),
            message_data.get('isAutoReply', False),
            message_data.get('isSystemMessage', False),
            message_data.get('isServiceMessage', False),
            message_data.get('isForward', False),
            message_data.get('isArchived', False),
            message_data.get('isAudioMessage', False),
            message_data.get('hasDdResults', False),
            message_data.get('itemType', 0),
            message_data.get('groupTitle'),
            message_data.get('groupActionType', 0),
            message_data.get('isExpired', False),
            message_data.get('balloonBundleId'),
            message_data.get('associatedMessageGuid'),
            message_data.get('associatedMessageType'),
            message_data.get('expressiveSendStyleId'),
            message_data.get('timeExpressiveSendStyleId'),
            attachments_json
        ))
        
        conn.commit()
        return message_data.get('guid')
    
    def get_chats(self, limit: int = 100, offset: int = 0) -> List[ChatRecord]:
        """Get chats from the database, ordered by last message date."""
        conn = self._get_connection()
        
        cursor = conn.execute("""
        SELECT c.*, 
               COUNT(cp.handle_id) as participant_count,
               h_last.address as last_message_address,
               m_last.text as last_message_text,
               m_last.date_created as last_message_date,
               m_last.is_from_me as last_message_from_me
        FROM chats c
        LEFT JOIN chat_participants cp ON c.guid = cp.chat_guid
        LEFT JOIN messages m_last ON c.guid = m_last.chat_guid 
            AND m_last.date_created = (
                SELECT MAX(date_created) 
                FROM messages 
                WHERE chat_guid = c.guid
            )
        LEFT JOIN handles h_last ON m_last.handle_id = h_last.original_rowid
        WHERE c.is_archived = FALSE
        GROUP BY c.id
        ORDER BY COALESCE(c.last_message_date, 0) DESC
        LIMIT ? OFFSET ?
        """, (limit, offset))
        
        chats = []
        for row in cursor.fetchall():
            # Get participants for this chat
            participants = self.get_chat_participants(row['guid'])
            
            chat_record = ChatRecord(
                original_rowid=row['original_rowid'],
                guid=row['guid'],
                chat_identifier=row['chat_identifier'],
                style=row['style'],
                is_archived=row['is_archived'],
                is_filtered=row['is_filtered'],
                display_name=row['display_name'],
                group_id=row['group_id'],
                participants=participants,
                last_message_text=row['last_message_text'],
                last_message_date=row['last_message_date'],
                last_message_from_me=row['last_message_from_me'],
                last_message_address=row['last_message_address']
            )
            chats.append(chat_record)
        
        return chats
    
    def get_chat_participants(self, chat_guid: str) -> List[HandleRecord]:
        """Get participants for a specific chat."""
        conn = self._get_connection()
        
        cursor = conn.execute("""
        SELECT h.* FROM handles h
        JOIN chat_participants cp ON h.original_rowid = cp.handle_id
        WHERE cp.chat_guid = ?
        ORDER BY h.address
        """, (chat_guid,))
        
        participants = []
        for row in cursor.fetchall():
            handle_record = HandleRecord(
                original_rowid=row['original_rowid'],
                address=row['address'],
                country=row['country'],
                uncanonicalizedId=row['uncanonicalizedId']
            )
            participants.append(handle_record)
        
        return participants
    
    def get_chat_messages(self, chat_guid: str, limit: int = 50, offset: int = 0) -> List[MessageRecord]:
        """Get messages for a specific chat."""
        conn = self._get_connection()
        
        cursor = conn.execute("""
        SELECT m.*, h.address as handle_address
        FROM messages m
        LEFT JOIN handles h ON m.handle_id = h.original_rowid
        WHERE m.chat_guid = ?
        ORDER BY m.date_created DESC
        LIMIT ? OFFSET ?
        """, (chat_guid, limit, offset))
        
        messages = []
        for row in cursor.fetchall():
            # Parse attachments
            attachments = []
            if row['attachments_json']:
                try:
                    attachments = json.loads(row['attachments_json'])
                except json.JSONDecodeError:
                    attachments = []
            
            message_record = MessageRecord(
                original_rowid=row['original_rowid'],
                guid=row['guid'],
                text=row['text'],
                handle_id=row['handle_id'],
                handle_address=row['handle_address'],
                chat_guid=row['chat_guid'],
                date_created=row['date_created'],
                date_read=row['date_read'],
                date_delivered=row['date_delivered'],
                is_from_me=row['is_from_me'],
                is_delayed=row['is_delayed'],
                is_auto_reply=row['is_auto_reply'],
                is_system_message=row['is_system_message'],
                is_service_message=row['is_service_message'],
                is_forward=row['is_forward'],
                is_archived=row['is_archived'],
                is_audio_message=row['is_audio_message'],
                has_dd_results=row['has_dd_results'],
                item_type=row['item_type'],
                group_title=row['group_title'],
                group_action_type=row['group_action_type'],
                is_expired=row['is_expired'],
                balloon_bundle_id=row['balloon_bundle_id'],
                associated_message_guid=row['associated_message_guid'],
                associated_message_type=row['associated_message_type'],
                expressive_send_style_id=row['expressive_send_style_id'],
                time_expressive_send_style_id=row['time_expressive_send_style_id'],
                attachments=attachments
            )
            messages.append(message_record)
        
        # Reverse the messages so they're in chronological order (oldest first)
        # Database query gets newest messages first (DESC), but UI expects oldest first
        return list(reversed(messages))
    
    def get_message_reactions(self, message_guid: str) -> List[MessageRecord]:
        """Get reactions for a specific message."""
        conn = self._get_connection()
        
        # Some servers prefix associated_message_guid (e.g., 'p:0/<guid>').
        # Match both exact and prefixed forms for robustness.
        cursor = conn.execute("""
        SELECT m.*, h.address as handle_address
        FROM messages m
        LEFT JOIN handles h ON m.handle_id = h.original_rowid
        WHERE (
            m.associated_message_guid = ?
            OR m.associated_message_guid = ('p:0/' || ?)
            OR m.associated_message_guid = ('bp:0/' || ?)
        )
        AND m.associated_message_type IS NOT NULL
        ORDER BY m.date_created ASC
        """, (message_guid, message_guid, message_guid))
        
        reactions = []
        for row in cursor.fetchall():
            # Parse attachments JSON if present
            attachments = []
            if row['attachments_json']:
                try:
                    attachments = json.loads(row['attachments_json'])
                except json.JSONDecodeError:
                    attachments = []
            
            reaction_record = MessageRecord(
                original_rowid=row['original_rowid'],
                guid=row['guid'],
                text=row['text'],
                handle_id=row['handle_id'],
                handle_address=row['handle_address'],
                chat_guid=row['chat_guid'],
                date_created=row['date_created'],
                date_read=row['date_read'],
                date_delivered=row['date_delivered'],
                is_from_me=row['is_from_me'],
                is_delayed=row['is_delayed'],
                is_auto_reply=row['is_auto_reply'],
                is_system_message=row['is_system_message'],
                is_service_message=row['is_service_message'],
                is_forward=row['is_forward'],
                is_archived=row['is_archived'],
                is_audio_message=row['is_audio_message'],
                has_dd_results=row['has_dd_results'],
                item_type=row['item_type'],
                group_title=row['group_title'],
                group_action_type=row['group_action_type'],
                is_expired=row['is_expired'],
                balloon_bundle_id=row['balloon_bundle_id'],
                associated_message_guid=row['associated_message_guid'],
                associated_message_type=row['associated_message_type'],
                expressive_send_style_id=row['expressive_send_style_id'],
                time_expressive_send_style_id=row['time_expressive_send_style_id'],
                attachments=attachments
            )
            reactions.append(reaction_record)
        
        return reactions
    
    def get_chat_by_guid(self, chat_guid: str) -> Optional[ChatRecord]:
        """Get a specific chat by its GUID."""
        conn = self._get_connection()
        
        cursor = conn.execute("""
        SELECT c.*, 
               h_last.address as last_message_address,
               m_last.text as last_message_text,
               m_last.date_created as last_message_date,
               m_last.is_from_me as last_message_from_me
        FROM chats c
        LEFT JOIN (
            SELECT m.chat_guid, m.text, m.date_created, m.is_from_me, m.handle_id,
                   ROW_NUMBER() OVER (PARTITION BY m.chat_guid ORDER BY m.date_created DESC) as rn
            FROM messages m
        ) m_last ON c.guid = m_last.chat_guid AND m_last.rn = 1
        LEFT JOIN handles h_last ON m_last.handle_id = h_last.original_rowid
        WHERE c.guid = ?
        """, (chat_guid,))
        
        row = cursor.fetchone()
        if row:
            # Get participants for this chat
            participants = self.get_chat_participants(chat_guid)
            
            return ChatRecord(
                original_rowid=row['original_rowid'],
                guid=row['guid'],
                chat_identifier=row['chat_identifier'],
                style=row['style'],
                is_archived=row['is_archived'],
                is_filtered=row['is_filtered'],
                display_name=row['display_name'],
                group_id=row['group_id'],
                participants=participants,
                last_message_text=row['last_message_text'],
                last_message_date=row['last_message_date'],
                last_message_from_me=row['last_message_from_me'],
                last_message_address=row['last_message_address']
            )
        return None
    
    def clear_cache(self):
        """Clear all cached data."""
        conn = self._get_connection()
        conn.executescript("""
        DELETE FROM chat_participants;
        DELETE FROM messages;
        DELETE FROM chats;
        DELETE FROM handles;
        """)
        conn.commit()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about cached data."""
        conn = self._get_connection()
        
        stats = {}
        
        # Count chats
        cursor = conn.execute("SELECT COUNT(*) FROM chats")
        stats['chats'] = cursor.fetchone()[0]
        
        # Count messages
        cursor = conn.execute("SELECT COUNT(*) FROM messages")
        stats['messages'] = cursor.fetchone()[0]
        
        # Count handles
        cursor = conn.execute("SELECT COUNT(*) FROM handles")
        stats['handles'] = cursor.fetchone()[0]
        
        return stats
    
    def close(self):
        """Close the database connection."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
