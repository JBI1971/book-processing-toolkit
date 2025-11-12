"""Structure handlers for different book formats."""

from .base import BaseStructureHandler, StructureDiscoveryResult
from .chapter_based import ChapterBasedHandler
from .episode_based import EpisodeBasedHandler
from .volume_based import VolumeBasedHandler
from .modern_novel import ModernNovelHandler

__all__ = [
    'BaseStructureHandler',
    'StructureDiscoveryResult',
    'ChapterBasedHandler',
    'EpisodeBasedHandler',
    'VolumeBasedHandler',
    'ModernNovelHandler',
]
