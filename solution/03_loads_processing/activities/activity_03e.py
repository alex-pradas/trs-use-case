from pathlib import Path
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.messages import ImageMediaType
from pydantic import BaseModel, Field
import logfire

logfire.configure()
logfire.instrument_pydantic_ai()

class Response(BaseModel):
    coordinate_count: int = Field(
        description="The number of coordinates present in the image"
    )
    coordinates_list: list[str] = Field(
        description="Coordinate system names as provided in the image"
    )
    transformation_matrix: list[list[int]] = Field(
        description="3d transformation matrix to go from the leftmost coordinate system to the other coordinate systems"
    )


class ResponseList(BaseModel):
    coordinate_count: int = Field(
        description="The number of coordinates present in the image"
    )
    coordinates_list: list[str] = Field(
        description="Coordinate system names as provided in the image"
    )
    transformation_matrix: list[list[list[int]]] = Field(
        description="list of 3d transformation matrix to go from the leftmost coordinate system to the other coordinate systems"
    )


system_prompt = """You are a image processing expert in coordinate systems for structural applications.
your goal is to evaluate images and provide a desciptive analysis on the coordinate systems used.

The user will provide an image and it is your task to determine if the coordinate systems aligns to the specifications.
You are very methodical and you capture subtelties on the orientations of coordinate systems and are very descriptive in a technical manner.
"""

agent = Agent(
    model="anthropic:claude-4-sonnet-20250514",
    # model="anthropic:claude-opus-4-20250514",
    output_type=Response,
)

# image_path = Path(
#     "/Users/alex/repos/trs-use-case/use_case_definition/data/loads/03e_coordinate_sys_2d_1.jpg"
# )

# dimension = "2d"

# user_prompt = f"""Here is an image containing coordinates systems. These coordinates are shown in a {dimension} view. The axes are part of a X, Y, Z orthogonal systems that follow the right-hand rule.
# Please provide the following information:
# 1. How many coordinate systems are shown in the image?
# 2. How are they labelled?
# 3. Assuming that a given vector is provided in the leftmost coordinate system, provide a transformation matrix of the coordinates to be expressed on the other coordinate system(s) shown in the image.
# """

# result = agent.run_sync(
#     [user_prompt, BinaryContent(data=image_path.read_bytes(), media_type="image/jpeg")]
# )

# print(result.output)
# # --------------------------------------------------------------------------------------

# image_path = Path(
#     "/Users/alex/repos/trs-use-case/use_case_definition/data/loads/03e_coordinate_sys_2d_2.jpg"
# )

# result = agent.run_sync(
#     [user_prompt, BinaryContent(data=image_path.read_bytes(), media_type="image/jpeg")]
# )

# print(result.output)

# # --------------------------------------------------------------------------------------

# agent = Agent(
#     model="anthropic:claude-4-sonnet-20250514",
#     # model="anthropic:claude-opus-4-20250514",
#     output_type=ResponseLIst,
# )
# image_path = Path(
#     "/Users/alex/repos/trs-use-case/use_case_definition/data/loads/03e_coordinate_sys_2d_3.jpg"
# )

# result = agent.run_sync(
#     [user_prompt, BinaryContent(data=image_path.read_bytes(), media_type="image/jpeg")]
# )

# print(result.output)

# # --------------------------------------------------------------------------------------

dimension = "3d"

agent = Agent(
    model="anthropic:claude-4-sonnet-20250514",
    # model="anthropic:claude-opus-4-20250514",
    output_type=Response,
)

user_prompt = f"""Here is an image containing coordinates systems. These coordinates are shown in a {dimension} view. The axes are part of a X, Y, Z orthogonal systems that follow the right-hand rule.
Please provide the following information:
1. How many coordinate systems are shown in the image?
2. How are they labelled?
3. Assuming that a given vector is provided in the leftmost coordinate system, provide a transformation matrix of the coordinates to be expressed on the other coordinate system(s) shown in the image.
"""

image_path = Path(
    "/Users/alex/repos/trs-use-case/use_case_definition/data/loads/03e_coordinate_sys_3d_2.jpg"
)

result = agent.run_sync(
    [user_prompt, BinaryContent(data=image_path.read_bytes(), media_type="image/jpeg")]
)
print("1: ", result.output)

#  -------------------------------------------------------------------------------------

image_path = Path(
    "/Users/alex/repos/trs-use-case/use_case_definition/data/loads/03e_coordinate_sys_3d_2.jpg"
)
result = agent.run_sync(
    [user_prompt, BinaryContent(data=image_path.read_bytes(), media_type="image/jpeg")]
)
print("2: ", result.output)


#  -------------------------------------------------------------------------------------

result = agent.run_sync(
    [
        user_prompt, BinaryContent(
            data=Path(
                "/Users/alex/repos/trs-use-case/use_case_definition/data/loads/03e_coordinate_sys_3d_3.jpg"
            ).read_bytes(), 
            media_type="image/jpeg",
        )
    ]
)

print("3: ", result.output)

#  -------------------------------------------------------------------------------------

agent = Agent(
    model="anthropic:claude-4-sonnet-20250514",
    # model="anthropic:claude-opus-4-20250514",
    # output_type=ResponseList,
)


result = agent.run_sync(
    [
        user_prompt, BinaryContent(
            data=Path(
                "/Users/alex/repos/trs-use-case/use_case_definition/data/loads/03e_coordinate_sys_3d_4.jpg"
            ).read_bytes(), 
            media_type="image/jpeg",
        )
    ]
)

print("4: ", result.output)

#  -------------------------------------------------------------------------------------

result = agent.run_sync(
    [
        user_prompt, BinaryContent(
            data=Path(
                "/Users/alex/repos/trs-use-case/use_case_definition/data/loads/03e_coordinate_sys_3d_5.jpg"
            ).read_bytes(), 
            media_type="image/jpeg",
        )
    ]
)

print("5: ", result.output)