from http import HTTPStatus


class BizException(Exception):
    """
    业务异常基类。
    """

    status_code: int = HTTPStatus.BAD_REQUEST
    code: int = 400
    message: str = "请求处理失败"

    def __init__(
            self,
            *,
            message: str | None = None,
            code: int | None = None,
            status_code: int | None = None,
    ):
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        super().__init__(self.message)


class UsernameOrPasswordError(BizException):
    """
    用户名或密码错误。
    """

    status_code = HTTPStatus.OK
    code = 100001
    message = "用户名或密码错误"


class InvalidTokenError(BizException):
    """
    Token 无效或已过期。
    """

    status_code = HTTPStatus.UNAUTHORIZED
    code = 401002
    message = "无效 token"
