from unittest.mock import patch, mock_open
import pytest
from importlib import reload
import subprocess


class TestConfig:
    def test_warns_when_calling_the_cli_without_an_action(self):
        output = subprocess.run(
            ["python3", "-m", "home_automation"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert output.stdout.decode("utf-8") == ""
        assert output.stderr.decode("utf-8") == "No action given.\n"
        assert output.returncode == 1

    def test_warns_when_calling_the_cli_with_an_unknown_action(self):
        output = subprocess.run(
            ["python3", "-m", "home_automation", "yolo"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert output.stdout.decode("utf-8") == ""
        assert output.stderr.decode("utf-8") == "Unknown action: yolo\n"
        assert output.returncode == 1
