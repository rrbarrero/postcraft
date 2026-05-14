"""Repository adapter."""


class ReportRepository:
    def save(self, report: object) -> None:
        raise NotImplementedError
