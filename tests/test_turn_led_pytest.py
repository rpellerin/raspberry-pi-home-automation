import unittest
from unittest.mock import patch, MagicMock

MockRPi = MagicMock()
modules = {
    "RPi": MockRPi,
    "RPi.GPIO": MockRPi.GPIO,
}
patcher = patch.dict("sys.modules", modules)
patcher.start()

# We need to mock RPi before importing our module
import home_automation.turn_led as turn_led


@patch("logging.info")
class TestTurnLed(unittest.TestCase):
    @patch("RPi.GPIO.setup")
    @patch("RPi.GPIO.output")
    def test_turn_off(self, patched_output, patched_setup, mock_logging):
        turn_led.turn_off()
        patched_setup.assert_called_with(23, MockRPi.GPIO.OUT)
        patched_output.assert_called_with(23, MockRPi.GPIO.LOW)
        mock_logging.assert_called_with("LED off")

    @patch("RPi.GPIO.setup")
    @patch("RPi.GPIO.output")
    def test_turn_on(self, patched_output, patched_setup, mock_logging):
        turn_led.turn_on()
        patched_setup.assert_called_with(23, MockRPi.GPIO.OUT)
        patched_output.assert_called_with(23, MockRPi.GPIO.HIGH)
        mock_logging.assert_called_with("LED on")

    def test_cleanup(self, mock_logging):
        with patch("RPi.GPIO.cleanup") as mock_cleanup:
            turn_led.cleanup()
            mock_cleanup.assert_called_once()
            mock_logging.assert_called_with("LED cleaned up")
