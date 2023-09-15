import subprocess
import psutil

from onedep_manager.services.handlers import Handler, Parser
from onedep_manager.services.schemas import Status
from wwpdb.utils.config.ConfigInfo import ConfigInfo


class ApacheHandler(Handler):
    def __init__(self) -> None:
        self.config = ConfigInfo()

    def start(self):
        # execute a command on the os to start an application
        # and return the status
        site_config_dir = self.config.get("TOP_WWPDB_SITE_CONFIG_DIR")

        try:
            subprocess.run([f"{site_config_dir}/apache_config/httpd-opt", "start"], check=True)
        except subprocess.CalledProcessError as e:
            return Status.FAILED

        return self.status()

    def stop(self):
        ...

    def restart(self):
        ...

    def status(self):
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            if proc.info['name'] == 'httpd':
                return Status.RUNNING

        return Status.STOPPED


if __name__ == "__main__":
    # provide a command line parser to the handler
    handler = ApacheHandler()
    Parser(handler=handler).run()
