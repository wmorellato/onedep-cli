import importlib

from onedep_manager.config import Config


class Dispatcher:
    def __init__(self, config: Config, local: bool = False) -> None:
        self._local = local
        self._config = config
    
    def _get_handler(self, handler: str) -> None:
        module, klass = handler.rsplit(".", 1)

        try:
            mod = importlib.import_module(module)
            handler = getattr(mod, klass)
            return handler
        except Exception as e:
            raise Exception(f"Could not load handler {handler}: {e}")

    def start_service(self, service: str) -> None:
        serv = self._config.get_service(service)
        handler = self._get_handler(serv.handler)
        handler().start()
