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


class InvalidAccessTokenError(BizException):
    """
    Access Token 无效或已过期。
    """

    status_code = HTTPStatus.UNAUTHORIZED
    code = 401002
    message = "access token 无效"


class InvalidRefreshTokenError(BizException):
    """
    Refresh Token 无效或已过期。
    """

    status_code = HTTPStatus.UNAUTHORIZED
    code = 401003
    message = "refresh token 无效"


class UserNotFoundError(BizException):
    """
    用户不存在。
    """

    status_code = HTTPStatus.NOT_FOUND
    code = 404001
    message = "用户不存在"


class UploadFileTooLargeError(BizException):
    """
    上传文件超过大小限制。
    """

    status_code = HTTPStatus.REQUEST_ENTITY_TOO_LARGE
    code = 413001
    message = "文件大小超过限制（最大 10MB）"


class UnsupportedFileTypeError(BizException):
    """
    上传文件类型不支持。
    """

    status_code = HTTPStatus.BAD_REQUEST
    code = 400001
    message = "不支持的文件类型，仅支持 jpg/png/webp/gif"


class NoFileUploadedError(BizException):
    """
    没有上传任何文件。
    """

    status_code = HTTPStatus.BAD_REQUEST
    code = 400002
    message = "请至少上传一张图片"


class TooManyFilesError(BizException):
    """
    上传文件数量超过限制。
    """

    status_code = HTTPStatus.BAD_REQUEST
    code = 400003
    message = "一次最多上传 6 张图片"


class UploadFailedError(BizException):
    """
    对象存储上传失败。
    """

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    code = 500001
    message = "文件上传失败"
