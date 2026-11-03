"""异常定义"""


class QuizGenerationError(Exception):
    """题库生成失败"""

    def __init__(self, message: str = "题库生成失败，请稍后重试"):
        self.message = message
        super().__init__(self.message)


class ReportGenerationError(Exception):
    """报告生成失败"""

    def __init__(self, message: str = "报告生成失败，请稍后重试"):
        self.message = message
        super().__init__(self.message)


class ContentFilterError(Exception):
    """内容过滤异常"""

    def __init__(self, message: str = "输入内容包含敏感词，请修改后重试"):
        self.message = message
        super().__init__(self.message)


class AuthenticationError(Exception):
    """鉴权失败"""

    def __init__(self, message: str = "未登录或登录已过期"):
        self.message = message
        super().__init__(self.message)


class KnowledgeBaseError(Exception):
    """知识库操作异常（格式/大小/数量校验失败、文档不存在或未就绪等）"""

    def __init__(self, message: str = "知识库操作失败"):
        self.message = message
        super().__init__(self.message)


class AdminUserError(Exception):
    """管理员账号操作异常（不存在、不能停用自己、不能停用最后一个管理员等）"""

    def __init__(self, message: str = "管理员操作失败"):
        self.message = message
        super().__init__(self.message)


class QuestionError(Exception):
    """题库操作异常（题目不存在、审核失败等）"""

    def __init__(self, message: str = "题库操作失败"):
        self.message = message
        super().__init__(self.message)


class KnowledgeCardError(Exception):
    """知识卡操作异常（不存在、状态不合法等）"""

    def __init__(self, message: str = "知识卡操作失败"):
        self.message = message
        super().__init__(self.message)


class AdminOrgError(Exception):
    """组织与员工操作异常（部门不存在、工号重复、导入格式错误等）"""

    def __init__(self, message: str = "组织与员工操作失败"):
        self.message = message
        super().__init__(self.message)


class AdminExamError(Exception):
    """考试与导出操作异常（题库不存在、题目不足、考试状态不允许等）"""

    def __init__(self, message: str = "考试操作失败"):
        self.message = message
        super().__init__(self.message)

