"""
BlueBubbles API Client
Handles all communication with the BlueBubbles server
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
import json

class BlueBubblesClient:
    """Async client for the BlueBubbles API."""
    
    def __init__(self, server_url: str, password: str, api_method: str = 'applescript'):
        self.server_url = server_url.rstrip('/')
        self.password = password
        self.api_method = api_method  # 'applescript' or 'private'
        self.session = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _build_url(self, endpoint: str) -> str:
        """Build a complete URL with the password parameter."""
        url = urljoin(self.server_url, endpoint)
        separator = '&' if '?' in url else '?'
        return f"{url}{separator}password={self.password}"
    
    def _add_api_method_to_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Add API method to request payload if using private API."""
        if self.api_method == 'private':
            payload = payload.copy()  # Don't modify the original
            payload['method'] = 'private-api'
        return payload
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request to the BlueBubbles server."""
        if not self.session:
            raise RuntimeError("Client not initialized. Use async context manager.")
        
        url = self._build_url(endpoint)
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.content_type == 'application/json':
                    data = await response.json()
                else:
                    text_data = await response.text()
                    data = {'data': text_data}
                
                if response.status == 200:
                    return data
                else:
                    error_msg = f"HTTP {response.status}: {data.get('message', 'Unknown error')}"
                    raise BlueBubblesAPIError(error_msg)
        
        except aiohttp.ClientError as e:
            error_msg = f"Network error: {str(e)}"
            raise BlueBubblesAPIError(error_msg)
    
    async def test_connection(self) -> bool:
        """Test if we can connect to the BlueBubbles server."""
        try:
            await self._make_request('GET', '/api/v1/server/info')
            return True
        except BlueBubblesAPIError:
            return False
    
    async def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        response = await self._make_request('GET', '/api/v1/server/info')
        return response.get('data', {})
    
    async def get_icloud_account_info(self) -> Dict[str, Any]:
        """Get iCloud account information."""
        response = await self._make_request('GET', '/api/v1/icloud/account')
        return response.get('data', {})
    
    async def get_server_statistics(self) -> Dict[str, Any]:
        """Get server statistics (message counts, etc.)."""
        response = await self._make_request('GET', '/api/v1/server/statistics/totals')
        return response.get('data', {})
    
    async def get_chats(self, limit: int = 100, offset: int = 0, with_data: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get chats from the server."""
        payload = {
            'limit': limit,
            'offset': offset
        }
        
        if with_data:
            payload['with'] = with_data
        
        response = await self._make_request(
            'POST', 
            '/api/v1/chat/query',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        return response.get('data', [])
    
    async def get_chat_messages(self, chat_guid: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get messages for a specific chat."""
        endpoint = f'/api/v1/chat/{chat_guid}/message'
        # Include attachment data in the response
        params = f'?limit={limit}&offset={offset}&with=handle,attachment&sort=DESC'
        
        response = await self._make_request('GET', endpoint + params)
        return response.get('data', [])
    
    async def send_message(self, chat_guid: str, message: str) -> Dict[str, Any]:
        """Send a text message to a chat."""
        payload = {
            'chatGuid': chat_guid,
            'message': message
        }
        payload = self._add_api_method_to_payload(payload)
        
        response = await self._make_request(
            'POST',
            '/api/v1/message/text',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        return response.get('data', {})
    
    async def create_chat(self, addresses: List[str], message: Optional[str] = None) -> Dict[str, Any]:
        """Create a new chat."""
        payload = {
            'addresses': addresses
        }
        
        if message:
            payload['message'] = message
        
        payload = self._add_api_method_to_payload(payload)
        
        try:
            response = await self._make_request(
                'POST',
                '/api/v1/chat/new',
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            return response.get('data', {})
        except BlueBubblesAPIError as e:
            raise
        except Exception as e:
            raise
    
    async def mark_chat_read(self, chat_guid: str) -> bool:
        """Mark a chat as read."""
        try:
            await self._make_request('POST', f'/api/v1/chat/{chat_guid}/read')
            return True
        except BlueBubblesAPIError:
            return False
    
    async def send_attachment(self, chat_guid: str, file_path: str, message: str = "") -> Dict[str, Any]:
        """Send an attachment to a chat."""
        import os
        from aiohttp import FormData
        
        if not os.path.exists(file_path):
            raise BlueBubblesAPIError(f"File not found: {file_path}")
        
        # Create form data
        data = FormData()
        data.add_field('chatGuid', chat_guid)
        if message:
            data.add_field('message', message)
        
        # Add API method for private API
        if self.api_method == 'private':
            data.add_field('method', 'private-api')
        
        # Add the file
        with open(file_path, 'rb') as f:
            data.add_field('attachment', f, filename=os.path.basename(file_path))
            
            response = await self._make_request(
                'POST',
                '/api/v1/message/attachment',
                data=data
            )
        
        return response.get('data', {})
    
    async def send_reaction(self, message_guid: str, reaction_type: str, chat_guid: str = None) -> Dict[str, Any]:
        """Send a reaction to a message."""
        payload = {
            'selectedMessageGuid': message_guid,
            'reaction': reaction_type,
            'partIndex': 0
        }
        
        # Add chat GUID if provided
        if chat_guid:
            payload['chatGuid'] = chat_guid
        
        payload = self._add_api_method_to_payload(payload)
        
        # print(f"🌐 Sending reaction request to /api/v1/message/react")
        # print(f"🌐 Payload: {payload}")
        
        response = await self._make_request(
            'POST',
            '/api/v1/message/react',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        # print(f"🌐 Raw response: {response}")
        return response.get('data', {})
    
    async def remove_reaction(self, message_guid: str, chat_guid: str = None) -> Dict[str, Any]:
        """Remove a reaction from a message."""
        payload = {
            'selectedMessageGuid': message_guid,
            'reaction': '',
            'partIndex': 0
        }
        
        # Add chat GUID if provided  
        if chat_guid:
            payload['chatGuid'] = chat_guid
        
        payload = self._add_api_method_to_payload(payload)
        
        # print(f"🌐 Removing reaction request to /api/v1/message/react")
        # print(f"🌐 Payload: {payload}")
        
        response = await self._make_request(
            'POST',
            '/api/v1/message/react',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        # print(f"🌐 Raw response: {response}")
        return response.get('data', {})
    
    async def send_typing_indicator(self, chat_guid: str, typing: bool = True) -> bool:
        """Send typing indicator to a chat."""
        try:
            payload = {
                'chatGuid': chat_guid,
                'display': typing
            }
            payload = self._add_api_method_to_payload(payload)
            
            await self._make_request(
                'POST',
                '/api/v1/chat/typing',
                json=payload,
                headers={'Content-Type': 'application/json'}
            )
            return True
        except BlueBubblesAPIError:
            return False
    
    async def unsend_message(self, message_guid: str) -> Dict[str, Any]:
        """Unsend a message."""
        payload = {
            'messageGuid': message_guid
        }
        payload = self._add_api_method_to_payload(payload)
        
        response = await self._make_request(
            'POST',
            '/api/v1/message/unsend',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        return response.get('data', {})
    
    async def edit_message(self, message_guid: str, new_text: str) -> Dict[str, Any]:
        """Edit a message."""
        payload = {
            'messageGuid': message_guid,
            'editedMessage': new_text
        }
        payload = self._add_api_method_to_payload(payload)
        
        response = await self._make_request(
            'POST',
            '/api/v1/message/edit',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        return response.get('data', {})
    
    async def get_contact_avatar(self, address: str) -> bytes:
        """Get contact avatar/profile picture."""
        response = await self._make_request(
            'GET',
            f'/api/v1/contact/{address}',
            params={'password': self.password}
        )
        
        # The contact endpoint returns contact info including base64 avatar
        contact_data = response.get('data', {})
        avatar_b64 = contact_data.get('avatar')
        
        if avatar_b64:
            import base64
            return base64.b64decode(avatar_b64)
        return None
    
    async def get_chat_icon(self, chat_guid: str) -> bytes:
        """Get group chat icon."""
        try:
            # This endpoint returns the raw image data
            async with self.session.get(
                f"{self.base_url}/api/v1/chat/{chat_guid}/icon",
                params={'password': self.password}
            ) as response:
                if response.status == 200:
                    return await response.read()
                return None
        except Exception:
            return None
    
    async def mark_chat_read(self, chat_guid: str) -> bool:
        """Mark a chat as read."""
        try:
            await self._make_request(
                'POST',
                f'/api/v1/chat/{chat_guid}/read',
                params={'password': self.password}
            )
            return True
        except BlueBubblesAPIError:
            return False

    async def get_attachment(self, attachment_guid: str) -> bytes:
        """Download attachment binary data."""
        try:
            # This endpoint returns the raw attachment data
            async with self.session.get(
                f"{self.server_url}/api/v1/attachment/{attachment_guid}/download",
                params={'password': self.password}
            ) as response:
                if response.status == 200:
                    return await response.read()
                return None
        except Exception:
            return None

    async def get_attachment_info(self, attachment_guid: str) -> Dict[str, Any]:
        """Get attachment metadata."""
        try:
            response = await self._make_request(
                'GET',
                f'/api/v1/attachment/{attachment_guid}',
                params={'password': self.password}
            )
            return response.get('data', {})
        except BlueBubblesAPIError:
            return {}

class BlueBubblesAPIError(Exception):
    """Exception raised for BlueBubbles API errors."""
    pass
