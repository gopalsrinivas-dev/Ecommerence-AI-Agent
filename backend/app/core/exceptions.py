class DomainError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, retryable: bool = False):
        self.code, self.message, self.status, self.retryable = code, message, status, retryable
        super().__init__(code)


def missing():
    return DomainError("NOT_FOUND", "This resource is unavailable.", 404)
