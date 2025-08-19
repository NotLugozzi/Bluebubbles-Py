"""
Database Models
Data models for database records
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class HandleRecord:
    """Database record for a handle/contact."""
    original_rowid: int
    address: str
    country: Optional[str] = None
    uncanonicalizedId: Optional[str] = None

@dataclass 
class ChatRecord:
    """Database record for a chat."""
    original_rowid: int
    guid: str
    chat_identifier: str
    style: int
    is_archived: bool = False
    is_filtered: bool = False
    display_name: Optional[str] = None
    group_id: Optional[str] = None
    participants: Optional[List[HandleRecord]] = None
    last_message_text: Optional[str] = None
    last_message_date: Optional[int] = None
    last_message_from_me: Optional[bool] = None
    last_message_address: Optional[str] = None
    
    def __post_init__(self):
        if self.participants is None:
            self.participants = []
    
    @property
    def is_group_chat(self) -> bool:
        """Check if this is a group chat."""
        return len(self.participants) > 1 if self.participants else False
    
    @property
    def display_title(self) -> str:
        """Get the display title for this chat."""
        if self.display_name:
            return self.display_name
        
        if self.participants:
            if len(self.participants) == 1:
                return self.participants[0].address
            else:
                return ", ".join([p.address for p in self.participants[:3]])
                
        return self.chat_identifier
    
    @property
    def last_message_datetime(self) -> Optional[datetime]:
        """Get last message time as a datetime object."""
        if self.last_message_date:
            return datetime.fromtimestamp(self.last_message_date / 1000)
        return None

@dataclass
class MessageRecord:
    """Database record for a message."""
    original_rowid: int
    guid: str
    text: Optional[str]
    handle_id: Optional[int]
    handle_address: Optional[str]
    chat_guid: str
    date_created: int
    date_read: Optional[int] = None
    date_delivered: Optional[int] = None
    is_from_me: bool = False
    is_delayed: bool = False
    is_auto_reply: bool = False
    is_system_message: bool = False
    is_service_message: bool = False
    is_forward: bool = False
    is_archived: bool = False
    is_audio_message: bool = False
    has_dd_results: bool = False
    item_type: int = 0
    group_title: Optional[str] = None
    group_action_type: int = 0
    is_expired: bool = False
    balloon_bundle_id: Optional[str] = None
    associated_message_guid: Optional[str] = None
    associated_message_type: Optional[str] = None
    expressive_send_style_id: Optional[str] = None
    time_expressive_send_style_id: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    
    def __post_init__(self):
        if self.attachments is None:
            self.attachments = []
    
    @property
    def datetime_created(self) -> datetime:
        """Get message creation time as a datetime object."""
        return datetime.fromtimestamp(self.date_created / 1000)
    
    @property
    def datetime_read(self) -> Optional[datetime]:
        """Get message read time as a datetime object."""
        if self.date_read:
            return datetime.fromtimestamp(self.date_read / 1000)
        return None
