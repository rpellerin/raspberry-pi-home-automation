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
    video_recorder_module.redis_instance.get.reset_mock()
    video_recorder_module.picam2.capture_array.reset_mock()
    video_recorder_module.cv2.imwrite.reset_mock()
    video_recorder_module.picam2.stop_encoder.reset_mock()
    video_recorder_module.picam2.stop.reset_mock()
    video_recorder_module.encoder.output.start.reset_mock()
    video_recorder_module.encoder.output.stop.reset_mock()
    video_recorder_module.clear_watchdog_task()
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
    video_recorder_module.redis_instance.get.return_value = "1"
    assert video_recorder_module.alarm_state() is True

    video_recorder_module.redis_instance.get.return_value = "0"
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
    video_recorder_module.redis_instance.get.return_value = "1"

    video_recorder_module.door_status_change({"data": "open"})

    mock_led_on.assert_called_once()
    assert mock_post_message.call_count == 5
    video_recorder_module.picam2.capture_array.assert_called()
    assert video_recorder_module.picam2.capture_array.call_count == 3
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
    video_recorder_module.redis_instance.get.return_value = "0"

    video_recorder_module.door_status_change({"data": "open"})

    mock_led_on.assert_called_once()
    mock_post_message.assert_not_called()
    video_recorder_module.picam2.capture_array.assert_called()
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
    video_recorder_module.picam2.capture_array.assert_not_called()
    video_recorder_module.encoder.output.start.assert_not_called()
    mock_os_system.assert_not_called()

@patch("video_recorder.os._exit")
@patch("video_recorder.stop_camera_and_led")
@patch("video_recorder.post_message")
@patch("video_recorder.turn_led.turn_on")
@patch("video_recorder.time.sleep")
@patch("video_recorder.os.system")
def test_camera_hardware_failure_triggers_exit(
    mock_os_system,
    mock_sleep,
    mock_led_on,
    mock_post_message,
    mock_stop_camera_and_led,
    mock_exit,
    video_recorder_module,
):
    video_recorder_module.redis_instance.get.return_value = "0"
    video_recorder_module.picam2.capture_array.side_effect = RuntimeError(
        "Camera timeout"
    )

    video_recorder_module.door_status_change({"data": "open"})

    mock_led_on.assert_called_once()
    mock_stop_camera_and_led.assert_called_once()
    mock_exit.assert_called_once_with(1)
    # Recording should NOT have started since capture_array failed first
    video_recorder_module.encoder.output.start.assert_not_called()

@patch("video_recorder.os._exit")
@patch("video_recorder.stop_camera_and_led")
@patch("video_recorder.post_message")
@patch("video_recorder.turn_led.turn_on")
@patch("video_recorder.time.sleep")
@patch("video_recorder.os.system")
def test_camera_failure_during_recording_triggers_exit(
    mock_os_system,
    mock_sleep,
    mock_led_on,
    mock_post_message,
    mock_stop_camera_and_led,
    mock_exit,
    video_recorder_module,
):
    video_recorder_module.redis_instance.get.return_value = "0"
    # First capture succeeds, second one (during recording) fails
    video_recorder_module.picam2.capture_array.side_effect = [
        None,
        RuntimeError("Hardware failure"),
    ]

    video_recorder_module.door_status_change({"data": "open"})

    mock_stop_camera_and_led.assert_called_once()
    mock_exit.assert_called_once_with(1)
    # Recording started but was interrupted
    video_recorder_module.encoder.output.start.assert_called_once()
    video_recorder_module.encoder.output.stop.assert_not_called()

@patch("video_recorder.os._exit")
@patch("video_recorder.stop_camera_and_led")
@patch("video_recorder.post_message")
@patch("video_recorder.turn_led.turn_on")
@patch("video_recorder.time.sleep")
@patch("video_recorder.os.system")
def test_camera_failure_cleanup_also_fails(
    mock_os_system,
    mock_sleep,
    mock_led_on,
    mock_post_message,
    mock_stop_camera_and_led,
    mock_exit,
    video_recorder_module,
):
    video_recorder_module.redis_instance.get.return_value = "0"
    video_recorder_module.picam2.capture_array.side_effect = RuntimeError(
        "Camera timeout"
    )
    # Cleanup itself also fails (hardware totally unresponsive)
    mock_stop_camera_and_led.side_effect = Exception("GPIO error")

    video_recorder_module.door_status_change({"data": "open"})

    # Should still exit even when cleanup fails
    mock_stop_camera_and_led.assert_called_once()
    mock_exit.assert_called_once_with(1)

