class BusinessError(Exception):
    """业务异常，由全局处理器统一转换为 {code, message, detail}。"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        detail: object | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail
