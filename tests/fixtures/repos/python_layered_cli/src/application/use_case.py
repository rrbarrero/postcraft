"""Application use case."""

from src.domain.model import Report


class CreateReportUseCase:
    def execute(self) -> Report:
        return Report(title="Test", body="Hello world")
