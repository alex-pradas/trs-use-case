from dataclasses import dataclass
from typing import Any

from pydantic_evals.evaluators import Evaluator, EvaluatorContext
from pydantic_evals.otel import SpanQuery


@dataclass
class ToolCalled(Evaluator):
    """Simplified evaluator to check if a specific tool was called (without agent name)."""
    tool_name: str
    tool_arguments: dict[str, Any] | None = None

    def _extract_tool_arguments(self, span) -> dict[str, Any] | None:
        """Extract and parse tool_arguments from span attributes."""
        if not (hasattr(span, 'attributes') and 'tool_arguments' in span.attributes):
            return None
            
        tool_arguments_attr = span.attributes['tool_arguments']
        
        # Handle different attribute value types
        if isinstance(tool_arguments_attr, dict):
            return tool_arguments_attr
        elif isinstance(tool_arguments_attr, str):
            try:
                import json
                return json.loads(tool_arguments_attr)
            except json.JSONDecodeError:
                return None
        
        return None

    def evaluate(self, ctx: EvaluatorContext) -> bool:
        import logfire
        
        with logfire.span(f"evaluate_tool_called_{self.tool_name}"):
            # If no tool_arguments specified, use the original simple logic
            if self.tool_arguments is None:
                result = ctx.span_tree.any(
                    SpanQuery(
                        name_equals='agent run',
                        stop_recursing_when=SpanQuery(name_equals='agent run'),
                        some_descendant_has=SpanQuery(
                            name_equals='running tool',
                            has_attributes={'gen_ai.tool.name': self.tool_name},
                        ),
                    )
                )
                
                logfire.info(
                    f"ToolCalled evaluation for '{self.tool_name}' (no argument checking)",
                    tool_name=self.tool_name,
                    result=result
                )
                
                return result
            
            # If tool_arguments are specified, we need to find spans and check arguments manually
            tool_spans = ctx.span_tree.find(
                SpanQuery(
                    name_equals='running tool',
                    has_attributes={'gen_ai.tool.name': self.tool_name},
                )
            )
            
            if not tool_spans:
                logfire.info(
                    f"ToolCalled evaluation for '{self.tool_name}' - no tool spans found",
                    tool_name=self.tool_name,
                    expected_arguments=self.tool_arguments,
                    result=False
                )
                return False
            
            # Check if any of the tool calls have the expected arguments
            for span in tool_spans:
                actual_arguments = self._extract_tool_arguments(span)
                
                if actual_arguments:
                    # Check if all expected arguments match
                    arguments_match = all(
                        actual_arguments.get(key) == expected_value
                        for key, expected_value in self.tool_arguments.items()
                    )
                    
                    if arguments_match:
                        logfire.info(
                            f"ToolCalled evaluation for '{self.tool_name}' - arguments match found",
                            tool_name=self.tool_name,
                            expected_arguments=self.tool_arguments,
                            actual_arguments=actual_arguments,
                            result=True
                        )
                        return True
            
            # No matching tool call with correct arguments found
            logfire.info(
                f"ToolCalled evaluation for '{self.tool_name}' - tool was called but no matching arguments found",
                tool_name=self.tool_name,
                expected_arguments=self.tool_arguments,
                result=False
            )
            
            return False


@dataclass
class ToolNotCalled(Evaluator):
    """Evaluator to check that a specific tool was NOT called by the agent."""
    tool_name: str

    def evaluate(self, ctx: EvaluatorContext) -> bool:
        import logfire
        
        with logfire.span(f"evaluate_tool_NOT_called_{self.tool_name}"):
            # Check if the tool was called (opposite of what we want)
            tool_was_called = ctx.span_tree.any(
                SpanQuery(
                    name_equals='agent run',
                    stop_recursing_when=SpanQuery(name_equals='agent run'),
                    some_descendant_has=SpanQuery(
                        name_equals='running tool',
                        has_attributes={'gen_ai.tool.name': self.tool_name},
                    ),
                )
            )
            
            # Return the opposite - True if tool was NOT called
            result = not tool_was_called
            
            logfire.info(
                f"ToolNotCalled evaluation for '{self.tool_name}'",
                tool_name=self.tool_name,
                tool_was_called=tool_was_called,
                result=result,
                expectation="Tool should NOT be called"
            )
            
            return result


