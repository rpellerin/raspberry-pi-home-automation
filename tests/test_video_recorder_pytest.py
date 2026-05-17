import sys
from unittest.mock import MagicMock, patch, mock_open

# Mocking hardware and external libraries before importing video_recorder
mock_picamera2 = MagicMock()
mock_cv2 = MagicMock()

# Setup complex mocks for picamera2
mock_picamera2.encoders.H264Encoder.return_value = MagicMock()
mock_picamera2.outputs.CircularOutput.return_value = MagicMock()
mock_picamera2.Picamera2.return_value = MagicMock()

sys.modules["picamera2"] = mock_picamera2
sys.modules["picamera2.encoders"] = mock_picamera2.encoders
sys.modules["picamera2.outputs"] = mock_picamera2.outputs
sys.modules["picamera2.MappedArray"] = MagicMock()
sys.modules["libcamera"] = MagicMock()
sys.modules["cv2"] = mock_cv2
sys.modules["redis"] = MagicMock()

# Mock home_automation.turn_led and home_automation.config
sys.modules["home_automation.turn_led"] = MagicMock()
sys.modules["home_automation.config"] = MagicMock()

import video_recorder
import pytest

@pytest.fixture(autouse=True)
def reset_mocks():
    # Reset all relevant mocks before each test
    video_recorder.red.get.reset_mock()
    video_recorder.picam2.capture_file.reset_mock()
    video_recorder.picam2.stop_encoder.reset_mock()
    video_recorder.picam2.stop.reset_mock()
    video_recorder.encoder.output.start.reset_mock()
    video_recorder.encoder.output.stop.reset_mock()
    # Reset module level attributes if needed
    video_recorder.thread = None
    video_recorder.pubsub = None

def test_post_to_pushover_missing_creds(caplog):
    video_recorder.PUSHOVER_USER = None
    video_recorder.PUSHOVER_TOKEN = None

    result = video_recorder.post_to_pushover("test message", None)

    assert result is None
    assert "Missing env vars to send to Pushover" in caplog.text

@patch("video_recorder.requests.post")
def test_post_to_pushover_success_no_attachment(mock_post):
    video_recorder.PUSHOVER_USER = "user"
    video_recorder.PUSHOVER_TOKEN = "token"
    mock_post.return_value.status_code = 200

    result = video_recorder.post_to_pushover("test message", None)

    assert result is True
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert kwargs["data"]["message"] == "test message"

@patch("video_recorder.requests.post")
def test_post_to_pushover_success_with_attachment(mock_post):
    video_recorder.PUSHOVER_USER = "user"
    video_recorder.PUSHOVER_TOKEN = "token"
    mock_post.return_value.status_code = 200

    # We need to mock open for the attachment
    with patch("builtins.open", mock_open(read_data=b"fake image data")):
        result = video_recorder.post_to_pushover("test message", "image.jpg")

    assert result is True
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert "files" in kwargs

# Sends an email and a Pushover notification
@patch("video_recorder.subprocess.Popen")
@patch("video_recorder.threading.Thread")
def test_post_message(mock_thread, mock_popen):
    video_recorder.post_message("test message", push_notification_too=True, attachment="image.jpg")

    mock_popen.assert_called_once()
    mock_thread.assert_called_once()
    # Verify thread was started
    mock_thread.return_value.start.assert_called_once()

# Adds a timestamp on each frame of the video
def test_apply_timestamp():
    mock_request = MagicMock()
    # MappedArray is used as a context manager
    mock_mapped_array_instance = video_recorder.MappedArray.return_value.__enter__.return_value
    mock_mapped_array_instance.array = MagicMock()

    video_recorder.apply_timestamp(mock_request)

    mock_cv2.putText.assert_called_once()

def test_alarm_state():
    video_recorder.red.get.return_value = "1"
    assert video_recorder.alarm_state() is True

    video_recorder.red.get.return_value = "0"
    assert video_recorder.alarm_state() is False

# CTRL+C, killing the process...
@patch("video_recorder.turn_led.cleanup")
def test_killing_the_process(mock_led_cleanup):
    video_recorder.thread = MagicMock()
    video_recorder.pubsub = MagicMock()

    video_recorder.signal_handler(None, None)

    video_recorder.thread.stop.assert_called_once()
    video_recorder.pubsub.close.assert_called_once()
    mock_led_cleanup.assert_called_once()
    video_recorder.picam2.stop_encoder.assert_called_once()
    video_recorder.picam2.stop.assert_called_once()

@patch("video_recorder.post_message")
@patch("video_recorder.turn_led.turn_on")
@patch("video_recorder.turn_led.turn_off")
@patch("video_recorder.time.sleep")
@patch("video_recorder.os.system")
def test_door_opened_alarm_enabled(mock_os_system, mock_sleep, mock_led_off, mock_led_on, mock_post_message):
    video_recorder.red.get.return_value = "1" # Alarm enabled

    video_recorder.door_status_change({"data": "open"})

    mock_led_on.assert_called_once()
    # Check if multiple `post_message`` calls were made
    assert mock_post_message.call_count == 5 # Door opened, photo 1, photo 2, photo 3, video
    video_recorder.picam2.capture_file.assert_called()
    assert video_recorder.picam2.capture_file.call_count == 3
    video_recorder.encoder.output.start.assert_called_once()
    video_recorder.encoder.output.stop.assert_called_once()
    mock_os_system.assert_called() # ffmpeg is called
    assert "ffmpeg" in str(mock_os_system.call_args)
    mock_led_off.assert_called_once()

@patch("video_recorder.post_message")
@patch("video_recorder.turn_led.turn_on")
@patch("video_recorder.turn_led.turn_off")
@patch("video_recorder.time.sleep")
@patch("video_recorder.os.system")
def test_door_opened_alarm_disabled(mock_os_system, mock_sleep, mock_led_off, mock_led_on, mock_post_message):
    video_recorder.red.get.return_value = "0" # Alarm disabled

    video_recorder.door_status_change({"data": "open"})

    mock_led_on.assert_called_once()
    # `post_message` should not be called since the alarm is not enabled
    mock_post_message.assert_not_called()
    video_recorder.picam2.capture_file.assert_called()
    video_recorder.encoder.output.start.assert_called_once()
    video_recorder.encoder.output.stop.assert_called_once()
    mock_os_system.assert_called() # ffmpeg is called
    assert "ffmpeg" in str(mock_os_system.call_args)
    mock_led_off.assert_called_once()

@patch("video_recorder.post_message")
@patch("video_recorder.turn_led.turn_on")
@patch("video_recorder.turn_led.turn_off")
@patch("video_recorder.time.sleep")
@patch("video_recorder.os.system")
def test_door_closed(mock_os_system, mock_sleep, mock_led_off, mock_led_on, mock_post_message):
    with patch("video_recorder.logging.info") as mock_log:
        video_recorder.door_status_change({"data": "closed"})
        mock_log.assert_called_with("Door status received: closed")

    # Ensure none of the hardware/external actions were taken
    mock_led_on.assert_not_called()
    mock_post_message.assert_not_called()
    video_recorder.picam2.capture_file.assert_not_called()
    video_recorder.encoder.output.start.assert_not_called()
    mock_os_system.assert_not_called()
