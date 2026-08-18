class KnowledgeBaseError(RuntimeError):
    pass


class KnowledgeNotFoundError(KnowledgeBaseError):
    pass


class KnowledgeConflictError(KnowledgeBaseError):
    pass


class KnowledgeIntegrityError(KnowledgeBaseError):
    pass


class KnowledgeLimitExceededError(KnowledgeBaseError):
    pass


class KnowledgeStaleReviewError(KnowledgeConflictError):
    pass