import redis
@patch("video_recorder.os._exit")
@patch("video_recorder.stop_camera_and_led")
@patch("video_recorder.post_message")
@patch("video_recorder.turn_led.turn_on")
@patch("video_recorder.time.sleep")
@patch("video_recorder.os.system")
def test_redis_failure_triggers_exit(
    mock_os_system,
    mock_sleep,
    mock_led_on,
    mock_post_message,
    mock_stop_camera_and_led,
    mock_exit,
    video_recorder_module,
):
    video_recorder_module.redis_instance.get.side_effect = redis.ConnectionError("Redis connection lost")

    video_recorder_module.door_status_change({"data": "open"})

    mock_led_on.assert_not_called()
    mock_stop_camera_and_led.assert_called_once()
    mock_exit.assert_called_once_with(1)
    video_recorder_module.picam2.capture_array.assert_not_called()

def test_set_and_clear_watchdog_task(video_recorder_module):
    assert video_recorder_module.current_task is None
    video_recorder_module.set_watchdog_task("test_operation")
    assert video_recorder_module.current_task == "test_operation"
    assert video_recorder_module.task_start_time > 0

    video_recorder_module.clear_watchdog_task()
    assert video_recorder_module.current_task is None

@patch("video_recorder.os._exit")
@patch("video_recorder.time.sleep")
@patch("video_recorder.time.time")
def test_watchdog_worker_triggers_exit_when_timeout_exceeded(
    mock_time, mock_sleep, mock_exit, video_recorder_module, caplog
):
    video_recorder_module.set_watchdog_task("frozen_camera_task")
    video_recorder_module.task_start_time = 100.0
    # Simulate elapsed time > WATCHDOG_TIMEOUT (25s)
    mock_time.return_value = 130.0
    # Raise an exception on os._exit to break out of the infinite while True loop
    mock_exit.side_effect = SystemExit

    with pytest.raises(SystemExit):
        video_recorder_module.watchdog_worker()

    mock_exit.assert_called_once_with(1)
    assert "WATCHDOG TRIGGERED: Task 'frozen_camera_task' has been frozen for 30.0 seconds!" in caplog.text

@patch("video_recorder.os._exit")
@patch("video_recorder.time.sleep")
@patch("video_recorder.time.time")
def test_watchdog_worker_does_not_exit_within_timeout(
    mock_time, mock_sleep, mock_exit, video_recorder_module
):
    video_recorder_module.set_watchdog_task("normal_task")
    video_recorder_module.task_start_time = 100.0
    # Simulate elapsed time within timeout (10s < 25s)
    mock_time.return_value = 110.0
    # Allow one loop iteration then raise StopIteration to break out of the while True loop
    mock_sleep.side_effect = [None, StopIteration]

    with pytest.raises(StopIteration):
        video_recorder_module.watchdog_worker()

    mock_exit.assert_not_called()

@patch("video_recorder.os._exit")
@patch("video_recorder.time.sleep")
def test_watchdog_worker_does_not_exit_when_no_active_task(
    mock_sleep, mock_exit, video_recorder_module
):
    video_recorder_module.clear_watchdog_task()
    # Allow one loop iteration then raise StopIteration to break out of the while True loop
    mock_sleep.side_effect = [None, StopIteration]

    with pytest.raises(StopIteration):
        video_recorder_module.watchdog_worker()

    mock_exit.assert_not_called()

@patch("video_recorder.clear_watchdog_task")
@patch("video_recorder.set_watchdog_task")
@patch("video_recorder.turn_led.turn_on")
@patch("video_recorder.turn_led.turn_off")
@patch("video_recorder.time.sleep")
@patch("video_recorder.os.system")
def test_door_status_change_sets_and_clears_watchdog(
    mock_os_system,
    mock_sleep,
    mock_led_off,
    mock_led_on,
    mock_set_watchdog,
    mock_clear_watchdog,
    video_recorder_module,
):
    video_recorder_module.redis_instance.get.return_value = "0"
    video_recorder_module.door_status_change({"data": "open"})

    mock_set_watchdog.assert_called_once_with("door_status_change")
    mock_clear_watchdog.assert_called_once()

def test_watchdog_thread_is_started_and_daemon(video_recorder_module):
    assert video_recorder_module.watchdog_thread is not None
    assert video_recorder_module.watchdog_thread.is_alive()
    assert video_recorder_module.watchdog_thread.daemon is True

def test_watchdog_thread_initialization_parameters(video_recorder_module):
    with patch("threading.Thread") as mock_thread:
        mock_instance = MagicMock()
        mock_thread.return_value = mock_instance
        importlib.reload(video_recorder_module)
        mock_thread.assert_called_with(
            target=video_recorder_module.watchdog_worker, daemon=True
        )
        mock_instance.start.assert_called_once()
