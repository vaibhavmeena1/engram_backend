from tortoise import Tortoise
from vortex import CONFIG
from vortex.constants.constants import LifespanEvent
from vortex.logging.log import logger


class DbListener:
    @classmethod
    async def setup_db(cls, app):  # pylint: disable=W0613
        """
        Listener function to set up a connection to the PostgreSQL database using Tortoise ORM.

        Args:
            app: current app instance

        Returns:
            None
        """
        try:
            db_config = CONFIG.config.get("DB_CONNECTIONS")

            if not db_config:
                logger.error("DB_CONNECTIONS configuration not found in config")
                raise ValueError("DB_CONNECTIONS configuration is missing")

            logger.info("Initializing Tortoise ORM connection...")
            await Tortoise.init(config=db_config)
            await Tortoise.generate_schemas(safe=True)
            logger.info("Tortoise ORM connection established successfully")

        except Exception:
            logger.exception("Failed to initialize Tortoise ORM")
            raise

    @classmethod
    async def teardown_db(cls, app):  # pylint: disable=W0613
        """
        Listener function to close connection to the PostgreSQL database.

        Args:
            app: current app instance

        Returns:
            None
        """
        try:
            logger.info("Closing Tortoise ORM connections...")
            await Tortoise.close_connections()
            logger.info("Tortoise ORM connections closed successfully")
        except Exception:
            logger.exception("Error closing Tortoise ORM connections")

    @classmethod
    def listeners(cls):
        """
        Returns list of listener functions and their lifecycle events.

        Returns:
            List of tuples containing (listener_function, event_type)
        """
        return [
            (cls.setup_db, LifespanEvent.STARTUP.value),
            (cls.teardown_db, LifespanEvent.SHUTDOWN.value),
        ]
