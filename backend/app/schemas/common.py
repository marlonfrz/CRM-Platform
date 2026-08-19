from typing import Annotated

from pydantic import StringConstraints

OrganizationName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
DepartmentName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
