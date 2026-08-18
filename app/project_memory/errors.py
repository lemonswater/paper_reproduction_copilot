class ProjectMemoryError(RuntimeError):
    """Project Memory 领域错误基类。"""


class ProjectNotFoundError(ProjectMemoryError):
    pass


class ProjectFactNotFoundError(ProjectMemoryError):
    pass


class ProjectMemoryConflictError(ProjectMemoryError):
    pass


class ProjectMemoryIntegrityError(ProjectMemoryError):
    pass


class ProjectMemoryLimitExceededError(ProjectMemoryError):
    pass
