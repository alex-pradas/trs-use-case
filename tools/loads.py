from typing import Literal
from pathlib import Path
from os import PathLike
import json
import re
from pydantic import BaseModel, ValidationError

# Type aliases for units
ForceUnit = Literal["N", "kN", "lbf", "klbf"]
MomentUnit = Literal["Nm", "kNm", "lbf-ft"]


class ForceMoment(BaseModel):
    """
    ForceMoment is a model that represents a force and a moment.
    It is used to calculate the force and moment at a point in space.
    """

    fx: float
    fy: float
    fz: float
    mx: float
    my: float
    mz: float


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
    load_cases: list[LoadCase]

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

    def to_ansys(self, folder_path: PathLike, name_stem: str) -> None:
        """
        Export LoadSet to ANSYS load files.

        Creates one file per load case with ANSYS F command format.

        Args:
            folder_path: Directory to save the files
            name_stem: Base name for the files (will be suffixed with load case names)

        Raises:
            FileNotFoundError: If the folder path doesn't exist
        """
        folder = Path(folder_path)

        # Validate that the folder exists
        if not folder.exists():
            raise FileNotFoundError(f"Directory does not exist: {folder_path}")

        if not folder.is_dir():
            raise FileNotFoundError(f"Path is not a directory: {folder_path}")

        # Return early if no load cases
        if not self.load_cases:
            return

        for load_case in self.load_cases:
            # Sanitize load case name for filename
            sanitized_name = self._sanitize_filename(load_case.name or "unnamed")
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
                ('fx', fm.fx),
                ('fy', fm.fy), 
                ('mx', fm.mx),
                ('my', fm.my),
                ('mz', fm.mz),
                ('fz', fm.fz)
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
