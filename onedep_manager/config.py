import os
import yaml
import logging

from onedep_manager.schemas import Service
from wwpdb.utils.config.ConfigInfo import ConfigInfo


class Config:
    def __init__(self, config_file: str = None):
        if not config_file:
            onedep_root = ConfigInfo().get("TOP_SOFTWARE_DIR")
            config_file = os.path.join(onedep_root, "odm", "config.yaml")

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
