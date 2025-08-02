from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, List, Dict, Type
from pydantic_evals import Case, Dataset


@dataclass
class ActivityConfig:
    """Configuration for an evaluation activity."""
    name: str
    description: str
    inputs: str
    evaluators: Tuple
    iterations: int = 10


class Activity(ABC):
    """Base class for all evaluation activities."""
    
    @property
    @abstractmethod
    def config(self) -> ActivityConfig:
        """Return the configuration for this activity."""
        pass
    
    def create_dataset(self) -> Dataset:
        """Create a dataset for this activity."""
        config = self.config
        cases = [
            Case(
                name=f"Activity {config.name} - iteration {i}",
                inputs=config.inputs,
            ) for i in range(1, config.iterations + 1)
        ]
        return Dataset(cases=cases, evaluators=config.evaluators)


class ActivityRegistry:
    """Registry for all available activities."""
    
    _activities: Dict[str, Type[Activity]] = {}
    
    @classmethod
    def register(cls, activity_class: Type[Activity]) -> None:
        """Register an activity class."""
        # Create a temporary instance to get the config name
        temp_instance = activity_class()
        name = temp_instance.config.name
        cls._activities[name] = activity_class
        
    @classmethod
    def get(cls, name: str) -> Activity:
        """Get an activity instance by name."""
        if name not in cls._activities:
            available = list(cls._activities.keys())
            raise ValueError(f"Activity '{name}' not found. Available activities: {available}")
        return cls._activities[name]()
    
    @classmethod
    def list_activities(cls) -> List[str]:
        """List all registered activity names."""
        return list(cls._activities.keys())
    
    @classmethod
    def create_dataset(cls, name: str) -> Dataset:
        """Create a dataset for the specified activity."""
        activity = cls.get(name)
        return activity.create_dataset()
    
    @classmethod
    def get_evaluators(cls, name: str) -> Tuple:
        """Get evaluators for the specified activity."""
        activity = cls.get(name)
        return activity.config.evaluators