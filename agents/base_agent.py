from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, name, description):
        self.name = name
        self.description = description
        logger.info(f"Initialized {self.name} agent")
    
    @abstractmethod
    async def run(self, *args, **kwargs):
        """Main execution method to be implemented by all agents."""
        pass
    
    @abstractmethod
    async def process(self, data):
        """Process the input data."""
        pass
    
    def log_status(self, message):
        """Log agent status."""
        logger.info(f"[{self.name}] {message}")