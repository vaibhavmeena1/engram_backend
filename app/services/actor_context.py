"""Request-safe actor context storage helpers."""

from contextvars import ContextVar, Token

from app.schemas.context import ActorContext
from app.schemas.repository import RepositoryContext

_current_actor_context: ContextVar[ActorContext | None] = ContextVar(
    "current_actor_context", default=None
)
_current_repository_context: ContextVar[RepositoryContext | None] = ContextVar(
    "current_repository_context", default=None
)


class ActorContextService:
    """Stores resolved request context without coupling services to FastAPI request objects."""

    @classmethod
    def set_actor_context(
        cls, actor_context: ActorContext
    ) -> Token[ActorContext | None]:
        return _current_actor_context.set(actor_context)

    @classmethod
    def get_actor_context(cls) -> ActorContext | None:
        return _current_actor_context.get()

    @classmethod
    def reset_actor_context(cls, token: Token[ActorContext | None]) -> None:
        _current_actor_context.reset(token)

    @classmethod
    def set_repository_context(
        cls, repository_context: RepositoryContext | None
    ) -> Token[RepositoryContext | None]:
        return _current_repository_context.set(repository_context)

    @classmethod
    def get_repository_context(cls) -> RepositoryContext | None:
        return _current_repository_context.get()

    @classmethod
    def reset_repository_context(cls, token: Token[RepositoryContext | None]) -> None:
        _current_repository_context.reset(token)

    @classmethod
    def clear(cls) -> None:
        _current_actor_context.set(None)
        _current_repository_context.set(None)
