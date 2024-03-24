from unittest.mock import patch, mock_open
import pytest
import configparser
from importlib import reload
import home_automation.config as config

mock_config_file_google_script_url_missing = """
[weatherstation]
GOOGLE_SCRIPTS_URL=
"""

mock_config_file = """
[weatherstation]
GOOGLE_SCRIPTS_URL=https://some.url

[pushover]
PUSHOVER_USER=456
PUSHOVER_TOKEN=654
"""


class TestConfig:
    @patch("builtins.open", mock_open(read_data=""))
    def test_check_fails_if_file_is_empty(self):
        with pytest.raises(configparser.NoSectionError):
            reload(config)

    @patch("builtins.open", mock_open(read_data="[weatherstation]"))
    def test_check_fails_if_option_in_file_is_missing(self):
        with pytest.raises(configparser.NoOptionError):
            reload(config)

    @patch(
        "builtins.open", mock_open(read_data=mock_config_file_google_script_url_missing)
    )
    def test_returns_default_values(self):
        reload(config)

        assert config.GOOGLE_SCRIPTS_URL == ""
        assert config.PUSHOVER_USER == None
        assert config.PUSHOVER_TOKEN == None

    @patch("builtins.open", mock_open(read_data=mock_config_file))
    def test_check_config_contains_google_scripts_url(self):
        reload(config)

        assert config.GOOGLE_SCRIPTS_URL == "https://some.url"

    @patch("builtins.open", mock_open(read_data=mock_config_file))
    def test_check_config_contains_pushover_credentials(self):
        reload(config)
        assert config.PUSHOVER_USER == "456"
        assert config.PUSHOVER_TOKEN == "654"
