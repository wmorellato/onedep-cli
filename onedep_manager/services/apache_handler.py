import time
import psutil
import subprocess

from onedep_manager.services.handlers import Handler, Parser
from onedep_manager.services.schemas import Status
from wwpdb.utils.config.ConfigInfo import ConfigInfo


class ApacheHandler(Handler):
    def __init__(self) -> None:
        self.config = ConfigInfo()

    def start(self):
        site_config_dir = self.config.get("TOP_WWPDB_SITE_CONFIG_DIR")

        try:
            subprocess.run([f"{site_config_dir}/apache_config/httpd-opt", "start"], check=True, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            return Status.FAILED

        return self.status()

    def stop(self):
        try:
            subprocess.run([f"killall", "httpd"], check=True)
        except subprocess.CalledProcessError as e:
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
    handler = ApacheHandler()
    Parser(handler=handler).run()
