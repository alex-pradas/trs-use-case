from .base import Activity, ActivityConfig, ActivityRegistry
from validators import ToolCalled, ToolNotCalled, ExtremesValidated


class Activity03A(Activity):
    """Activity 03A: New loads only, scaling by 1.5, no unit conversion."""
    
    @property
    def config(self) -> ActivityConfig:
        return ActivityConfig(
            name="03A",
            description="New loads only, scaling by 1.5, no unit conversion",
            iterations=1,
            inputs="""I need to process some loads for ANSYS analysis.
the files are here: /Users/alex/repos/trs-use-case/use_case_definition/data/loads/03_A_new_loads.json
output directory for ansys files: /Users/alex/repos/trs-use-case/output
I do not have any previous loads to compare against.""",
            evaluators=(
                # Tool call validations
                ToolCalled(tool_name="scale_loads", tool_arguments={"factor": 1.5}),  # Check factor(1.5) operation
                ToolCalled(tool_name="export_to_ansys"),  # Check ANSYS export
                ToolCalled(tool_name="load_from_json"),  # Check load operation
                ToolNotCalled(tool_name="convert_units"),  # Check units not converted
                ToolCalled(tool_name="envelope_loadset"),  # Check envelope operation
                
                # Numerical validation of point extremes (using LoadSet data from tool call response)
                ExtremesValidated(
                    point_name="Point A",
                    component="fx",
                    extreme_type="max",
                    expected_value=1.4958699,
                    expected_loadcase="landing_011"
                ),
                ExtremesValidated(
                    point_name="Point A", 
                    component="my",
                    extreme_type="min",
                    expected_value=0.213177015,
                    expected_loadcase="cruise2_098"
                ),
                ExtremesValidated(
                    point_name="Point B",
                    component="fy", 
                    extreme_type="max",
                    expected_value=1.462682895,
                    expected_loadcase="landing_012"
                ),
            )
        )


# Auto-register this activity when the module is imported
ActivityRegistry.register(Activity03A)