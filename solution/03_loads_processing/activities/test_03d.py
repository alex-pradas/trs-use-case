from os import system
from pathlib import Path
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.messages import ImageMediaType









agent = Agent(
    # model="anthropic:claude-4-sonnet-20250514",
    model="anthropic:claude-opus-4-20250514",
)

system_prompt = """You are a image processing expert in coordinate systems for structural applications.
your goal is to evaluate images and provide a desciptive analysis on the coordinate systems used.

The user will provide an image and it is your task to determine if the coordinate systems aligns to the specifications.
You will also define how the components of the coordinate system need to be changed to align to the baseline global coordinate system.

The view is isometric. The coordinate system is defined at the bottom left of the image. Then, the coordinates of the interface points will be shown at different parts of the component.
For each interface point (A, B, C...) you need to describe if the x,y,z coordinates align to the Global coordinate system, both in orientation and in direction.
"""

image_path = Path("/Users/alex/repos/trs-use-case/use_case_definition/data/loads/03d_01_coordinates.jpg")

user_prompt = f"""Here is an image, please tell me if I need to change the coordinates of the interface points and how

<example 1 >
I can see two interfaces and their coordinate systems: P1 and P2.

Let me define the unit vectors of the different coordinate systems:
    - Global: [e_x^Global, e_y^Global, e_z^Global]
    - P1: [e_x^P1, e_y^P1, e_z^P1]
    - P2: [e_x^P2, e_y^P2, e_z^P2]

Lets analyze all the points

P1 analysis:
Let me understand the relationship between P1 and the global coordinate system:
    - Both are X, Y, Z systems
    - x_P1 points along x_Global
    - y_P1 points along y_Global
    - z_P1 points along -z_Global

The basis vectors of P1 expressed in Global coordinates are:
    - e_x^P1 in Global = [1, 0, 0]^T
    - e_y^P1 in Global = [0, 1, 0]^T
    - e_z^P1 in Global = [0, 0, -1]^T

So the reflection/rotation matrix to translate P1 coordinate system to the global coordinate system are: 
R = [[1, 0, 0],
[0, 1, 0],
[0, 0, -1]]

Now lets move to P2

Let me understand the relationship between P1 and the global coordinate system:
    - Both are X, Y, Z systems
    - x_P1 points along y_Global
    - y_P1 points along -x_Global
    - z_P1 points along z_Global

So the basis vectors of P1 expressed in Global coordinates are:
    - e_x^P1 = [0, 1, 0]^T in Global
    - e_y^P1 = [-1, 0, 0]^T in Global
    - e_z^P1 = [0, 0, 1]^T in Global

The rotation matrix R that transforms from P2 to Global will have these as columns:
R = [[0, -1, 0],
[1, 0, 0],
[0, 0, 1]]

</example 1>
"""

result = agent.run_sync(
    [
        "describe the directions of the coordinates system in this image.",
        BinaryContent(data=image_path.read_bytes(), media_type="image/jpeg")
    ]
)

print(result.output)
