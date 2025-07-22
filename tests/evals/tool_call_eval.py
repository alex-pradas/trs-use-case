"""
Tool call evaluator for testing agent tool usage.

This module provides evaluators specifically for testing that agents
call the correct tools with the expected parameters.
"""

from typing import Any, Dict, List, Optional, Callable
from .eval_framework import BaseEvaluator, EvalCase, EvalResult, ToolCall, MockableAgentRunner
from pydantic_ai import Agent
import re


class ToolCallEvaluator(BaseEvaluator):
    """Evaluator that checks if specific tools are called with expected parameters."""
    
    def __init__(
        self, 
        name: str = "ToolCallEvaluator",
        strict_mode: bool = True,
        allow_extra_calls: bool = True
    ):
        super().__init__(name)
        self.strict_mode = strict_mode  # If True, parameters must match exactly
        self.allow_extra_calls = allow_extra_calls  # If True, allows additional tool calls
        self.runner = MockableAgentRunner(capture_tool_calls=True)
    
    async def evaluate(self, agent: Agent, eval_case: EvalCase, deps: Any) -> EvalResult:
        """Evaluate if the agent makes the expected tool calls."""
        
        # Run the agent and capture tool calls
        try:
            result = await self.runner.run_agent(agent, eval_case.prompt, deps)
            captured_calls = self.runner.captured_calls.copy()
        except Exception as e:
            return EvalResult(
                passed=False,
                score=0.0,
                message=f"Agent execution failed: {str(e)}",
                tool_calls=[]
            )
        
        # Evaluate the captured tool calls
        return self._evaluate_tool_calls(captured_calls, eval_case.expected_tool_calls, result.output)
    
    def _evaluate_tool_calls(
        self, 
        actual_calls: List[ToolCall], 
        expected_calls: List[Dict[str, Any]],
        agent_output: str
    ) -> EvalResult:
        """Evaluate actual tool calls against expected calls."""
        
        if not expected_calls:
            return EvalResult(
                passed=True,
                score=1.0,
                message="No tool call expectations specified",
                tool_calls=actual_calls
            )
        
        score = 0.0
        total_expected = len(expected_calls)
        matched_calls = 0
        detailed_results = []
        
        for expected in expected_calls:
            tool_name = expected.get("name", expected.get("tool"))
            expected_args = expected.get("args", expected.get("parameters", {}))
            
            # Find matching tool calls
            matches = self._find_matching_calls(actual_calls, tool_name, expected_args)
            
            if matches:
                matched_calls += 1
                best_match = matches[0]  # Take the first/best match
                detailed_results.append({
                    "expected_tool": tool_name,
                    "expected_args": expected_args,
                    "actual_call": {
                        "name": best_match.name,
                        "args": best_match.args,
                        "result": best_match.result
                    },
                    "matched": True,
                    "score": self._calculate_call_score(best_match, tool_name, expected_args)
                })
            else:
                detailed_results.append({
                    "expected_tool": tool_name,
                    "expected_args": expected_args,
                    "actual_call": None,
                    "matched": False,
                    "score": 0.0
                })
        
        # Calculate overall score
        if total_expected > 0:
            base_score = matched_calls / total_expected
            
            # Apply penalties for extra calls if not allowed
            if not self.allow_extra_calls and len(actual_calls) > total_expected:
                penalty = (len(actual_calls) - total_expected) * 0.1
                score = max(0.0, base_score - penalty)
            else:
                score = base_score
        else:
            score = 1.0
        
        # Determine if evaluation passed
        passed = score >= 0.8 and matched_calls == total_expected
        
        # Create summary message
        message = self._create_summary_message(
            matched_calls, total_expected, len(actual_calls), score
        )
        
        return EvalResult(
            passed=passed,
            score=score,
            message=message,
            details={
                "expected_calls": len(expected_calls),
                "actual_calls": len(actual_calls),
                "matched_calls": matched_calls,
                "call_details": detailed_results,
                "agent_output": agent_output
            },
            tool_calls=actual_calls
        )
    
    def _find_matching_calls(
        self, 
        actual_calls: List[ToolCall], 
        expected_name: str, 
        expected_args: Dict[str, Any]
    ) -> List[ToolCall]:
        """Find tool calls that match the expected name and arguments."""
        matches = []
        
        for call in actual_calls:
            if call.name == expected_name:
                if self._args_match(call.args, expected_args):
                    matches.append(call)
        
        return matches
    
    def _args_match(self, actual_args: Dict[str, Any], expected_args: Dict[str, Any]) -> bool:
        """Check if actual arguments match expected arguments."""
        if not expected_args:  # No specific args expected
            return True
        
        for key, expected_value in expected_args.items():
            if key not in actual_args:
                return False
            
            actual_value = actual_args[key]
            
            if not self._values_match(actual_value, expected_value):
                return False
        
        return True
    
    def _values_match(self, actual: Any, expected: Any) -> bool:
        """Check if two values match, with flexible comparison."""
        if self.strict_mode:
            return actual == expected
        
        # Flexible matching
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            # Allow small numerical differences
            return abs(actual - expected) < 0.001
        
        if isinstance(expected, str) and isinstance(actual, str):
            # Allow case-insensitive string matching
            return expected.lower() == actual.lower()
        
        return actual == expected
    
    def _calculate_call_score(
        self, 
        call: ToolCall, 
        expected_name: str, 
        expected_args: Dict[str, Any]
    ) -> float:
        """Calculate a score for how well a call matches expectations."""
        if call.name != expected_name:
            return 0.0
        
        if not expected_args:
            return 1.0
        
        matching_args = 0
        total_args = len(expected_args)
        
        for key, expected_value in expected_args.items():
            if key in call.args and self._values_match(call.args[key], expected_value):
                matching_args += 1
        
        return matching_args / total_args if total_args > 0 else 1.0
    
    def _create_summary_message(
        self, 
        matched: int, 
        expected: int, 
        actual_total: int, 
        score: float
    ) -> str:
        """Create a human-readable summary message."""
        if matched == expected and expected > 0:
            return f"✅ All {expected} expected tool calls matched (score: {score:.2f})"
        elif matched > 0:
            return f"⚠️ {matched}/{expected} expected tool calls matched (score: {score:.2f})"
        else:
            return f"❌ No expected tool calls matched. Found {actual_total} actual calls (score: {score:.2f})"


