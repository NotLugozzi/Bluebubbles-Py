"""Avatar cache service for storing and retrieving contact avatars."""

import os
import hashlib
from typing import Optional
from pathlib import Path
import asyncio
from ..api.client import BlueBubblesClient


class AvatarCache:
    """Manages caching of contact avatars and group chat icons."""
    
    def __init__(self, cache_dir: str = None):
        """Initialize the avatar cache."""
        if cache_dir is None:
            # Use XDG cache directory or fallback to home
            cache_base = os.environ.get('XDG_CACHE_HOME', 
                                      os.path.expanduser('~/.cache'))
            cache_dir = os.path.join(cache_base, 'bluebubbles', 'avatars')
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for this session
        self._memory_cache = {}
    
    def _get_cache_path(self, identifier: str, is_group: bool = False) -> Path:
        """Get the cache file path for an identifier."""
        # Create a safe filename from the identifier
        safe_name = hashlib.md5(identifier.encode()).hexdigest()
        prefix = "group_" if is_group else "contact_"
        return self.cache_dir / f"{prefix}{safe_name}.jpg"
    
    def get_cached_avatar(self, identifier: str, is_group: bool = False) -> Optional[bytes]:
        """Get cached avatar data if it exists."""
        # Check memory cache first
        cache_key = f"{'group' if is_group else 'contact'}:{identifier}"
        if cache_key in self._memory_cache:
            return self._memory_cache[cache_key]
        
        # Check disk cache
        cache_path = self._get_cache_path(identifier, is_group)
        if cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    data = f.read()
                    # Store in memory cache for quick access
                    self._memory_cache[cache_key] = data
                    return data
            except Exception:
                # If file is corrupted, remove it
                cache_path.unlink(missing_ok=True)
        
        return None
    
    def cache_avatar(self, identifier: str, avatar_data: bytes, is_group: bool = False):
        """Cache avatar data to disk and memory."""
        if not avatar_data:
            return
        
        cache_key = f"{'group' if is_group else 'contact'}:{identifier}"
        cache_path = self._get_cache_path(identifier, is_group)
        
        try:
            # Save to disk
            with open(cache_path, 'wb') as f:
                f.write(avatar_data)
            
            # Save to memory cache
            self._memory_cache[cache_key] = avatar_data
        except Exception as e:
            print(f"Failed to cache avatar for {identifier}: {e}")
    
    async def get_avatar(self, client: BlueBubblesClient, identifier: str, 
                        is_group: bool = False) -> Optional[bytes]:
        """Get avatar, from cache or by fetching from server."""
        # Try cache first
        cached = self.get_cached_avatar(identifier, is_group)
        if cached:
            return cached
        
        # Fetch from server
        try:
            if is_group:
                avatar_data = await client.get_chat_icon(identifier)
            else:
                avatar_data = await client.get_contact_avatar(identifier)
            
            if avatar_data:
                self.cache_avatar(identifier, avatar_data, is_group)
                return avatar_data
        except Exception as e:
            print(f"Failed to fetch avatar for {identifier}: {e}")
        
        return None
    
    def clear_cache(self):
        """Clear all cached avatars."""
        # Clear memory cache
        self._memory_cache.clear()
        
        # Clear disk cache
        try:
            for file_path in self.cache_dir.glob("*"):
                if file_path.is_file():
                    file_path.unlink()
        except Exception as e:
            print(f"Failed to clear avatar cache: {e}")
    
    def generate_initials_avatar(self, name: str, size: int = 40) -> bytes:
        """Generate a simple initials-based avatar as fallback."""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io
        except ImportError:
            # PIL not available, return None - will use default icon
            return None
            
        try:
            # Get initials (up to 2 characters)
            words = name.strip().split()
            if len(words) >= 2:
                initials = words[0][0].upper() + words[-1][0].upper()
            elif len(words) == 1 and words[0]:
                initials = words[0][0].upper()
            else:
                initials = "?"
            
            # Generate a color based on the name hash
            import hashlib
            name_hash = hashlib.md5(name.encode()).hexdigest()
            
            # Use hash to pick a color from a pleasant palette
            colors = [
                '#007AFF',  # Blue
                '#34C759',  # Green  
                '#FF9500',  # Orange
                '#FF3B30',  # Red
                '#AF52DE',  # Purple
                '#FF2D92',  # Pink
                '#5AC8FA',  # Light Blue
                '#FFCC00',  # Yellow
                '#FF6B35',  # Red Orange
                '#32D74B',  # Light Green
            ]
            
            color_index = int(name_hash[:2], 16) % len(colors)
            bg_color = colors[color_index]
            
            # Create image
            img = Image.new('RGB', (size, size), color=bg_color)
            draw = ImageDraw.Draw(img)
            
            # Try to use a nice font, fallback to default
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", size//2)
            except:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", size//2)
                except:
                    font = ImageFont.load_default()
            
            # Get text bounding box and center it
            bbox = draw.textbbox((0, 0), initials, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = (size - text_width) // 2
            y = (size - text_height) // 2
            
            draw.text((x, y), initials, fill='white', font=font)
            
            # Convert to bytes
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            
            return buffer.getvalue()
            
        except Exception as e:
            # Handle any errors in avatar generation
            return None