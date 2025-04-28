"""Agent metrics module for tracking agent performance."""

import time
import asyncio
import functools
import logging
import json
from datetime import datetime
from typing import Dict, List, Callable, Any, Optional

logger = logging.getLogger(__name__)

class AgentMetrics:
    """Class for tracking and reporting agent performance metrics."""
    
    def __init__(self):
        """Initialize the metrics tracker."""
        self.metrics = {}
        self.current_run_id = None
    
    def start_run(self, agent_name: str, operation: str) -> str:
        """Start a new metrics run and return its ID."""
        run_id = f"{agent_name}_{operation}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        self.metrics[run_id] = {
            "agent": agent_name,
            "operation": operation,
            "start_time": time.time(),
            "end_time": None,
            "duration": None,
            "status": "running",
            "steps": [],
            "error": None,
        }
        self.current_run_id = run_id
        logger.debug(f"Started metrics run: {run_id}")
        return run_id
    
    def record_step(self, run_id: str, step_name: str, start_time: float, end_time: float, metadata: Optional[Dict] = None) -> None:
        """Record a step within a run."""
        if run_id not in self.metrics:
            logger.warning(f"Attempted to record step for unknown run: {run_id}")
            return
        
        step = {
            "name": step_name,
            "start_time": start_time,
            "end_time": end_time,
            "duration": end_time - start_time,
            "metadata": metadata or {}
        }
        
        self.metrics[run_id]["steps"].append(step)
        logger.debug(f"Recorded step: {step_name} for run: {run_id}")
    
    def end_run(self, run_id: str, status: str = "success", error: Optional[str] = None) -> Dict:
        """End a metrics run and return the metrics."""
        if run_id not in self.metrics:
            logger.warning(f"Attempted to end unknown run: {run_id}")
            return {}
        
        self.metrics[run_id]["end_time"] = time.time()
        self.metrics[run_id]["duration"] = self.metrics[run_id]["end_time"] - self.metrics[run_id]["start_time"]
        self.metrics[run_id]["status"] = status
        
        if error:
            self.metrics[run_id]["error"] = error
        
        if self.current_run_id == run_id:
            self.current_run_id = None
        
        logger.debug(f"Ended metrics run: {run_id} with status: {status}")
        return self.metrics[run_id]
    
    def get_metrics(self, run_id: str) -> Dict:
        """Get metrics for a specific run."""
        return self.metrics.get(run_id, {})
    
    def get_all_metrics(self) -> Dict:
        """Get all collected metrics."""
        return self.metrics
    
    def get_agent_metrics(self, agent_name: str) -> List[Dict]:
        """Get all metrics for a specific agent."""
        return [m for m in self.metrics.values() if m["agent"] == agent_name]
    
    def get_operation_metrics(self, operation: str) -> List[Dict]:
        """Get all metrics for a specific operation."""
        return [m for m in self.metrics.values() if m["operation"] == operation]
    
    def export_metrics(self, filepath: str) -> None:
        """Export all metrics to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.metrics, f, indent=2)
        logger.info(f"Exported metrics to: {filepath}")
    
    def clear_metrics(self) -> None:
        """Clear all collected metrics."""
        self.metrics = {}
        self.current_run_id = None
        logger.debug("Cleared all metrics")

# Create a singleton instance
metrics = AgentMetrics()

def timed_step(step_name: str):
    """Decorator for timing a function execution as a step in the current run."""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if metrics.current_run_id is None:
                return await func(*args, **kwargs)
            
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                end_time = time.time()
                metrics.record_step(
                    metrics.current_run_id,
                    step_name,
                    start_time,
                    end_time
                )
                return result
            except Exception as e:
                end_time = time.time()
                metrics.record_step(
                    metrics.current_run_id,
                    step_name,
                    start_time,
                    end_time,
                    {"error": str(e)}
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if metrics.current_run_id is None:
                return func(*args, **kwargs)
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                metrics.record_step(
                    metrics.current_run_id,
                    step_name,
                    start_time,
                    end_time
                )
                return result
            except Exception as e:
                end_time = time.time()
                metrics.record_step(
                    metrics.current_run_id,
                    step_name,
                    start_time,
                    end_time,
                    {"error": str(e)}
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def timed_run(agent_name: str, operation: str):
    """Decorator for timing an entire function execution as a run."""
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            run_id = metrics.start_run(agent_name, operation)
            try:
                result = await func(*args, **kwargs)
                metrics.end_run(run_id, "success")
                return result
            except Exception as e:
                metrics.end_run(run_id, "error", str(e))
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            run_id = metrics.start_run(agent_name, operation)
            try:
                result = func(*args, **kwargs)
                metrics.end_run(run_id, "success")
                return result
            except Exception as e:
                metrics.end_run(run_id, "error", str(e))
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator