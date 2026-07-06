from app.listeners.db_listeners import DbListener


class ListenersManager:
    @classmethod
    def listeners(cls):
        return DbListener.listeners()
