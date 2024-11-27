import os
import yaml

from onedep_manager.schemas import Service
from wwpdb.utils.config.ConfigInfo import ConfigInfo


class Config:
    GITHUB_PACKAGE_HOST = "wwPDB"

    def __init__(self, config_file: str = None):
        self._odconfig = ConfigInfo()
        self.ODM_CONFIG_DIR = os.path.join(self._odconfig.get("TOP_SOFTWARE_DIR"), "odm")

        if not config_file:
            config_file = os.path.join(self.ODM_CONFIG_DIR, "config.yaml")

        self._config_file = config_file
        self._config = self._load_config()
    
    def _load_config(self):
        with open(self._config_file, "r") as f:
            config = yaml.safe_load(f)
        return config

    def get_services(self):
        services = []

        for service in self._config["services"]:
            services.append(Service(**service))
        
        return services

    def get_service(self, name):
        for service in self._config["services"]:
            if service["name"] == name:
                return Service(**service)

        raise Exception(f"Service {name} not found in config")

    def from_site(self, variable: str):
        return self._odconfig.get(variable)
