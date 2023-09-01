import yaml

from onedep_manager.schemas import Service


class Config:
    def __init__(self, config_file):
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