class SpecificToolEvaluator(ToolCallEvaluator):
    """Evaluator for testing a specific tool call with specific parameters."""
    
    def __init__(
        self, 
        tool_name: str, 
        expected_args: Dict[str, Any], 
        name: Optional[str] = None
    ):
        super().__init__(name or f"SpecificTool_{tool_name}")
        self.tool_name = tool_name
        self.expected_args = expected_args
    
    async def evaluate(self, agent: Agent, eval_case: EvalCase, deps: Any) -> EvalResult:
        """Evaluate if the agent calls the specific tool with expected arguments."""
        
        # Override the eval_case expected calls with our specific expectation
        eval_case.expected_tool_calls = [{
            "name": self.tool_name,
            "args": self.expected_args
        }]
        
        return await super().evaluate(agent, eval_case, deps)


class ScaleLoadsEvaluator(SpecificToolEvaluator):
    """Specialized evaluator for the scale_loads tool with factor parameter."""
    
    def __init__(self, expected_factor: float, name: Optional[str] = None):
        super().__init__(
            tool_name="scale_loads",
            expected_args={"factor": expected_factor},
            name=name or f"ScaleLoads_Factor_{expected_factor}"
        )
        self.expected_factor = expected_factor
    
    async def evaluate(self, agent: Agent, eval_case: EvalCase, deps: Any) -> EvalResult:
        """Evaluate if scale_loads is called with the expected factor."""
        result = await super().evaluate(agent, eval_case, deps)
        
        # Add specific messaging for scale_loads
        if result.passed:
            result.message = f"✅ scale_loads called with factor {self.expected_factor} as expected"
        else:
            # Check if scale_loads was called at all
            scale_calls = [call for call in result.tool_calls if call.name == "scale_loads"]
            if scale_calls:
                actual_factors = [call.args.get("factor", "unknown") for call in scale_calls]
                result.message = f"❌ scale_loads called with factor(s) {actual_factors}, expected {self.expected_factor}"
            else:
                result.message = f"❌ scale_loads was not called (expected factor {self.expected_factor})"
        
        return result


class ToolSequenceEvaluator(BaseEvaluator):
    """Evaluator that checks if tools are called in a specific sequence."""
    
    def __init__(self, expected_sequence: List[str], name: str = "ToolSequenceEvaluator"):
        super().__init__(name)
        self.expected_sequence = expected_sequence
        self.runner = MockableAgentRunner(capture_tool_calls=True)
    
    async def evaluate(self, agent: Agent, eval_case: EvalCase, deps: Any) -> EvalResult:
        """Evaluate if tools are called in the expected sequence."""
        
        try:
            result = await self.runner.run_agent(agent, eval_case.prompt, deps)
            captured_calls = self.runner.captured_calls.copy()
        except Exception as e:
            return EvalResult(
                passed=False,
                score=0.0,
                message=f"Agent execution failed: {str(e)}",
                tool_calls=[]
            )
        
        # Extract the sequence of tool names
        actual_sequence = [call.name for call in captured_calls]
        
        # Check if the expected sequence appears in the actual sequence
        score = self._calculate_sequence_score(actual_sequence, self.expected_sequence)
        passed = score >= 0.8
        
        message = self._create_sequence_message(actual_sequence, self.expected_sequence, score)
        
        return EvalResult(
            passed=passed,
            score=score,
            message=message,
            details={
                "expected_sequence": self.expected_sequence,
                "actual_sequence": actual_sequence,
                "sequence_found": self._find_subsequence(actual_sequence, self.expected_sequence)
            },
            tool_calls=captured_calls
        )
    
    def _calculate_sequence_score(self, actual: List[str], expected: List[str]) -> float:
        """Calculate how well the actual sequence matches the expected sequence."""
        if not expected:
            return 1.0
        
        if self._find_subsequence(actual, expected):
            return 1.0
        
        # Partial credit for having some of the expected tools
        expected_set = set(expected)
        actual_set = set(actual)
        overlap = len(expected_set.intersection(actual_set))
        
        return overlap / len(expected_set) if expected_set else 0.0
    
    def _find_subsequence(self, actual: List[str], expected: List[str]) -> bool:
        """Check if expected sequence appears as a subsequence in actual."""
        if not expected:
            return True
        
        i = 0  # Index for expected sequence
        for tool in actual:
            if i < len(expected) and tool == expected[i]:
                i += 1
                if i == len(expected):
                    return True
        
        return False
    
    def _create_sequence_message(self, actual: List[str], expected: List[str], score: float) -> str:
        """Create a summary message for sequence evaluation."""
        if score >= 0.8:
            return f"✅ Expected tool sequence found: {' → '.join(expected)}"
        else:
            return f"❌ Expected sequence {' → '.join(expected)} not found in {' → '.join(actual)} (score: {score:.2f})"