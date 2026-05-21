import sys
import importlib
from unittest.mock import MagicMock, patch, mock_open

import pytest

@pytest.fixture
def video_recorder_module():
    mock_picamera2 = MagicMock()
    mock_cv2 = MagicMock()

    # Setup complex mocks for picamera2
    mock_picamera2.encoders.H264Encoder.return_value = MagicMock()
    mock_picamera2.outputs.CircularOutput.return_value = MagicMock()
    mock_picamera2.Picamera2.return_value = MagicMock()

    fake_config = MagicMock()
    fake_config.PUSHOVER_USER = None
    fake_config.PUSHOVER_TOKEN = None

    with patch.dict(
        sys.modules,
        {
            "picamera2": mock_picamera2,
            "picamera2.encoders": mock_picamera2.encoders,
            "picamera2.outputs": mock_picamera2.outputs,
            "picamera2.MappedArray": MagicMock(),
            "libcamera": MagicMock(),
            "cv2": mock_cv2,
            "redis": MagicMock(),
            "home_automation.turn_led": MagicMock(),
            "home_automation.config": fake_config,
        },
        clear=False,
    ):
        import video_recorder

        importlib.reload(video_recorder)
        yield video_recorder

@pytest.fixture(autouse=True)
def reset_mocks(video_recorder_module):
    # Reset all relevant mocks before each test
    video_recorder_module.red.get.reset_mock()
    video_recorder_module.picam2.capture_file.reset_mock()
    video_recorder_module.picam2.stop_encoder.reset_mock()
    video_recorder_module.picam2.stop.reset_mock()
    video_recorder_module.encoder.output.start.reset_mock()
    video_recorder_module.encoder.output.stop.reset_mock()
    # Reset module level attributes if needed
    video_recorder_module.thread = None
    video_recorder_module.pubsub = None
    return video_recorder_module

def test_post_to_pushover_missing_creds(video_recorder_module, caplog):
    video_recorder_module.PUSHOVER_USER = None
    video_recorder_module.PUSHOVER_TOKEN = None

    result = video_recorder_module.post_to_pushover("test message", None)

    assert result is None
    assert "Missing env vars to send to Pushover" in caplog.text

@patch("video_recorder.requests.post")
def test_post_to_pushover_success_no_attachment(mock_post, video_recorder_module):
    video_recorder_module.PUSHOVER_USER = "user"
    video_recorder_module.PUSHOVER_TOKEN = "token"
    mock_post.return_value.status_code = 200

    result = video_recorder_module.post_to_pushover("test message", None)

    assert result is True
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert kwargs["data"]["message"] == "test message"

@patch("video_recorder.requests.post")
def test_post_to_pushover_success_with_attachment(mock_post, video_recorder_module):
    video_recorder_module.PUSHOVER_USER = "user"
    video_recorder_module.PUSHOVER_TOKEN = "token"
    mock_post.return_value.status_code = 200

    with patch("builtins.open", mock_open(read_data=b"fake image data")):
        result = video_recorder_module.post_to_pushover("test message", "image.jpg")

    assert result is True
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert "files" in kwargs

@patch("video_recorder.subprocess.Popen")
@patch("video_recorder.threading.Thread")
def test_post_message(mock_thread, mock_popen, video_recorder_module):
    video_recorder_module.post_message(
        "test message", push_notification_too=True, attachment="image.jpg"
    )

    mock_popen.assert_called_once()
    mock_thread.assert_called_once()
    mock_thread.return_value.start.assert_called_once()

def test_apply_timestamp(video_recorder_module):
    mock_request = MagicMock()
    mock_mapped_array_instance = (
        video_recorder_module.MappedArray.return_value.__enter__.return_value
    )
    mock_mapped_array_instance.array = MagicMock()

    video_recorder_module.apply_timestamp(mock_request)

    video_recorder_module.cv2.putText.assert_called_once()

def test_alarm_state(video_recorder_module):
    video_recorder_module.red.get.return_value = "1"
    assert video_recorder_module.alarm_state() is True

    video_recorder_module.red.get.return_value = "0"
    assert video_recorder_module.alarm_state() is False

@patch("video_recorder.turn_led.cleanup")
def test_killing_the_process(mock_led_cleanup, video_recorder_module):
    video_recorder_module.thread = MagicMock()
    video_recorder_module.pubsub = MagicMock()

    video_recorder_module.signal_handler(None, None)

    video_recorder_module.thread.stop.assert_called_once()
    video_recorder_module.pubsub.close.assert_called_once()
    mock_led_cleanup.assert_called_once()
    video_recorder_module.picam2.stop_encoder.assert_called_once()
    video_recorder_module.picam2.stop.assert_called_once()

@patch("video_recorder.post_message")
@patch("video_recorder.turn_led.turn_on")
@patch("video_recorder.turn_led.turn_off")
@patch("video_recorder.time.sleep")
@patch("video_recorder.os.system")
def test_door_opened_alarm_enabled(
    mock_os_system,
    mock_sleep,
    mock_led_off,
    mock_led_on,
    mock_post_message,
    video_recorder_module,
):
    video_recorder_module.red.get.return_value = "1"

    video_recorder_module.door_status_change({"data": "open"})

    mock_led_on.assert_called_once()
    assert mock_post_message.call_count == 5
    video_recorder_module.picam2.capture_file.assert_called()
    assert video_recorder_module.picam2.capture_file.call_count == 3
    video_recorder_module.encoder.output.start.assert_called_once()
    video_recorder_module.encoder.output.stop.assert_called_once()
    mock_os_system.assert_called()
    assert "ffmpeg" in str(mock_os_system.call_args)
    mock_led_off.assert_called_once()

@patch("video_recorder.post_message")
@patch("video_recorder.turn_led.turn_on")
@patch("video_recorder.turn_led.turn_off")
@patch("video_recorder.time.sleep")
@patch("video_recorder.os.system")
def test_door_opened_alarm_disabled(
    mock_os_system,
    mock_sleep,
    mock_led_off,
    mock_led_on,
    mock_post_message,
    video_recorder_module,
):
    video_recorder_module.red.get.return_value = "0"

    video_recorder_module.door_status_change({"data": "open"})

    mock_led_on.assert_called_once()
    mock_post_message.assert_not_called()
    video_recorder_module.picam2.capture_file.assert_called()
    video_recorder_module.encoder.output.start.assert_called_once()
    video_recorder_module.encoder.output.stop.assert_called_once()
    mock_os_system.assert_called()
    assert "ffmpeg" in str(mock_os_system.call_args)
    mock_led_off.assert_called_once()

@patch("video_recorder.post_message")
@patch("video_recorder.turn_led.turn_on")
@patch("video_recorder.turn_led.turn_off")
@patch("video_recorder.time.sleep")
@patch("video_recorder.os.system")
def test_door_closed(
    mock_os_system,
    mock_sleep,
    mock_led_off,
    mock_led_on,
    mock_post_message,
    video_recorder_module,
):
    with patch("video_recorder.logging.info") as mock_log:
        video_recorder_module.door_status_change({"data": "closed"})
        mock_log.assert_called_with("Door status received: closed")

    mock_led_on.assert_not_called()
    mock_post_message.assert_not_called()
    video_recorder_module.picam2.capture_file.assert_not_called()
    video_recorder_module.encoder.output.start.assert_not_called()
    mock_os_system.assert_not_called()
