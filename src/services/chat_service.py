"""
Chat Service
Handles chat data synchronization between API and database
"""

import asyncio
import threading
from typing import List, Optional, Dict, Any
from ..api.client import BlueBubblesClient, BlueBubblesAPIError
from ..db.manager import DatabaseManager
from ..db.models import ChatRecord, MessageRecord
from ..config.manager import ConfigManager
from .avatar_cache import AvatarCache
from .attachment_cache import AttachmentCache

class ChatService:
    """Service for managing chat data synchronization."""
    
    def __init__(self, db_manager: DatabaseManager, config_manager: ConfigManager):
        self.db_manager = db_manager
        self.config_manager = config_manager
        self._message_check_task = None
        self._message_check_thread = None
        self.avatar_cache = AvatarCache()
        self.attachment_cache = AttachmentCache()
        self._stop_message_check = False
        self._message_check_callbacks = []
    
    async def sync_chats_from_server(self, server_url: str, password: str, 
                                   limit: int = 100) -> List[ChatRecord]:
        """
        Fetch chats from the server and sync them to the local database.
        
        Args:
            server_url: BlueBubbles server URL
            password: Server password
            limit: Maximum number of chats to fetch
            
        Returns:
            List of synchronized chat records
        """
        try:
            api_method = self.config_manager.get_api_method()
            async with BlueBubblesClient(server_url, password, api_method) as client:
                # Fetch chats with participants data
                chats_data = await client.get_chats(
                    limit=limit, 
                    with_data=['participants', 'lastMessage']
                )
                
                # Save chats to database
                for chat_data in chats_data:
                    self.db_manager.save_chat(chat_data)
                
                # Return cached chats (will include the newly synced ones)
                return self.db_manager.get_chats(limit=limit)
                
        except BlueBubblesAPIError as e:
            # print(f"API Error syncing chats: {e}")
            # Return cached chats if API fails
            return self.db_manager.get_chats(limit=limit)
        except Exception as e:
            # print(f"Unexpected error syncing chats: {e}")
            # Return cached chats if anything fails
            return self.db_manager.get_chats(limit=limit)
    
    async def sync_chat_messages(self, server_url: str, password: str, 
                               chat_guid: str, limit: int = 50) -> List[MessageRecord]:
        """
        Fetch messages for a specific chat and sync them to the database.
        
        Args:
            server_url: BlueBubbles server URL
            password: Server password
            chat_guid: GUID of the chat to fetch messages for
            limit: Maximum number of messages to fetch
            
        Returns:
            List of synchronized message records
        """
        try:
            api_method = self.config_manager.get_api_method()
            async with BlueBubblesClient(server_url, password, api_method) as client:
                # Fetch messages with handle data
                messages_data = await client.get_chat_messages(
                    chat_guid, 
                    limit=limit
                )
                
                # Save messages to database
                for message_data in messages_data:
                    self.db_manager.save_message(message_data, chat_guid)
                
                # Return cached messages
                return self.db_manager.get_chat_messages(chat_guid, limit=limit)
                
        except BlueBubblesAPIError as e:
            # print(f"API Error syncing messages for chat {chat_guid}: {e}")
            # Return cached messages if API fails
            return self.db_manager.get_chat_messages(chat_guid, limit=limit)
        except Exception as e:
            # print(f"Unexpected error syncing messages for chat {chat_guid}: {e}")
            # Return cached messages if anything fails
            return self.db_manager.get_chat_messages(chat_guid, limit=limit)
    
    def get_cached_chats(self, limit: int = 100, offset: int = 0) -> List[ChatRecord]:
        """Get chats from the local cache."""
        return self.db_manager.get_chats(limit=limit, offset=offset)
    
    def get_cached_chat_messages(self, chat_guid: str, limit: int = 50, 
                               offset: int = 0) -> List[MessageRecord]:
        """Get messages for a specific chat from the local cache."""
        return self.db_manager.get_chat_messages(chat_guid, limit=limit, offset=offset)
    
    def get_message_reactions(self, message_guid: str) -> List[MessageRecord]:
        """Get reactions for a specific message from cache."""
        return self.db_manager.get_message_reactions(message_guid)
    
    def get_chat_by_guid(self, chat_guid: str) -> Optional[ChatRecord]:
        """Get a specific chat by GUID from the cache."""
        return self.db_manager.get_chat_by_guid(chat_guid)
    
    def clear_cache(self):
        """Clear all cached data."""
        self.db_manager.clear_cache()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return self.db_manager.get_cache_stats()
    
    async def refresh_chat_data(self, server_url: str, password: str, 
                              chat_guid: str) -> Optional[ChatRecord]:
        """
        Refresh data for a specific chat including recent messages.
        
        Args:
            server_url: BlueBubbles server URL
            password: Server password
            chat_guid: GUID of the chat to refresh
            
        Returns:
            Updated chat record or None if failed
        """
        try:
            # Sync recent messages for this chat
            await self.sync_chat_messages(server_url, password, chat_guid, limit=50)
            
            # Return updated chat record
            return self.get_chat_by_guid(chat_guid)
            
        except Exception as e:
            # print(f"Error refreshing chat data for {chat_guid}: {e}")
            return None
    
    async def send_message(self, server_url: str, password: str, 
                          chat_guid: str, message: str) -> bool:
        """Send a text message to a chat."""
        try:
            api_method = self.config_manager.get_api_method()
            async with BlueBubblesClient(server_url, password, api_method) as client:
                await client.send_message(chat_guid, message)
                # Refresh messages after sending
                await self.sync_chat_messages(server_url, password, chat_guid, limit=10)
                return True
        except Exception as e:
            # print(f"Error sending message: {e}")
            return False
    
    async def send_attachment(self, server_url: str, password: str, 
                            chat_guid: str, file_path: str, message: str = "") -> bool:
        """Send an attachment to a chat."""
        try:
            api_method = self.config_manager.get_api_method()
            async with BlueBubblesClient(server_url, password, api_method) as client:
                await client.send_attachment(chat_guid, file_path, message)
                # Refresh messages after sending
                await self.sync_chat_messages(server_url, password, chat_guid, limit=10)
                return True
        except Exception as e:
            # print(f"Error sending attachment: {e}")
            return False
    
    async def send_reaction(self, server_url: str, password: str, 
                           message_guid: str, reaction_type: str, chat_guid: str = None) -> bool:
        """Send a reaction to a message."""
        try:
            api_method = self.config_manager.get_api_method()
            # print(f"🎭 Sending reaction: message_guid={message_guid}, reaction_type={reaction_type}, chat_guid={chat_guid}, api_method={api_method}")
            async with BlueBubblesClient(server_url, password, api_method) as client:
                result = await client.send_reaction(message_guid, reaction_type, chat_guid)
                # print(f"🎭 Reaction API response: {result}")
            # Proactively sync messages so UI can immediately reflect the reaction badge
            if chat_guid:
                try:
                    await self.sync_chat_messages(server_url, password, chat_guid, limit=50)
                except Exception as sync_err:
                    # Non-fatal; background monitor may still pick it up
                    # print(f"⚠️  Failed to sync messages after reaction: {sync_err}")
                    pass
            return True
        except Exception as e:
            # print(f"❌ Error sending reaction: {e}")
            return False
    
    async def remove_reaction(self, server_url: str, password: str, 
                             message_guid: str, chat_guid: str = None) -> bool:
        """Remove a reaction from a message."""
        try:
            api_method = self.config_manager.get_api_method()
            # print(f"🎭 Removing reaction: message_guid={message_guid}, chat_guid={chat_guid}, api_method={api_method}")
            async with BlueBubblesClient(server_url, password, api_method) as client:
                result = await client.remove_reaction(message_guid, chat_guid)
                # print(f"🎭 Remove reaction API response: {result}")
            # Proactively sync messages so UI can immediately reflect the removed badge
            if chat_guid:
                try:
                    await self.sync_chat_messages(server_url, password, chat_guid, limit=50)
                except Exception as sync_err:
                    # print(f"⚠️  Failed to sync messages after removing reaction: {sync_err}")
                    pass
            return True
        except Exception as e:
            # print(f"❌ Error removing reaction: {e}")
            return False
    
    async def send_typing_indicator(self, server_url: str, password: str, 
                                   chat_guid: str, typing: bool = True) -> bool:
        """Send typing indicator to a chat."""
        try:
            api_method = self.config_manager.get_api_method()
            async with BlueBubblesClient(server_url, password, api_method) as client:
                return await client.send_typing_indicator(chat_guid, typing)
        except Exception as e:
            # print(f"Error sending typing indicator: {e}")
            return False
    
    async def unsend_message(self, server_url: str, password: str, 
                            message_guid: str, chat_guid: str) -> bool:
        """Unsend a message."""
        try:
            api_method = self.config_manager.get_api_method()
            async with BlueBubblesClient(server_url, password, api_method) as client:
                await client.unsend_message(message_guid)
                # Refresh messages after unsending
                await self.sync_chat_messages(server_url, password, chat_guid, limit=10)
                return True
        except Exception as e:
            # print(f"Error unsending message: {e}")
            return False
    
    async def edit_message(self, server_url: str, password: str, 
                          message_guid: str, new_text: str, chat_guid: str) -> bool:
        """Edit a message."""
        try:
            api_method = self.config_manager.get_api_method()
            async with BlueBubblesClient(server_url, password, api_method) as client:
                await client.edit_message(message_guid, new_text)
                # Refresh messages after editing
                await self.sync_chat_messages(server_url, password, chat_guid, limit=10)
                return True
        except Exception as e:
            # print(f"Error editing message: {e}")
            return False
    
    def add_new_message_callback(self, callback):
        """Add a callback to be called when new messages are detected."""
        self._message_check_callbacks.append(callback)
    
    def remove_new_message_callback(self, callback):
        """Remove a new message callback."""
        if callback in self._message_check_callbacks:
            self._message_check_callbacks.remove(callback)
    
    def start_message_checking(self, server_url: str, password: str, check_interval: int = 3):
        """Start the background message checking task."""
        if self._message_check_task is not None:
            # print("⚠️  Message checking task is already running")
            return
        
        self._stop_message_check = False
        # print(f"🔄 Starting message checking with {check_interval}s interval")
        
        async def message_check_loop():
            """Background task to periodically check for new messages."""
            while not self._stop_message_check:
                try:
                    # Get all cached chats
                    cached_chats = self.get_cached_chats(limit=50)
                    
                    for chat in cached_chats:
                        if self._stop_message_check:
                            break
                        
                        # Get current message count for this chat
                        current_messages = self.get_cached_chat_messages(chat.guid, limit=1)
                        current_count = len(current_messages)
                        
                        # Check for new messages on server
                        try:
                            api_method = self.config_manager.get_api_method()
                            async with BlueBubblesClient(server_url, password, api_method) as client:
                                new_messages = await client.get_chat_messages(chat.guid, limit=5)
                                
                                if len(new_messages) > 0:
                                    # Get the latest message timestamp from our cache
                                    latest_cached_timestamp = 0
                                    if current_messages:
                                        latest_cached_timestamp = current_messages[0].date_created
                                    
                                    # Check if any new messages are newer than our latest cached message
                                    new_message_found = False
                                    for msg_data in new_messages:
                                        msg_timestamp = msg_data.get('dateCreated', 0)
                                        if msg_timestamp > latest_cached_timestamp:
                                            # Save new message to database
                                            self.db_manager.save_message(msg_data, chat.guid)
                                            new_message_found = True
                                            # print(f"📨 New message detected in chat {chat.display_name or chat.guid[:8]}")
                                    
                                    # Notify callbacks if new messages were found
                                    if new_message_found:
                                        for callback in self._message_check_callbacks:
                                            try:
                                                callback(chat.guid)
                                            except Exception as e:
                                                # print(f"❌ Error in message callback: {e}")
                                                pass
                        
                        except Exception as e:
                            # Don't # print errors for individual chats as it can be spammy
                            pass
                    
                    # Wait before next check
                    await asyncio.sleep(check_interval)
                
                except Exception as e:
                    # print(f"❌ Error in message checking loop: {e}")
                    await asyncio.sleep(check_interval)
            
            # print("🛑 Message checking stopped")
        
        # Start the background task by running the async function in a thread
        def run_async_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(message_check_loop())
            except asyncio.CancelledError:
                # print("🛑 Message checking task cancelled")
                pass
            except Exception as e:
                # print(f"❌ Error in message checking thread: {e}")
                pass
            finally:
                loop.close()
        
        self._message_check_thread = threading.Thread(target=run_async_loop, daemon=True)
        self._message_check_thread.start()
    
    def stop_message_checking(self):
        """Stop the background message checking task."""
        if self._message_check_task is None and self._message_check_thread is None:
            return
        
        # print("🛑 Stopping message checking...")
        self._stop_message_check = True
        
        if self._message_check_task and not self._message_check_task.done():
            self._message_check_task.cancel()
        
        # Wait a bit for the thread to finish
        if self._message_check_thread and self._message_check_thread.is_alive():
            self._message_check_thread.join(timeout=2.0)
        
        self._message_check_task = None
        self._message_check_thread = None
    
    async def get_contact_avatar(self, server_url: str, password: str, address: str) -> Optional[bytes]:
        """Get contact avatar from server or cache."""
        try:
            api_method = self.config_manager.get_api_method()
            async with BlueBubblesClient(server_url, password, api_method) as client:
                return await self.avatar_cache.get_avatar(client, address, is_group=False)
        except Exception as e:
            # Silently handle avatar fetch errors
            return None
    
    async def get_chat_icon(self, server_url: str, password: str, chat_guid: str) -> Optional[bytes]:
        """Get group chat icon from server or cache."""
        try:
            api_method = self.config_manager.get_api_method()
            async with BlueBubblesClient(server_url, password, api_method) as client:
                return await self.avatar_cache.get_avatar(client, chat_guid, is_group=True)
        except Exception as e:
            # Silently handle avatar fetch errors
            return None
    
    def generate_fallback_avatar(self, name: str, size: int = 40) -> Optional[bytes]:
        """Generate a fallback avatar with initials."""
        return self.avatar_cache.generate_initials_avatar(name, size)
    
    async def mark_chat_read(self, server_url: str, password: str, chat_guid: str) -> bool:
        """Mark a chat as read."""
        try:
            api_method = self.config_manager.get_api_method()
            async with BlueBubblesClient(server_url, password, api_method) as client:
                return await client.mark_chat_read(chat_guid)
        except Exception as e:
            # Silently handle mark read errors
            return False
    
    async def get_attachment(self, server_url: str, password: str, attachment_guid: str) -> Optional[bytes]:
        """Get attachment data from server or cache."""
        try:
            api_method = self.config_manager.get_api_method()
            async with BlueBubblesClient(server_url, password, api_method) as client:
                return await self.attachment_cache.get_attachment(client, attachment_guid)
        except Exception as e:
            # Silently handle attachment fetch errors
            return None
    
    def get_attachment_metadata(self, attachment_guid: str) -> Optional[Dict[str, Any]]:
        """Get cached attachment metadata."""
        return self.attachment_cache.get_cached_metadata(attachment_guid)
