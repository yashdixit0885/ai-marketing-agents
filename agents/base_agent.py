from abc import ABC, abstractmethod
import logging
import time
import asyncio
from utils.agent_metrics import metrics, timed_step, timed_run

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
    
    async def timed_operation(self, operation_name, func, *args, **kwargs):
        """Execute a function with timing metrics."""
        run_id = metrics.start_run(self.name, operation_name)
        start_time = time.time()
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
                
            end_time = time.time()
            metrics.end_run(run_id, "success")
            
            self.log_status(f"Completed {operation_name} in {end_time - start_time:.2f}s")
            return result
            
        except Exception as e:
            end_time = time.time()
            metrics.end_run(run_id, "error", str(e))
            
            self.log_status(f"Error in {operation_name}: {str(e)}")
            raise
    
    def get_metrics(self):
        """Get all metrics for this agent."""
        return metrics.get_agent_metrics(self.name)