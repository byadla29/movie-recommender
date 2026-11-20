from dataclasses import dataclass


@dataclass(frozen=True)
class FieldError:
    """One problem with one input field, in the same shape as FastAPI's validation errors."""

    loc: tuple[str | int, ...]  # e.g. ("body", "languages", 1)
    msg: str
    type: str


class DomainValidationError(Exception):
    """Input is well-formed but breaks a business rule -> 422 problem+json."""

    def __init__(self, errors: list[FieldError]) -> None:
        super().__init__(f"{len(errors)} validation error(s)")
        self.errors = errors
