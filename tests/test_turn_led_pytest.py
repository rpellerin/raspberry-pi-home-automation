import unittest
from unittest.mock import patch, MagicMock
import logging
import home_automation.turn_led as turn_led

class TestTurnLed(unittest.TestCase):
    @patch('turn_led.GPIO')
    def test_turn_off(self, mock_gpio):
        with patch('turn_led.logging') as mock_logging:
            turn_led.turn_off()
            mock_gpio.setup.assert_called_with(23, mock_gpio.OUT)
            mock_gpio.output.assert_called_with(23, mock_gpio.LOW)
            mock_logging.info.assert_called_with("LED off")

    @patch('turn_led.GPIO')
    def test_turn_on(self, mock_gpio):
        with patch('turn_led.logging') as mock_logging:
            turn_led.turn_on()
            mock_gpio.setup.assert_called_with(23, mock_gpio.OUT)
            mock_gpio.output.assert_called_with(23, mock_gpio.HIGH)
            mock_logging.info.assert_called_with("LED on")

    @patch('turn_led.GPIO')
    def test_cleanup(self, mock_gpio):
        with patch('turn_led.logging') as mock_logging:
            turn_led.cleanup()
            mock_gpio.cleanup.assert_called_once()
            mock_logging.info.assert_called_with("LED cleaned up")
