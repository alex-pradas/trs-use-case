"""
Activities package for evaluation activities.

This package automatically imports all activity modules, which triggers
their auto-registration with the ActivityRegistry.
"""

# Import base classes and registry
from .base import Activity, ActivityConfig, ActivityRegistry

# Import all activity modules to trigger auto-registration
from .activity_03a import Activity03A
from .activity_03b import Activity03B
from .activity_03c import Activity03C

# Make registry available at package level
__all__ = ['Activity', 'ActivityConfig', 'ActivityRegistry', 'Activity03A', 'Activity03B', 'Activity03C']