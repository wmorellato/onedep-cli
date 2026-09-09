import time
import psutil
import subprocess

from onedep_manager.services.handlers import Handler, Parser
from onedep_manager.services.schemas import Status
from onedep_manager.config import Config


class ApacheHandler(Handler):
    def __init__(self, config: Config) -> None:
        super().__init__(config)

    def start(self):
        site_config_dir = self._config.from_site("TOP_WWPDB_SITE_CONFIG_DIR")

        try:
            subprocess.run([f"{site_config_dir}/apache_config/httpd-opt", "start"], check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            return Status.FAILED

        return self.status()

    def stop(self):
        # Scoped to this instance's own httpd, unlike a bare `killall httpd`
        # which would kill every Apache process on a shared host.
        site_config_dir = self._config.from_site("TOP_WWPDB_SITE_CONFIG_DIR")

        try:
            subprocess.run([f"{site_config_dir}/apache_config/httpd-opt", "stop"], check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            return Status.FAILED

        return self.status()

    def restart(self):
        self.stop()
        time.sleep(1) # needed this
        return self.start()

    def status(self):
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            if proc.info['name'] == 'httpd':
                return Status.RUNNING

        return Status.STOPPED


if __name__ == "__main__":
    handler = ApacheHandler(config=Config())
    print(Parser(handler=handler).run())
