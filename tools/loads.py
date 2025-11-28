from typing import Literal
from pathlib import Path
from os import PathLike
import json
import re
from pydantic import BaseModel, ValidationError

# Type aliases for units
ForceUnit = Literal["N", "kN", "lbf", "klbf"]
MomentUnit = Literal["Nm", "kNm", "lbf-ft"]


class ComparisonRow(BaseModel):
    """
    ComparisonRow represents one row in a LoadSet comparison table.
    Each row compares a specific point/component/type combination between two LoadSets.
    """

    point_name: str
    component: Literal["fx", "fy", "fz", "mx", "my", "mz"]
    type: Literal["max", "min"]
    loadset1_value: float
    loadset2_value: float
    loadset1_loadcase: str
    loadset2_loadcase: str
    abs_diff: float
    pct_diff: float  # Percentage difference relative to loadset1


class LoadSetCompare(BaseModel):
    """
    LoadSetCompare contains the results of comparing two LoadSets.
    Provides tabular comparison data and export functionality.
    """

    loadset1_metadata: dict
    loadset2_metadata: dict
    comparison_rows: list[ComparisonRow]

    def to_dict(self) -> dict:
        """
        Convert LoadSetCompare to dictionary format.

        Returns:
            dict: Dictionary representation of the comparison
        """
        return {
            "report_metadata": {
                "loadcases_info": {
                    "loadset1": self.loadset1_metadata,
                    "loadset2": self.loadset2_metadata,
                },
            },
            "comparisons": [row.model_dump() for row in self.comparison_rows],
        }

    def to_json(self, indent: int = 2) -> str:
        """
        Export LoadSetCompare to JSON string.

        Args:
            indent: JSON indentation level

        Returns:
            str: JSON representation of the comparison
        """
        return json.dumps(self.to_dict(), indent=indent)

    def new_exceeds_old(self) -> bool:
        """
        Check if loadset2 (new) exceeds loadset1 (old) envelope in every component comparison.

        For the new loads to be considered more critical than the old loads, every single
        component comparison must show that loadset2 exceeds loadset1's bounds:
        - For "max" type: loadset2_value > loadset1_value (higher maximum)
        - For "min" type: loadset2_value < loadset1_value (lower minimum, more negative)

        Returns:
            bool: True if new loads should be considered for analysis (loadset2 exceeds 
                  loadset1 envelope in all comparisons), False if previous loads are more 
                  critical (loadset2 is enveloped by loadset1 in any comparison)
        """
        if not self.comparison_rows:
            return False
        
        for row in self.comparison_rows:
            if row.type == "max":
                # For maximum values, loadset2 must be greater than loadset1
                if row.loadset2_value <= row.loadset1_value:
                    return False
            elif row.type == "min":
                # For minimum values, loadset2 must be less than loadset1 (more negative)
                if row.loadset2_value >= row.loadset1_value:
                    return False
        
        return True

    def generate_comparison_report(
        self,
        output_dir: PathLike,
        report_name: str = "comparison_report",
        image_format: str = "png",
        indent: int = 2,
    ) -> Path:
        """
        Export complete comparison report including JSON data and chart images.

        Creates a comprehensive report with:
        - JSON file containing comparison data and generated chart filenames
        - Chart image files for each point comparison

        Args:
            output_dir: Directory to save the report files
            report_name: Base name for the report files (default: "comparison_report")
            image_format: Image format for charts (png, svg)
            indent: JSON indentation level

        Returns:
            Path: Path to the generated JSON report file

        Raises:
            ImportError: If matplotlib is not available
            FileNotFoundError: If output directory doesn't exist and can't be created
            ValueError: If report generation fails
        """
        from pathlib import Path
        import json

        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        if not output_path.is_dir():
            raise FileNotFoundError(f"Output path exists but is not a directory: {output_dir}")

        # Generate chart images in the same directory
        try:
            chart_files = self.generate_range_charts(
                output_dir=output_path,
                image_format=image_format,
                as_base64=False
            )
        except Exception as e:
            raise ValueError(f"Failed to generate charts: {e}")

        # Get base comparison data
        comparison_data = self.to_dict()
        
        # Add chart metadata to the comparison data
        chart_metadata = {}
        for point_name, file_path in chart_files.items():
            # Convert Path to relative filename for portability
            if isinstance(file_path, Path):
                chart_metadata[point_name] = file_path.name
            else:
                chart_metadata[point_name] = str(file_path)

        # Add chart information and envelope check to existing report metadata
        comparison_data["report_metadata"].update({
            "chart_files": chart_metadata,
            "image_format": image_format,
            "new_exceeds_old": self.new_exceeds_old(),
            "total_comparisons": len(self.comparison_rows),
            "points_analyzed": len(set(row.point_name for row in self.comparison_rows)),
        })

        # Write JSON report file
        json_filename = f"{report_name}.json"
        json_path = output_path / json_filename
        
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(comparison_data, f, indent=indent)
        except Exception as e:
            raise ValueError(f"Failed to write JSON report: {e}")

        return json_path

    def generate_range_charts(
        self,
        output_dir: PathLike | None = None,
        image_format: str = "png",
        as_base64: bool = False,
    ) -> dict[str, Path | str]:
        """
        Generate range bar chart images comparing LoadSets for each point.

        Creates dual subplot charts showing force and moment ranges with bars
        representing the min-to-max range for each component.

        Args:
            output_dir: Directory to save the generated images (required if as_base64=False)
            image_format: Image format (png, svg)
            as_base64: If True, return base64-encoded strings instead of saving files

        Returns:
            dict: If as_base64=False, mapping of point names to generated image file paths.
                  If as_base64=True, mapping of point names to base64-encoded image strings.

        Raises:
            ImportError: If matplotlib is not available
            FileNotFoundError: If output directory doesn't exist and can't be created (when as_base64=False)
            ValueError: If output_dir is None and as_base64=False
        """
        try:
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend to avoid GUI threading issues
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches
        except ImportError:
            raise ImportError("matplotlib is required for image generation")

        from pathlib import Path

        # Validate parameters
        if not as_base64 and output_dir is None:
            raise ValueError("output_dir is required when as_base64=False")
        
        # Validate image format
        supported_formats = ["png", "svg"]
        if image_format not in supported_formats:
            raise ValueError(f"Unsupported image format '{image_format}'. Supported formats: {supported_formats}")

        # Handle output directory for file saving
        output_path: Path | None = None
        if not as_base64:
            assert output_dir is not None  # Already validated above
            output_path = Path(output_dir)
            # Create output directory if it doesn't exist
            if not output_path.exists():
                output_path.mkdir(parents=True, exist_ok=True)
            elif not output_path.is_dir():
                raise FileNotFoundError(
                    f"Output path exists but is not a directory: {output_dir}"
                )

        # Group comparison rows by point
        points_data = {}
        for row in self.comparison_rows:
            if row.point_name not in points_data:
                points_data[row.point_name] = []
            points_data[row.point_name].append(row)

        generated_files = {}

        for point_name, rows in points_data.items():
            # Create figure with dual subplots - narrower width
            fig, (ax_forces, ax_moments) = plt.subplots(1, 2, figsize=(8, 6))
            fig.suptitle(
                f"{point_name}: Forces vs Moments Comparison",
                fontsize=14,
                fontweight="bold",
            )

            # Process data for forces and moments
            force_data = self._extract_component_ranges(rows, ["fx", "fy", "fz"])
            moment_data = self._extract_component_ranges(rows, ["mx", "my", "mz"])

            # Create force subplot
            if force_data:
                self._create_range_subplot(
                    ax_forces,
                    force_data,
                    "Forces",
                    self.loadset1_metadata.get("units", {}).get("forces", "N"),
                )
            else:
                ax_forces.text(
                    0.5,
                    0.5,
                    "No force data",
                    ha="center",
                    va="center",
                    transform=ax_forces.transAxes,
                )
                ax_forces.set_title("Forces")

            # Create moment subplot
            if moment_data:
                self._create_range_subplot(
                    ax_moments,
                    moment_data,
                    "Moments",
                    self.loadset1_metadata.get("units", {}).get("moments", "Nm"),
                )
            else:
                ax_moments.text(
                    0.5,
                    0.5,
                    "No moment data",
                    ha="center",
                    va="center",
                    transform=ax_moments.transAxes,
                )
                ax_moments.set_title("Moments")

            # Add legend
            loadset1_name = self.loadset1_metadata.get("name", "LoadSet 1")
            loadset2_name = self.loadset2_metadata.get("name", "LoadSet 2")

            loadset1_patch = mpatches.Patch(
                color="lightgrey", alpha=1.0, label=loadset1_name
            )
            loadset2_normal_patch = mpatches.Patch(
                color="darkgrey", alpha=1.0, label=f"{loadset2_name} (within range)"
            )
            loadset2_exceed_patch = mpatches.Patch(
                color="maroon", alpha=1.0, label=f"{loadset2_name} (exceeds range)"
            )
            fig.legend(
                handles=[loadset1_patch, loadset2_normal_patch, loadset2_exceed_patch],
                loc="upper center",
                bbox_to_anchor=(0.5, 0.02),
                ncol=3,
            )

            # Adjust layout and save
            plt.tight_layout()
            plt.subplots_adjust(top=0.85, bottom=0.15)

            if as_base64:
                # Generate base64 string
                import io
                import base64

                buffer = io.BytesIO()
                plt.savefig(buffer, format=image_format, dpi=300, bbox_inches="tight")
                buffer.seek(0)

                # Convert to base64
                image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                generated_files[point_name] = image_base64

                buffer.close()
            else:
                # Save to file
                assert (
                    output_path is not None
                )  # This should never be None when as_base64=False
                safe_point_name = self._sanitize_filename(point_name)
                filename = f"{safe_point_name}_ranges.{image_format}"
                file_path = output_path / filename

                plt.savefig(file_path, dpi=300, bbox_inches="tight")
                generated_files[point_name] = file_path

            plt.close()

        return generated_files

    def _extract_component_ranges(
        self, rows: list[ComparisonRow], components: list[str]
    ) -> dict:
        """
        Extract min/max ranges for specified components from comparison rows.

        Args:
            rows: List of ComparisonRow objects for a point
            components: List of component names to extract

        Returns:
            dict: Component data with min/max values for both LoadSets
        """
        component_data = {}

        for component in components:
            # Find max and min rows for this component
            max_row = next(
                (
                    row
                    for row in rows
                    if row.component == component and row.type == "max"
                ),
                None,
            )
            min_row = next(
                (
                    row
                    for row in rows
                    if row.component == component and row.type == "min"
                ),
                None,
            )

            if max_row and min_row:
                component_data[component] = {
                    "loadset1_min": min_row.loadset1_value,
                    "loadset1_max": max_row.loadset1_value,
                    "loadset2_min": min_row.loadset2_value,
                    "loadset2_max": max_row.loadset2_value,
                    "loadset1_min_case": min_row.loadset1_loadcase,
                    "loadset1_max_case": max_row.loadset1_loadcase,
                    "loadset2_min_case": min_row.loadset2_loadcase,
                    "loadset2_max_case": max_row.loadset2_loadcase,
                }

        return component_data

    def _create_range_subplot(self, ax, data: dict, title: str, units: str):
        """
        Create a range bar subplot for force or moment components.

        Args:
            ax: Matplotlib axis object
            data: Component range data
            title: Subplot title
            units: Units string for y-axis label
        """
        import numpy as np

        components = list(data.keys())
        if not components:
            return

        x_pos = np.arange(len(components))
        # Keep consistent bar width regardless of number of components (based on 3-component layout)
        bar_width_full = (
            0.8  # Width for LoadSet 1 (background bars) - same as 3-component case
        )
        bar_width_inner = (
            bar_width_full * 0.5
        )  # 50% width for LoadSet 2 (foreground bars)

        # Extract data for plotting
        loadset1_bottoms = []
        loadset1_heights = []
        loadset2_bottoms = []
        loadset2_heights = []

        for component in components:
            comp_data = data[component]

            # LoadSet 1
            ls1_min = comp_data["loadset1_min"]
            ls1_max = comp_data["loadset1_max"]
            loadset1_bottoms.append(ls1_min)
            loadset1_heights.append(ls1_max - ls1_min)

            # LoadSet 2
            ls2_min = comp_data["loadset2_min"]
            ls2_max = comp_data["loadset2_max"]
            loadset2_bottoms.append(ls2_min)
            loadset2_heights.append(ls2_max - ls2_min)

        # Create bars - LoadSet 1 as background (light grey, 100% opacity, no edges)
        ax.bar(
            x_pos,
            loadset1_heights,
            bar_width_full,
            bottom=loadset1_bottoms,
            color="lightgrey",
            alpha=1.0,
            edgecolor="none",
            linewidth=0,
        )

        # Determine colors for LoadSet 2 based on whether values exceed LoadSet 1
        loadset2_colors = []
        for component in components:
            comp_data = data[component]
            ls1_min = comp_data["loadset1_min"]
            ls1_max = comp_data["loadset1_max"]
            ls2_min = comp_data["loadset2_min"]
            ls2_max = comp_data["loadset2_max"]

            # Check if LoadSet 2 range exceeds LoadSet 1 range (either min is lower or max is higher)
            if ls2_min < ls1_min or ls2_max > ls1_max:
                loadset2_colors.append("maroon")
            else:
                loadset2_colors.append("darkgrey")

        # Create bars - LoadSet 2 as foreground with conditional coloring (no edges)
        for x, height, bottom, color in zip(
            x_pos, loadset2_heights, loadset2_bottoms, loadset2_colors
        ):
            ax.bar(
                x,
                height,
                bar_width_inner,
                bottom=bottom,
                color=color,
                alpha=1.0,
                edgecolor="none",
                linewidth=0,
            )

        # Add subtle zero reference line for visual grounding
        ax.axhline(
            y=0, color="#333333", linestyle="-", linewidth=1, alpha=0.6, zorder=1
        )

        # Styling - clean appearance with no grid or spines
        ax.set_title(title, fontweight="bold")
        ax.set_xlabel("Component")
        ax.set_ylabel(f"Value ({units})")
        ax.set_xticks(x_pos)
        ax.set_xticklabels(components)

        # Remove all spines (box around plot)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)

        # Remove grid
        ax.grid(False)

        # Set x-axis limits to maintain consistent bar width and auto-center regardless of number of components
        # Calculate centering offset to center the group of bars
        if len(components) > 0:
            # Center point of the component group
            center_point = (len(components) - 1) / 2.0
            # Fixed range width to maintain consistent bar scaling (based on 3-component case)
            range_width = 3.0  # Total width that would accommodate 3 components with proper spacing

            # Auto-center by adjusting the x-axis limits around the center point
            ax.set_xlim(center_point - range_width / 2, center_point + range_width / 2)

        # Set y-axis limits with some padding
        all_values = (
            loadset1_bottoms
            + [b + h for b, h in zip(loadset1_bottoms, loadset1_heights)]
            + loadset2_bottoms
            + [b + h for b, h in zip(loadset2_bottoms, loadset2_heights)]
        )
        if all_values:
            y_min, y_max = min(all_values), max(all_values)
            y_range = y_max - y_min
            if y_range > 0:
                padding = y_range * 0.1
                ax.set_ylim(y_min - padding, y_max + padding)

    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize a string to be safe for use as a filename.

        Args:
            name: Original name

        Returns:
            str: Sanitized name safe for filenames
        """
        import re

        # Replace spaces, special characters with underscores
        sanitized = re.sub(r"[^\w\-_]", "_", name)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        return sanitized


class ForceMoment(BaseModel):
    """
    ForceMoment is a model that represents a force and a moment.
    It is used to calculate the force and moment at a point in space.
    """

    fx: float = 0.0
    fy: float = 0.0
    fz: float = 0.0
    mx: float = 0.0
    my: float = 0.0
    mz: float = 0.0


class PointLoad(BaseModel):
    """
    PointLoad is a model that represents a point load in a simulation.
    It is used to define the loads acting on a structure at a specific point.
    """

    name: str | None = None
    force_moment: ForceMoment


class LoadCase(BaseModel):
    """
    LoadCase is a model that represents a load case in a simulation.
    It is used to define the loads acting on a structure.
    """

    name: str | None = None
    description: str | None = None
    point_loads: list[PointLoad] = []


class Units(BaseModel):
    """
    Units is a model that represents the units used in the load set.
    """

    forces: ForceUnit = "N"
    moments: MomentUnit = "Nm"


class LoadSet(BaseModel):
    """
    LoadSet is a model that represents a set of load cases in a simulation.
    It is used to group multiple load cases together.
    """

    name: str | None
    description: str | None = None
    version: int
    units: Units
    loads_type: Literal["limit", "ultimate"] | None = None
    load_cases: list[LoadCase]

    @classmethod
    def generate_json_schema(cls, output_file: PathLike | None = None) -> dict:
        """
        Generate JSON Schema for LoadSet model.

        Args:
            output_file: Optional path to save the schema file

        Returns:
            dict: JSON Schema for LoadSet model

        Raises:
            FileNotFoundError: If output directory doesn't exist
            ValueError: If schema generation fails
        """
        try:
            # Generate schema using Pydantic's built-in method
            schema = cls.model_json_schema()
            
            # Add JSON Schema metadata at the top level
            schema = {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$id": "loadset_schema.json",
                **schema
            }
            
            # Enhance with additional metadata
            if "title" not in schema:
                schema["title"] = "LoadSet Schema"
            if "description" not in schema:
                schema["description"] = "JSON Schema for LoadSet - a model representing aerospace structural load cases"
            
            # Add examples section
            schema["examples"] = [{
                "name": "Example LoadSet",
                "version": 1,
                "units": {
                    "forces": "N",
                    "moments": "Nm"
                },
                "description": "Example load cases for structural analysis",
                "load_cases": [{
                    "name": "Example_Case",
                    "description": "Example load case",
                    "point_loads": [{
                        "name": "Point A",
                        "force_moment": {
                            "fx": 100.0,
                            "fy": 0.0,
                            "fz": 0.0,
                            "mx": 0.0,
                            "my": 0.0,
                            "mz": 0.0
                        }
                    }]
                }]
            }]
            
            # Save to file if path provided
            if output_file is not None:
                output_path = Path(output_file)
                
                # Create parent directory if it doesn't exist
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    with open(output_path, "w", encoding="utf-8") as f:
                        json.dump(schema, f, indent=2, ensure_ascii=False)
                except Exception as e:
                    raise ValueError(f"Failed to write schema file: {e}")
            
            return schema
            
        except Exception as e:
            raise ValueError(f"Failed to generate JSON schema: {e}")

    @classmethod
    def read_json(cls, file_path: PathLike) -> "LoadSet":
        """
        Read a LoadSet from a JSON file.

        Args:
            file_path: Path to the JSON file to read

        Returns:
            LoadSet: The loaded LoadSet instance

        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the JSON is invalid
            ValueError: If the data doesn't match the schema
        """
        path = Path(file_path)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in file {file_path}: {e.msg}", e.doc, e.pos
            )

        try:
            return cls.model_validate(data)
        except ValidationError as e:
            raise ValueError(f"Invalid LoadSet data in file {file_path}: {e}")

    def convert_to(self, units: ForceUnit) -> "LoadSet":
        """
        Convert LoadSet to different units.

        Args:
            units: Target force units ("N", "kN", "lbf", "klbf")

        Returns:
            LoadSet: New LoadSet instance with converted values

        Raises:
            ValueError: If the target units are not supported
        """
        # Define conversion factors to base units (N and Nm)
        force_factors = {"N": 1.0, "kN": 1000.0, "lbf": 4.448222, "klbf": 4448.222}

        moment_factors = {"Nm": 1.0, "kNm": 1000.0, "lbf-ft": 1.355818}

        # Map force units to corresponding moment units
        force_to_moment: dict[ForceUnit, MomentUnit] = {
            "N": "Nm",
            "kN": "kNm",
            "lbf": "lbf-ft",
            "klbf": "lbf-ft",
        }

        if units not in force_factors:
            raise ValueError(f"Unsupported force unit: {units}")

        target_moment_units = force_to_moment[units]

        # Get conversion factors
        current_force_factor = force_factors[self.units.forces]
        current_moment_factor = moment_factors[self.units.moments]
        target_force_factor = force_factors[units]
        target_moment_factor = moment_factors[target_moment_units]

        # Calculate overall conversion factors
        force_conversion = current_force_factor / target_force_factor
        moment_conversion = current_moment_factor / target_moment_factor

        # Create new load cases with converted values
        new_load_cases = []
        for load_case in self.load_cases:
            new_point_loads = []
            for point_load in load_case.point_loads:
                fm = point_load.force_moment
                new_force_moment = ForceMoment(
                    fx=fm.fx * force_conversion,
                    fy=fm.fy * force_conversion,
                    fz=fm.fz * force_conversion,
                    mx=fm.mx * moment_conversion,
                    my=fm.my * moment_conversion,
                    mz=fm.mz * moment_conversion,
                )
                new_point_loads.append(
                    PointLoad(name=point_load.name, force_moment=new_force_moment)
                )

            new_load_cases.append(
                LoadCase(
                    name=load_case.name,
                    description=load_case.description,
                    point_loads=new_point_loads,
                )
            )

        # Create new LoadSet with converted units
        return LoadSet(
            name=self.name,
            description=self.description,
            version=self.version,
            units=Units(forces=units, moments=target_moment_units),
            load_cases=new_load_cases,
        )

    def factor(self, by: float) -> "LoadSet":
        """
        Scale all force and moment values by a factor.

        Args:
            by: Factor to scale by (can be positive, negative, or zero)

        Returns:
            LoadSet: New LoadSet instance with scaled values
        """
        # Create new load cases with scaled values
        new_load_cases = []
        for load_case in self.load_cases:
            new_point_loads = []
            for point_load in load_case.point_loads:
                fm = point_load.force_moment
                new_force_moment = ForceMoment(
                    fx=fm.fx * by,
                    fy=fm.fy * by,
                    fz=fm.fz * by,
                    mx=fm.mx * by,
                    my=fm.my * by,
                    mz=fm.mz * by,
                )
                new_point_loads.append(
                    PointLoad(name=point_load.name, force_moment=new_force_moment)
                )

            new_load_cases.append(
                LoadCase(
                    name=load_case.name,
                    description=load_case.description,
                    point_loads=new_point_loads,
                )
            )

        # Create new LoadSet with same units but scaled values
        return LoadSet(
            name=self.name,
            description=self.description,
            version=self.version,
            units=Units(forces=self.units.forces, moments=self.units.moments),
            load_cases=new_load_cases,
        )

    def to_ansys(self, folder_path: PathLike | None = None, name_stem: str | None = None) -> None:
        """
        Export LoadSet to ANSYS load files.

        Creates one file per load case with ANSYS F command format.
        Creates the output folder if it doesn't exist and cleans any existing files.

        Args:
            folder_path: Optional directory to save the files. Defaults to 'output' folder.
            name_stem: Optional base name for the files. If None, uses only load case names.

        Raises:
            FileNotFoundError: If the folder path exists but is not a directory
        """
        if folder_path is None:
            folder = Path("output")
        else:
            folder = Path(folder_path)

        # Check if path exists and is not a directory
        if folder.exists() and not folder.is_dir():
            raise FileNotFoundError(
                f"Path exists but is not a directory: {folder_path}"
            )

        # Create folder if it doesn't exist
        folder.mkdir(parents=True, exist_ok=True)

        # Clean existing files in the folder
        for file in folder.glob("*"):
            if file.is_file():
                file.unlink()

        # Return early if no load cases
        if not self.load_cases:
            return

        for load_case in self.load_cases:
            # Sanitize load case name for filename
            sanitized_name = self._sanitize_filename(load_case.name or "unnamed")
            if name_stem is None:
                filename = f"{sanitized_name}.inp"
            else:
                filename = f"{name_stem}_{sanitized_name}.inp"
            file_path = folder / filename

            # Generate ANSYS commands
            ansys_content = self._generate_ansys_content(load_case)

            # Write to file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(ansys_content)

    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize a string to be safe for use as a filename.

        Args:
            name: Original name

        Returns:
            str: Sanitized name safe for filenames
        """
        # Replace spaces, special characters with underscores
        sanitized = re.sub(r"[^\w\-_]", "_", name)
        # Remove multiple consecutive underscores
        sanitized = re.sub(r"_+", "_", sanitized)
        # Remove leading/trailing underscores
        sanitized = sanitized.strip("_")
        return sanitized

    def _generate_ansys_content(self, load_case: LoadCase) -> str:
        """
        Generate ANSYS commands for a load case.

        Args:
            load_case: LoadCase to convert

        Returns:
            str: ANSYS commands as text
        """
        lines = []

        # Add title command with load case name
        lines.append(f"/TITLE,{load_case.name or 'Unnamed'}")
        lines.append("nsel,u,,,all")
        lines.append("")

        # Generate commands for each point load
        for point_load in load_case.point_loads:
            node_name = point_load.name or "UnnamedNode"
            pilot_name = f"pilot_{node_name}"
            fm = point_load.force_moment

            # Force and moment components in specific order: fx, fy, mx, my, mz, fz
            components = [
                ("fx", fm.fx),
                ("fy", fm.fy),
                ("mx", fm.mx),
                ("my", fm.my),
                ("mz", fm.mz),
                ("fz", fm.fz),
            ]

            # Only write non-zero values
            for dof, value in components:
                if value != 0.0:
                    lines.append(f"cmsel,s,{pilot_name}")
                    lines.append(f"f,all,{dof},{value:.3e}")
                    lines.append("nsel,u,,,all")
                    lines.append("")

        lines.append("")
        lines.append("alls")

        return "\n".join(lines)

    def get_point_extremes(self) -> dict:
        """
        Get extreme values (max/min) for each point and component across all load cases.

        Returns:
            dict: Nested dictionary structure:
                {
                    "Point_A": {
                        "fx": {"max": {"value": 100.0, "loadcase": "Case1"},
                               "min": {"value": 80.0, "loadcase": "Case2"}},
                        "fy": {...},
                        ...
                    },
                    ...
                }
        """
        point_extremes = {}
        components = ["fx", "fy", "fz", "mx", "my", "mz"]

        # Collect all point data across all load cases
        for load_case in self.load_cases:
            for point_load in load_case.point_loads:
                point_name = point_load.name or "Unnamed"

                if point_name not in point_extremes:
                    point_extremes[point_name] = {}

                # Get force/moment values
                fm = point_load.force_moment
                values = {
                    "fx": fm.fx,
                    "fy": fm.fy,
                    "fz": fm.fz,
                    "mx": fm.mx,
                    "my": fm.my,
                    "mz": fm.mz,
                }

                for component in components:
                    value = values[component]

                    if component not in point_extremes[point_name]:
                        point_extremes[point_name][component] = {
                            "max": {
                                "value": value,
                                "loadcase": load_case.name or "Unnamed",
                            },
                            "min": {
                                "value": value,
                                "loadcase": load_case.name or "Unnamed",
                            },
                        }
                    else:
                        # Update max
                        if (
                            value
                            > point_extremes[point_name][component]["max"]["value"]
                        ):
                            point_extremes[point_name][component]["max"] = {
                                "value": value,
                                "loadcase": load_case.name or "Unnamed",
                            }

                        # Update min
                        if (
                            value
                            < point_extremes[point_name][component]["min"]["value"]
                        ):
                            point_extremes[point_name][component]["min"] = {
                                "value": value,
                                "loadcase": load_case.name or "Unnamed",
                            }

        # Filter out components where both max and min are zero
        filtered_extremes = {}
        for point_name, point_data in point_extremes.items():
            filtered_point_data = {}
            for component, comp_data in point_data.items():
                max_val = comp_data["max"]["value"]
                min_val = comp_data["min"]["value"]

                # Only include if not both max and min are zero
                if not (max_val == 0.0 and min_val == 0.0):
                    filtered_point_data[component] = comp_data

            if filtered_point_data:  # Only include points that have non-zero components
                filtered_extremes[point_name] = filtered_point_data

        return filtered_extremes

    def compare_to(self, other: "LoadSet") -> LoadSetCompare:
        """
        Compare this LoadSet to another LoadSet.

        Args:
            other: The LoadSet to compare against

        Returns:
            LoadSetCompare: Detailed comparison results

        Raises:
            ValueError: If the comparison cannot be performed
        """
        if not isinstance(other, LoadSet):
            raise ValueError("Can only compare to another LoadSet instance")

        # Convert units if necessary (convert other to match self's units)
        other_converted = other
        if other.units.forces != self.units.forces:
            other_converted = other.convert_to(self.units.forces)

        # Get extremes for both LoadSets
        self_extremes = self.get_point_extremes()
        other_extremes = other_converted.get_point_extremes()

        # Collect all unique point names from both LoadSets
        all_points = set(self_extremes.keys()) | set(other_extremes.keys())

        comparison_rows = []
        components: list[Literal["fx", "fy", "fz", "mx", "my", "mz"]] = [
            "fx",
            "fy",
            "fz",
            "mx",
            "my",
            "mz",
        ]

        for point_name in sorted(all_points):
            for component in components:
                # Check if component exists in both LoadSets for this point
                self_has_component = (
                    point_name in self_extremes
                    and component in self_extremes[point_name]
                )
                other_has_component = (
                    point_name in other_extremes
                    and component in other_extremes[point_name]
                )

                # Skip if component doesn't exist in either LoadSet (filtered out as zero)
                if not self_has_component and not other_has_component:
                    continue

                # Handle max comparison
                self_max_val = 0.0
                self_max_case = "N/A"
                other_max_val = 0.0
                other_max_case = "N/A"

                if self_has_component:
                    self_max_val = self_extremes[point_name][component]["max"]["value"]
                    self_max_case = self_extremes[point_name][component]["max"][
                        "loadcase"
                    ]

                if other_has_component:
                    other_max_val = other_extremes[point_name][component]["max"][
                        "value"
                    ]
                    other_max_case = other_extremes[point_name][component]["max"][
                        "loadcase"
                    ]

                # Calculate differences for max
                abs_diff_max = abs(other_max_val - self_max_val)
                pct_diff_max = 0.0
                if self_max_val != 0.0:
                    pct_diff_max = (abs_diff_max / abs(self_max_val)) * 100.0
                elif other_max_val != 0.0:
                    pct_diff_max = float("inf")  # Infinite percentage change

                # Create max comparison row
                max_row = ComparisonRow(
                    point_name=point_name,
                    component=component,
                    type="max",
                    loadset1_value=self_max_val,
                    loadset2_value=other_max_val,
                    loadset1_loadcase=self_max_case,
                    loadset2_loadcase=other_max_case,
                    abs_diff=abs_diff_max,
                    pct_diff=pct_diff_max,
                )
                comparison_rows.append(max_row)

                # Handle min comparison
                self_min_val = 0.0
                self_min_case = "N/A"
                other_min_val = 0.0
                other_min_case = "N/A"

                if self_has_component:
                    self_min_val = self_extremes[point_name][component]["min"]["value"]
                    self_min_case = self_extremes[point_name][component]["min"][
                        "loadcase"
                    ]

                if other_has_component:
                    other_min_val = other_extremes[point_name][component]["min"][
                        "value"
                    ]
                    other_min_case = other_extremes[point_name][component]["min"][
                        "loadcase"
                    ]

                # Calculate differences for min
                abs_diff_min = abs(other_min_val - self_min_val)
                pct_diff_min = 0.0
                if self_min_val != 0.0:
                    pct_diff_min = (abs_diff_min / abs(self_min_val)) * 100.0
                elif other_min_val != 0.0:
                    pct_diff_min = float("inf")  # Infinite percentage change

                # Create min comparison row
                min_row = ComparisonRow(
                    point_name=point_name,
                    component=component,
                    type="min",
                    loadset1_value=self_min_val,
                    loadset2_value=other_min_val,
                    loadset1_loadcase=self_min_case,
                    loadset2_loadcase=other_min_case,
                    abs_diff=abs_diff_min,
                    pct_diff=pct_diff_min,
                )
                comparison_rows.append(min_row)

        # Create metadata for both LoadSets
        self_metadata = {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "units": {"forces": self.units.forces, "moments": self.units.moments},
        }

        other_metadata = {
            "name": other.name,
            "version": other.version,
            "description": other.description,
            "units": {"forces": other.units.forces, "moments": other.units.moments},
        }

        return LoadSetCompare(
            loadset1_metadata=self_metadata,
            loadset2_metadata=other_metadata,
            comparison_rows=comparison_rows,
        )

    def envelope(self) -> "LoadSet":
        """
        Create an envelope LoadSet containing only load cases with extreme values.

        For each point and component (fx, fy, fz, mx, my, mz), selects load cases with:
        - Maximum value (always included)
        - Minimum value (only if negative)

        Load cases appearing multiple times (having extremes in multiple components)
        are deduplicated in the result.

        Returns:
            LoadSet: New LoadSet with envelope load cases only

        Raises:
            ValueError: If LoadSet has no load cases
        """
        if not self.load_cases:
            raise ValueError("Cannot create envelope of empty LoadSet")

        # Get extreme values for all points and components
        extremes = self.get_point_extremes()

        # Collect unique load case names that have extreme values
        envelope_case_names = set()

        for point_name, point_data in extremes.items():
            for component, comp_data in point_data.items():
                # Always include max value load case
                max_case = comp_data["max"]["loadcase"]
                envelope_case_names.add(max_case)

                # Include min value load case only if it's negative
                min_value = comp_data["min"]["value"]
                if min_value < 0:
                    min_case = comp_data["min"]["loadcase"]
                    envelope_case_names.add(min_case)

        # Filter original load cases to include only envelope cases
        envelope_load_cases = []
        for load_case in self.load_cases:
            case_name = load_case.name or "Unnamed"
            if case_name in envelope_case_names:
                envelope_load_cases.append(load_case)

        # Create new LoadSet with envelope load cases
        return LoadSet(
            name=self.name,
            description=self.description,
            version=self.version,
            units=Units(forces=self.units.forces, moments=self.units.moments),
            load_cases=envelope_load_cases,
        )

    def _format_value(
        self,
        value: float,
        is_extreme: bool = False,
    ) -> str:
        """
        Format a numeric value with optional bold highlighting.

        Args:
            value: The numeric value to format
            is_extreme: True if this is max positive or min negative within load case

        Returns:
            str: Rich-formatted string
        """
        # Format number
        if value == 0.0:
            return "[dim]0.000[/dim]"
        elif abs(value) >= 10000 or abs(value) < 0.01:
            formatted = f"{value:.3e}"
        else:
            formatted = f"{value:.3f}"

        # Apply bold if extreme value
        if is_extreme:
            return f"[bold]{formatted}[/bold]"
        else:
            return formatted

    def _get_loadcase_extremes(
        self, load_case: LoadCase
    ) -> dict[str, dict[str, int | float]]:
        """
        Get max/min indices for each coordinate within a single load case.

        Args:
            load_case: The LoadCase to analyze

        Returns:
            dict: {"fx": {"max_idx": 0, "min_idx": 2, "max": val, "min": val}, ...}
        """
        components = ["fx", "fy", "fz", "mx", "my", "mz"]
        extremes: dict[str, dict[str, int | float]] = {}

        for comp in components:
            values = [
                getattr(pl.force_moment, comp) for pl in load_case.point_loads
            ]
            if values:
                max_val = max(values)
                min_val = min(values)
                # Store indices for exact matching (avoids float precision issues)
                extremes[comp] = {
                    "max_idx": values.index(max_val),
                    "min_idx": values.index(min_val),
                    "max": max_val,
                    "min": min_val,
                }

        return extremes

    def print_head(self, n: int = 5) -> None:
        """
        Print a preview of the first N load cases in a formatted table.

        Args:
            n: Number of load cases to display (default: 5)
        """
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel

        console = Console()

        # Header panel with metadata
        header_text = f"[bold cyan]{self.name or 'Unnamed LoadSet'}[/bold cyan]\n"
        header_text += f"Version: {self.version} | "
        header_text += f"Units: {self.units.forces}, {self.units.moments}"
        if self.description:
            header_text += f"\n{self.description}"
        console.print(Panel(header_text, title="LoadSet", border_style="cyan"))

        # Create table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Load Case", style="bold")
        table.add_column("Point")
        table.add_column("Fx", justify="right")
        table.add_column("Fy", justify="right")
        table.add_column("Fz", justify="right")
        table.add_column("Mx", justify="right")
        table.add_column("My", justify="right")
        table.add_column("Mz", justify="right")

        # Add rows for first n load cases
        cases_to_show = self.load_cases[:n]
        for load_case in cases_to_show:
            case_name = load_case.name or "Unnamed"
            local_extremes = self._get_loadcase_extremes(load_case)

            for i, point_load in enumerate(load_case.point_loads):
                fm = point_load.force_moment
                point_name = point_load.name or "Unnamed"
                display_case = case_name if i == 0 else ""

                # Format each component with highlighting
                formatted = []
                for comp in ["fx", "fy", "fz", "mx", "my", "mz"]:
                    val = getattr(fm, comp)
                    local = local_extremes.get(comp, {})

                    # Highlight if max positive or min negative within load case
                    # Skip if all values are the same (max_idx == min_idx)
                    max_idx = local.get("max_idx", -1)
                    min_idx = local.get("min_idx", -1)
                    max_val = local.get("max", 0.0)
                    min_val = local.get("min", 0.0)

                    is_extreme = False
                    if max_idx != min_idx:  # Values differ
                        # Bold if max positive value
                        if i == max_idx and max_val > 0:
                            is_extreme = True
                        # Bold if min negative value
                        elif i == min_idx and min_val < 0:
                            is_extreme = True

                    formatted.append(self._format_value(val, is_extreme))

                table.add_row(display_case, point_name, *formatted)

            # Add separator between load cases
            if load_case != cases_to_show[-1]:
                table.add_row("", "", "", "", "", "", "", "", end_section=True)

        console.print(table)

        # Footer with count
        total = len(self.load_cases)
        if n < total:
            console.print(f"[dim]Showing {n} of {total} load cases[/dim]")
        else:
            console.print(f"[dim]Showing all {total} load cases[/dim]")

    def print_table(self) -> None:
        """
        Print all load cases in a formatted table.
        """
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel

        console = Console()

        # Header panel with metadata
        header_text = f"[bold cyan]{self.name or 'Unnamed LoadSet'}[/bold cyan]\n"
        header_text += f"Version: {self.version} | "
        header_text += f"Units: {self.units.forces}, {self.units.moments}"
        if self.description:
            header_text += f"\n{self.description}"
        console.print(Panel(header_text, title="LoadSet", border_style="cyan"))

        # Create table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Load Case", style="bold")
        table.add_column("Point")
        table.add_column("Fx", justify="right")
        table.add_column("Fy", justify="right")
        table.add_column("Fz", justify="right")
        table.add_column("Mx", justify="right")
        table.add_column("My", justify="right")
        table.add_column("Mz", justify="right")

        # Add rows for all load cases
        for idx, load_case in enumerate(self.load_cases):
            case_name = load_case.name or "Unnamed"
            local_extremes = self._get_loadcase_extremes(load_case)

            for i, point_load in enumerate(load_case.point_loads):
                fm = point_load.force_moment
                point_name = point_load.name or "Unnamed"
                display_case = case_name if i == 0 else ""

                # Format each component with highlighting
                formatted = []
                for comp in ["fx", "fy", "fz", "mx", "my", "mz"]:
                    val = getattr(fm, comp)
                    local = local_extremes.get(comp, {})

                    # Highlight if max positive or min negative within load case
                    # Skip if all values are the same (max_idx == min_idx)
                    max_idx = local.get("max_idx", -1)
                    min_idx = local.get("min_idx", -1)
                    max_val = local.get("max", 0.0)
                    min_val = local.get("min", 0.0)

                    is_extreme = False
                    if max_idx != min_idx:  # Values differ
                        # Bold if max positive value
                        if i == max_idx and max_val > 0:
                            is_extreme = True
                        # Bold if min negative value
                        elif i == min_idx and min_val < 0:
                            is_extreme = True

                    formatted.append(self._format_value(val, is_extreme))

                table.add_row(display_case, point_name, *formatted)

            # Add separator between load cases
            if idx < len(self.load_cases) - 1:
                table.add_row("", "", "", "", "", "", "", "", end_section=True)

        console.print(table)
        console.print(f"[dim]Total: {len(self.load_cases)} load cases[/dim]")

    def print_extremes(self) -> None:
        """
        Print extreme values (max/min) for each point and component.

        Uses get_point_extremes() to show only the envelope bounds.
        """
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel

        console = Console()

        # Header panel with metadata
        name = self.name or 'Unnamed LoadSet'
        header_text = f"[bold cyan]{name}[/bold cyan] - Extreme Values\n"
        header_text += f"Version: {self.version} | "
        header_text += f"Units: {self.units.forces}, {self.units.moments}"
        console.print(Panel(header_text, title="LoadSet Extremes", border_style="cyan"))

        extremes = self.get_point_extremes()

        if not extremes:
            console.print("[yellow]No extreme values found (all zero)[/yellow]")
            return

        # Create table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Point", style="bold")
        table.add_column("Component")
        table.add_column("Type")
        table.add_column("Value", justify="right")
        table.add_column("Load Case")

        for point_name in sorted(extremes.keys()):
            point_data = extremes[point_name]
            first_row = True
            for component in ["fx", "fy", "fz", "mx", "my", "mz"]:
                if component not in point_data:
                    continue
                comp_data = point_data[component]

                # Max row
                max_val = comp_data["max"]["value"]
                max_case = comp_data["max"]["loadcase"]
                display_point = point_name if first_row else ""
                table.add_row(
                    display_point,
                    component.upper(),
                    "[bold green]max[/bold green]",
                    f"[bold green]{self._format_value(max_val)}[/bold green]",
                    max_case,
                )
                first_row = False

                # Min row
                min_val = comp_data["min"]["value"]
                min_case = comp_data["min"]["loadcase"]
                table.add_row(
                    "",
                    component.upper(),
                    "[bold red]min[/bold red]",
                    f"[bold red]{self._format_value(min_val)}[/bold red]",
                    min_case,
                )

            # Add separator between points
            table.add_row("", "", "", "", "", end_section=True)

        console.print(table)
        n_cases = len(self.load_cases)
        console.print(f"[dim]Points: {len(extremes)} | From {n_cases} load cases[/dim]")

    @classmethod
    def read_ansys(
        cls, file_path: PathLike, units: Units, name: str | None = None, version: int = 1
    ) -> "LoadSet":
        """
        Read a LoadSet from an ANSYS .inp file.

        Parses ANSYS load files with the following format:
        - /TITLE,{loadcase_name} - defines the load case name
        - cmsel,s,pilot_{node_name} - selects the pilot node
        - f,all,{component},{value} - applies force/moment components

        Args:
            file_path: Path to the ANSYS .inp file to read
            units: Units to use for the LoadSet (forces and moments)
            name: Optional name for the LoadSet (defaults to filename without extension)
            version: Version number for the LoadSet (defaults to 1)

        Returns:
            LoadSet: The loaded LoadSet instance with a single LoadCase

        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid or cannot be parsed
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Use filename as default name if not provided
        if name is None:
            name = path.stem

        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            raise ValueError(f"Could not read file {file_path}: {e}")

        # Parse the ANSYS file
        load_case_name = None
        current_point = None
        point_loads_data = {}  # {point_name: {component: value}}

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith("!"):  # Skip empty lines and comments
                continue

            try:
                # Parse title command to get load case name
                if line.startswith("/TITLE,"):
                    load_case_name = line[7:]  # Remove "/TITLE," prefix
                    continue

                # Parse component selection to get point name
                if line.startswith("cmsel,s,pilot_"):
                    # Extract point name by removing "cmsel,s,pilot_" prefix
                    current_point = line[14:]  # Remove "cmsel,s,pilot_" prefix
                    if current_point not in point_loads_data:
                        point_loads_data[current_point] = {}
                    continue

                # Parse force/moment command
                if line.startswith("f,all,"):
                    if current_point is None:
                        raise ValueError(
                            f"Line {line_num}: Force command found without preceding point selection"
                        )

                    # Parse: f,all,component,value
                    parts = line.split(",")
                    if len(parts) != 4 or parts[0] != "f" or parts[1] != "all":
                        raise ValueError(f"Line {line_num}: Invalid force command format: {line}")

                    component = parts[2].strip()
                    value_str = parts[3].strip()

                    # Validate component
                    valid_components = {"fx", "fy", "fz", "mx", "my", "mz"}
                    if component not in valid_components:
                        raise ValueError(
                            f"Line {line_num}: Invalid component '{component}'. Must be one of {valid_components}"
                        )

                    # Parse value (handle scientific notation)
                    try:
                        value = float(value_str)
                    except ValueError:
                        raise ValueError(
                            f"Line {line_num}: Invalid numeric value '{value_str}'"
                        )

                    point_loads_data[current_point][component] = value
                    continue

                # Skip other commands (nsel, alls, etc.)

            except Exception as e:
                if isinstance(e, ValueError):
                    raise  # Re-raise ValueError with line context
                raise ValueError(f"Line {line_num}: Error parsing line '{line}': {e}")

        # Validate that we found a load case name
        if load_case_name is None:
            raise ValueError("No /TITLE command found in ANSYS file")

        # Validate that we found at least one point load
        if not point_loads_data:
            raise ValueError("No point loads found in ANSYS file")

        # Create PointLoad objects
        point_loads = []
        for point_name, components in point_loads_data.items():
            # Create ForceMoment with all components (default to 0.0 if not specified)
            force_moment = ForceMoment(
                fx=components.get("fx", 0.0),
                fy=components.get("fy", 0.0),
                fz=components.get("fz", 0.0),
                mx=components.get("mx", 0.0),
                my=components.get("my", 0.0),
                mz=components.get("mz", 0.0),
            )

            point_load = PointLoad(name=point_name, force_moment=force_moment)
            point_loads.append(point_load)

        # Create LoadCase
        load_case = LoadCase(
            name=load_case_name,
            description=f"Imported from {path.name}",
            point_loads=point_loads,
        )

        # Create and return LoadSet
        return cls(
            name=name,
            description=f"LoadSet imported from ANSYS file: {path.name}",
            version=version,
            units=units,
            load_cases=[load_case],
        )
