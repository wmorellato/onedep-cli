import os
from typing import Optional, List, Tuple
from rich.console import Console

from onedep_manager.config import Config


class InfoDataRetriever:
    """Retrieves system configuration data from Config and environment variables."""

    def __init__(self, config: Config):
        self._config = config

    def get_value(self, key: str, from_env: bool = False, env_var: str = None) -> Optional[str]:
        """
        Get a configuration value from Config or environment variable.

        Args:
            key: Configuration key to retrieve
            from_env: If True, retrieve from environment variable
            env_var: Environment variable name (required if from_env is True)

        Returns:
            The configuration value or None if not found
        """
        if from_env:
            return os.environ.get(env_var)
        return self._config.from_site(key)

    def get_first_available(self, keys: List[str]) -> Optional[str]:
        """
        Get the first available value from a list of keys.

        Args:
            keys: List of configuration keys to try in order

        Returns:
            The first non-empty value found, or None
        """
        for key in keys:
            value = self._config.from_site(key)
            if value:
                return value
        return None

    def build_database_url(self, user_key: str, host_key: str, port_key: str, name_key: str) -> Optional[str]:
        """
        Build a database connection URL from configuration keys.

        Args:
            user_key: Configuration key for database user
            host_key: Configuration key for database host
            port_key: Configuration key for database port
            name_key: Configuration key for database name

        Returns:
            A formatted database URL or None if any key is missing
        """
        user = self._config.from_site(user_key)
        host = self._config.from_site(host_key)
        port = self._config.from_site(port_key)
        name = self._config.from_site(name_key)

        # If any value is None or empty, return None
        if not all([user, host, port, name]):
            return None

        return f"mysql://{user}@{host}:{port}/{name}"


class InfoFormatter:
    """Formats system information with aligned columns and colors."""

    def __init__(self, console: Console, key_width: int = 20):
        self._console = console
        self._key_width = key_width

    def print_row(self, key: str, value: Optional[str], color: str = "cyan"):
        """
        Print a formatted row with key and colored value.

        Args:
            key: The label/key to display
            value: The value to display (will be colored)
            color: Rich color name for the value
        """
        if value is None:
            value = "[dim]Not configured[/dim]"
        else:
            value = f"[{color}]{value}[/{color}]"

        padded_key = key.ljust(self._key_width)
        self._console.print(f"{padded_key} {value}")

    def print_section_header(self, title: str):
        """Print a section header."""
        self._console.print(f"\n[bold]{title}[/bold]")

    def print_empty_line(self):
        """Print an empty line."""
        self._console.print()


class InstanceInfoService:
    """Service to gather and display instance information."""

    def __init__(self, data_retriever: InfoDataRetriever, formatter: InfoFormatter):
        self._retriever = data_retriever
        self._formatter = formatter

    def display_basic_info(self):
        """Display basic site information."""
        site_id = self._retriever.get_value("site_prefix", from_env=True, env_var="WWPDB_SITE_ID")
        site_location = self._retriever.get_value("wwpdb_site_loc")
        tools_path = self._retriever.get_value("tools_path")
        slurm_queue = self._retriever.get_value("pdbe_cluster_queue")

        self._formatter.print_row("Site ID:", site_id, "green")
        self._formatter.print_row("Site location:", site_location, "yellow")
        self._formatter.print_row("Tools:", tools_path, "cyan")
        self._formatter.print_row("Slurm queue:", slurm_queue, "magenta")

    def display_databases(self):
        """Display database connection information."""
        self._formatter.print_section_header("Databases:")

        db_configs = [
            ("site_da_internal_db_user_name", "site_da_internal_db_host_name",
             "site_da_internal_db_port_number", "site_da_internal_db_name"),
            ("site_da_internal_combine_db_user_name", "site_da_internal_combine_db_host_name",
             "site_da_internal_combine_db_port_number", "site_da_internal_combine_db_name"),
            ("site_db_user_name", "site_db_host_name",
             "site_db_port_number", "site_db_database_name"),
            ("site_dep_db_user_name", "site_dep_db_host_name",
             "site_dep_db_port_number", "site_dep_db_database_name"),
            ("site_instance_db_user_name", "site_instance_db_host_name",
             "site_instance_db_port_number", "site_instance_db_name"),
            ("site_refdata_db_user_name", "site_refdata_db_host_name",
             "site_refdata_db_port_number", "site_refdata_cc_db_name"),
        ]

        for user_key, host_key, port_key, name_key in db_configs:
            db_url = self._retriever.build_database_url(user_key, host_key, port_key, name_key)
            if db_url:
                self._formatter.print_row("  ", db_url, "blue")

    def display_paths(self):
        """Display OneDep paths."""
        self._formatter.print_section_header("Paths:")

        onedep_root = self._retriever.get_first_available(["deploy_path", "top_software_path"])
        data_path = self._retriever.get_first_available(["top_data_dir", "data_path"])

        self._formatter.print_row("OneDep root:", onedep_root, "green")
        self._formatter.print_row("Data path:", data_path, "green")

    def display_all(self):
        """Display all instance information."""
        self.display_basic_info()
        self.display_databases()
        self.display_paths()
        self._formatter.print_empty_line()
