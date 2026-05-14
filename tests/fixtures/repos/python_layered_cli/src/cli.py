"""CLI entrypoint."""

from src.application.use_case import CreateReportUseCase


def main() -> None:
    use_case = CreateReportUseCase()
    result = use_case.execute()
    print(result)
