"""
Data Models
Represents the various data structures used in BlueBubbles
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class Handle:
    """Represents a contact/handle in BlueBubbles."""
    original_rowid: int
    address: str
    country: Optional[str] = None
    uncanonicalizedId: Optional[str] = None

@dataclass
class Message:
    """Represents a message in BlueBubbles."""
    original_rowid: int
    guid: str
    text: Optional[str]
    handle_id: int
    date_created: int  # Unix timestamp in milliseconds
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
    
    # Related objects
    handle: Optional[Handle] = None
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

@dataclass
class Chat:
    """Represents a chat in BlueBubbles."""
    original_rowid: int
    guid: str
    chat_identifier: str
    style: int
    is_archived: bool = False
    is_filtered: bool = False
    display_name: Optional[str] = None
    group_id: Optional[str] = None
    
    # Related objects
    participants: Optional[List[Handle]] = None
    last_message: Optional[Message] = None
    
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

@dataclass
class ServerInfo:
    """Represents BlueBubbles server information."""
    os_version: str
    server_version: str
    private_api: bool
    proxy_service: Optional[str] = None
    helper_connected: bool = False
