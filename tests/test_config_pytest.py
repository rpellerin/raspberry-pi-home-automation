# import pytest
from unittest.mock import patch, mock_open

mock_config_file = """
[weatherstation]
GOOGLE_SCRIPTS_URL=https://some.url

[pushover]
PUSHOVER_USER=456
PUSHOVER_TOKEN=654
"""


@patch("builtins.open", mock_open(read_data=mock_config_file))
class TestClass:
    def test_check_config_contains_google_scripts_url(self):
        # This needs to be imported only now, for the mock to work
        from home_automation.config import GOOGLE_SCRIPTS_URL

        assert GOOGLE_SCRIPTS_URL == "https://some.url"

    def test_check_config_contains_pushover_credentials(self):
        # This needs to be imported only now, for the mock to work
        from home_automation.config import PUSHOVER_USER, PUSHOVER_TOKEN

        assert PUSHOVER_USER == "456"
        assert PUSHOVER_TOKEN == "654"
