"""Task backend implementations and factory."""

from .base import TaskBackend, TaskItem


def create_backend(backend_type: str, config, logger) -> TaskBackend:
    """Factory function to create appropriate task backend.

    Args:
        backend_type: Type of backend ('microsoft' or 'google')
        config: Configuration object with backend-specific settings
        logger: Logger instance

    Returns:
        TaskBackend implementation instance

    Raises:
        ValueError: If backend_type is not supported
    """
    if backend_type == "microsoft":
        from .microsoft_todo import MicrosoftTodoBackend
        return MicrosoftTodoBackend(
            client_id=config.client_id,
            tenant_id=config.tenant_id,
            auth_mode=config.auth_mode,
            client_secret=config.client_secret,
            token_storage_path=config.token_storage_path,
            allow_prompt=config.allow_prompt,
            logger=logger,
        )
    elif backend_type == "google":
        from .google_tasks import GoogleTasksBackend
        return GoogleTasksBackend(
            client_id=config.google_client_id,
            client_secret=config.google_client_secret,
            token_storage_path=config.token_storage_path,
            allow_prompt=config.allow_prompt,
            logger=logger,
        )
    else:
        raise ValueError(
            f"Unknown backend type: {backend_type}. "
            f"Supported backends: 'microsoft', 'google'"
        )


__all__ = ["TaskBackend", "TaskItem", "create_backend"]
