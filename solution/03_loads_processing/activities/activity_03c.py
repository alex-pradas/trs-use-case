from json import tool
from mcp import Tool
from .base import Activity, ActivityConfig, ActivityRegistry
from validators import ToolCalled, ToolNotCalled, ExtremesValidated


class Activity03C(Activity):
    """New loads with old loads comparison, unit conversion, scaling and exceeding."""

    @property
    def config(self) -> ActivityConfig:
        return ActivityConfig(
            name="03C",
            description="New loads with old loads comparison, unit conversion, no scaling and exceeding old loads",
            iterations=1,
            inputs="""I need to process some loads for ANSYS analysis.
the files are here:  /Users/alex/repos/trs-use-case/use_case_definition/data/03_C_new_loads.json
output directory for ansys files: /Users/alex/repos/trs-use-case/output
I have the following previous (old)loads to compare against: /Users/alex/repos/trs-use-case/use_case_definition/data/loads/03_old_loads.json""",
            evaluators=(
                # Tool call validations
                ToolCalled(tool_name="load_from_json"),
                ToolCalled(tool_name="convert_units"),
                ToolCalled(tool_name="scale_loads"),
                ToolCalled(tool_name="load_second_loadset"),
                ToolCalled(tool_name="compare_loadsets"),
                ToolCalled(tool_name="envelope_loadset"),
                ToolCalled(tool_name="export_to_ansys"),
                # Numerical validation of point extremes (using LoadSet data from tool call response)
                ExtremesValidated(
                    point_name="Point A",
                    component="fx",
                    extreme_type="max",
                    expected_value=6.6539613983178,
                    expected_loadcase="landing_011",
                ),
                ExtremesValidated(
                    point_name="Point A",
                    component="my",
                    extreme_type="min",
                    expected_value=0.28902923412327,
                    expected_loadcase="cruise2_098",
                ),
                ExtremesValidated(
                    point_name="Point B",
                    component="fy",
                    extreme_type="max",
                    expected_value=6.506338232562691,
                    expected_loadcase="landing_012",
                ),
            ),
        )


# Auto-register this activity when the module is imported
ActivityRegistry.register(Activity03C)
