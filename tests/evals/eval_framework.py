"""
Core evaluation framework for Pydantic AI agents.

This module provides the base classes and utilities for creating evaluations
that test agent behavior, tool calls, and outputs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel
from pydantic_ai import Agent
from pathlib import Path
import json
import time


@dataclass
class ToolCall:
    """Represents a tool call made by an agent."""
    name: str
    args: Dict[str, Any]
    timestamp: float
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class EvalResult:
    """Result of an evaluation."""
    passed: bool
    score: float  # 0.0 to 1.0
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    tool_calls: List[ToolCall] = field(default_factory=list)
    execution_time: float = 0.0


class EvalCase(BaseModel):
    """Defines a single evaluation case."""
    name: str
    prompt: str
    expected_tool_calls: List[Dict[str, Any]] = []
    expected_outputs: List[str] = []
    timeout: float = 30.0
    description: Optional[str] = None


class BaseEvaluator(ABC):
    """Base class for all evaluators."""
    
    def __init__(self, name: str):
        self.name = name
        self.tool_calls: List[ToolCall] = []
    
    @abstractmethod
    async def evaluate(self, agent: Agent, eval_case: EvalCase, deps: Any) -> EvalResult:
        """Evaluate an agent against an evaluation case."""
        pass
    
    def reset(self):
        """Reset evaluator state."""
        self.tool_calls.clear()


class AgentEvaluationSuite:
    """Suite for running multiple evaluations on an agent."""
    
    def __init__(self, name: str):
        self.name = name
        self.evaluators: List[BaseEvaluator] = []
        self.eval_cases: List[EvalCase] = []
    
    def add_evaluator(self, evaluator: BaseEvaluator):
        """Add an evaluator to the suite."""
        self.evaluators.append(evaluator)
    
    def add_eval_case(self, eval_case: EvalCase):
        """Add an evaluation case to the suite."""
        self.eval_cases.append(eval_case)
    
    async def run_evaluations(self, agent: Agent, deps: Any) -> List[EvalResult]:
        """Run all evaluations and return results."""
        results = []
        
        for eval_case in self.eval_cases:
            for evaluator in self.evaluators:
                evaluator.reset()
                start_time = time.time()
                
                try:
                    result = await evaluator.evaluate(agent, eval_case, deps)
                    result.execution_time = time.time() - start_time
                except Exception as e:
                    result = EvalResult(
                        passed=False,
                        score=0.0,
                        message=f"Evaluation failed: {str(e)}",
                        execution_time=time.time() - start_time
                    )
                
                results.append(result)
        
        return results
    
    def generate_report(self, results: List[EvalResult]) -> Dict[str, Any]:
        """Generate a comprehensive evaluation report."""
        total_cases = len(results)
        passed_cases = sum(1 for r in results if r.passed)
        avg_score = sum(r.score for r in results) / total_cases if total_cases > 0 else 0.0
        
        return {
            "suite_name": self.name,
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "failed_cases": total_cases - passed_cases,
            "pass_rate": passed_cases / total_cases if total_cases > 0 else 0.0,
            "average_score": avg_score,
            "total_execution_time": sum(r.execution_time for r in results),
            "results": [
                {
                    "evaluator": type(evaluator).__name__,
                    "case": eval_case.name,
                    "passed": result.passed,
                    "score": result.score,
                    "message": result.message,
                    "execution_time": result.execution_time,
                    "tool_calls_count": len(result.tool_calls),
                    "details": result.details
                }
                for result, evaluator, eval_case in zip(results, self.evaluators * len(self.eval_cases), self.eval_cases * len(self.evaluators))
            ]
        }
    
    def save_report(self, results: List[EvalResult], output_path: Union[str, Path]):
        """Save evaluation report to JSON file."""
        report = self.generate_report(results)
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)


class MockableAgentRunner:
    """Wrapper that allows capturing tool calls during agent execution."""
    
    def __init__(self, capture_tool_calls: bool = True):
        self.capture_tool_calls = capture_tool_calls
        self.captured_calls: List[ToolCall] = []
    
    async def run_agent(self, agent: Agent, prompt: str, deps: Any):
        """Run agent and optionally capture tool calls."""
        self.captured_calls.clear()
        
        if self.capture_tool_calls:
            # Wrap the dependencies to capture tool calls
            wrapped_deps = self._wrap_dependencies(deps)
            result = await agent.run(prompt, deps=wrapped_deps)
        else:
            result = await agent.run(prompt, deps=deps)
        
        return result
    
    def _wrap_dependencies(self, deps: Any) -> Any:
        """Wrap dependencies to capture tool calls."""
        # This is a simplified wrapper - in practice, you might need more sophisticated
        # wrapping based on your specific dependency injection system
        from tools.dependencies import MCPServerProvider
        
        if isinstance(deps, MCPServerProvider):
            return ToolCallCapturingDeps(deps, self.captured_calls)
        
        return deps


class ToolCallCapturingDeps:
    """Wrapper for dependencies that captures tool calls."""
    
    def __init__(self, original_deps: Any, call_list: List[ToolCall]):
        self._original_deps = original_deps
        self._call_list = call_list
    
    def __getattr__(self, name):
        attr = getattr(self._original_deps, name)
        
        # If it's an MCP server, wrap its tool calls
        if hasattr(attr, '_tool_manager'):
            return ToolCallCapturingServer(attr, self._call_list)
        
        return attr


class ToolCallCapturingServer:
    """Wrapper for MCP servers that captures tool calls."""
    
    def __init__(self, original_server: Any, call_list: List[ToolCall]):
        self._original_server = original_server
        self._call_list = call_list
    
    def __getattr__(self, name):
        attr = getattr(self._original_server, name)
        
        if name == '_tool_manager':
            return ToolCallCapturingToolManager(attr, self._call_list)
        
        return attr


class ToolCallCapturingToolManager:
    """Wrapper for tool managers that captures tool calls."""
    
    def __init__(self, original_manager: Any, call_list: List[ToolCall]):
        self._original_manager = original_manager
        self._call_list = call_list
    
    def __getattr__(self, name):
        attr = getattr(self._original_manager, name)
        
        if name == '_tools':
            return ToolCallCapturingTools(attr, self._call_list)
        
        return attr


class ToolCallCapturingTools:
    """Wrapper for tools dictionary that captures tool calls."""
    
    def __init__(self, original_tools: Dict, call_list: List[ToolCall]):
        self._original_tools = original_tools
        self._call_list = call_list
    
    def __getitem__(self, tool_name: str):
        original_tool = self._original_tools[tool_name]
        return ToolCallCapturingTool(original_tool, tool_name, self._call_list)
    
    def __contains__(self, tool_name: str):
        return tool_name in self._original_tools
    
    def get(self, tool_name: str, default=None):
        if tool_name in self._original_tools:
            return self[tool_name]
        return default


class ToolCallCapturingTool:
    """Wrapper for individual tools that captures calls."""
    
    def __init__(self, original_tool: Any, tool_name: str, call_list: List[ToolCall]):
        self._original_tool = original_tool
        self._tool_name = tool_name
        self._call_list = call_list
    
    def __getattr__(self, name):
        attr = getattr(self._original_tool, name)
        
        if name == 'fn' and callable(attr):
            return self._wrap_function(attr)
        
        return attr
    
    def _wrap_function(self, fn):
        """Wrap the function to capture calls."""
        def wrapper(**kwargs):
            start_time = time.time()
            tool_call = ToolCall(
                name=self._tool_name,
                args=kwargs.copy(),
                timestamp=start_time
            )
            
            try:
                result = fn(**kwargs)
                tool_call.result = result
                self._call_list.append(tool_call)
                return result
            except Exception as e:
                tool_call.error = str(e)
                self._call_list.append(tool_call)
                raise
        
        return wrapper