@dataclass
class ExtremesValidated(Evaluator):
    """Evaluator to validate specific point extreme values from LoadSet data in tool call response."""
    point_name: str
    component: str  # fx, fy, fz, mx, my, mz
    extreme_type: str  # max or min
    expected_value: float
    expected_loadcase: str
    tolerance: float = 0.0001

    def evaluate(self, ctx: EvaluatorContext) -> bool:
        import logfire
        
        with logfire.span(f"evaluate_loadset_extremes_{self.point_name}_{self.component}_{self.extreme_type}"):
            try:
                # First verify that export_to_ansys was called
                export_tool_called = ctx.span_tree.any(
                    SpanQuery(
                        name_equals='running tool',
                        has_attributes={'gen_ai.tool.name': 'export_to_ansys'}
                    )
                )
                
                if not export_tool_called:
                    logfire.warning("export_to_ansys tool was not called")
                    return False
                
                # Find the export_to_ansys tool call spans  
                export_spans = ctx.span_tree.find(
                    SpanQuery(
                        name_equals='running tool',
                        has_attributes={'gen_ai.tool.name': 'export_to_ansys'}
                    )
                )
                
                if not export_spans:
                    logfire.error("export_to_ansys tool span not found")
                    return False
                
                export_span = export_spans[0]  # Get the first matching span
                
                # Extract tool_response from span attributes
                tool_response = None
                if hasattr(export_span, 'attributes') and 'tool_response' in export_span.attributes:
                    tool_response_attr = export_span.attributes['tool_response']
                    
                    # Handle different attribute value types
                    if isinstance(tool_response_attr, dict):
                        tool_response = tool_response_attr
                        logfire.info("Successfully extracted tool_response as dict from span")
                    elif isinstance(tool_response_attr, str):
                        try:
                            import json
                            tool_response = json.loads(tool_response_attr)
                            logfire.info("Successfully extracted tool_response as parsed JSON from span")
                        except json.JSONDecodeError as e:
                            logfire.error(f"Failed to parse tool_response JSON: {e}")
                            return False
                    else:
                        logfire.error(f"Unexpected tool_response type: {type(tool_response_attr)}")
                        return False
                else:
                    logfire.error(
                        "tool_response not found in export_to_ansys span attributes",
                        available_attributes=list(export_span.attributes.keys()) if hasattr(export_span, 'attributes') else None
                    )
                    return False
                
                # Validate tool call was successful
                if not tool_response.get('success', False):
                    logfire.error(f"export_to_ansys tool call failed: {tool_response.get('message', 'Unknown error')}")
                    return False
                
                # Extract loadset extremes from the tool response
                loadset_extremes = tool_response.get('loadset_extremes')
                if not loadset_extremes:
                    logfire.error("No loadset_extremes found in export_to_ansys tool response")
                    return False
                
                logfire.info(
                    f"Successfully extracted LoadSet extremes for validation",
                    evaluator_type="ExtremesValidated",
                    point_name=self.point_name,
                    component=self.component,
                    extreme_type=self.extreme_type,
                    num_points=len(loadset_extremes)
                )
                
                # Validate the expected point exists
                if self.point_name not in loadset_extremes:
                    logfire.error(
                        f"Point '{self.point_name}' not found in loadset extremes",
                        available_points=list(loadset_extremes.keys())
                    )
                    return False
                
                point_data = loadset_extremes[self.point_name]
                
                # Validate the expected component exists
                if self.component not in point_data:
                    logfire.error(
                        f"Component '{self.component}' not found for point '{self.point_name}'",
                        available_components=list(point_data.keys())
                    )
                    return False
                
                component_data = point_data[self.component]
                
                # Validate the expected extreme type exists
                if self.extreme_type not in component_data:
                    logfire.error(
                        f"Extreme type '{self.extreme_type}' not found for component '{self.component}'",
                        available_extreme_types=list(component_data.keys())
                    )
                    return False
                
                extreme_data = component_data[self.extreme_type]
                actual_value = extreme_data["value"]
                actual_loadcase = extreme_data["loadcase"]
                
                # Validate the value within tolerance
                value_diff = abs(actual_value - self.expected_value)
                value_match = value_diff <= self.tolerance
                
                # Validate the load case
                loadcase_match = actual_loadcase == self.expected_loadcase
                
                result = value_match and loadcase_match
                
                logfire.info(
                    f"ExtremesValidated for {self.point_name}.{self.component}.{self.extreme_type}",
                    point_name=self.point_name,
                    component=self.component,
                    extreme_type=self.extreme_type,
                    expected_value=self.expected_value,
                    actual_value=actual_value,
                    value_diff=value_diff,
                    tolerance=self.tolerance,
                    value_match=value_match,
                    expected_loadcase=self.expected_loadcase,
                    actual_loadcase=actual_loadcase,
                    loadcase_match=loadcase_match,
                    result=result,
                )
                
                return result
                
            except Exception as e:
                logfire.error(f"Error in ExtremesValidated: {e}", exc_info=True)
                return False