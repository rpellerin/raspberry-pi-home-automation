import json
import requests
from unittest.mock import patch, MagicMock
from home_automation.remote_control import (
    report_alarm_status_and_fetch_sheet_data,
    update_alarm_state,
    run
)

@patch('home_automation.remote_control.requests.get')
@patch('home_automation.remote_control.GOOGLE_SCRIPTS_URL', 'http://mock-url')
def test_report_alarm_status_success(mock_get):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = json.dumps({"shouldEnableAlarm": "yes", "shouldReboot": "no"})
    mock_get.return_value = mock_response

    success, data = report_alarm_status_and_fetch_sheet_data(is_alarm_enabled="yes")

    assert success is True
    assert data == {"shouldEnableAlarm": "yes", "shouldReboot": "no"}
    mock_get.assert_called_once_with(
        'http://mock-url',
        params={"remote_control": "yes"},
        timeout=20
    )

@patch('home_automation.remote_control.requests.get')
def test_report_alarm_status_exception(mock_get, capsys):
    # Setup mock to raise exception
    mock_get.side_effect = requests.exceptions.RequestException("Network error")

    success, data = report_alarm_status_and_fetch_sheet_data(is_alarm_enabled="no")

    assert success is False
    assert data is None
    
    # Verify stderr output
    captured = capsys.readouterr()
    assert "RequestException occurred: Network error" in captured.err

@patch('home_automation.remote_control.report_alarm_status_and_fetch_sheet_data')
def test_update_alarm_state_changes(mock_report_alarm_status_and_fetch_sheet_data):
    mock_redis = MagicMock()
    # Mock return value to avoid unpacking error
    mock_report_alarm_status_and_fetch_sheet_data.return_value = (True, {})
    
    # Current state is "0" (disabled), requested state is "yes" (enable)
    update_alarm_state(
        should_enable_alarm="yes",
        current_alarm_state="0",
        r=mock_redis
    )
    
    mock_redis.set.assert_called_once_with("alarm_state", "1")
    mock_report_alarm_status_and_fetch_sheet_data.assert_called_once_with(is_alarm_enabled="yes")

@patch('home_automation.remote_control.report_alarm_status_and_fetch_sheet_data')
def test_update_alarm_state_no_change(mock_report_alarm_status_and_fetch_sheet_data):
    mock_redis = MagicMock()

    # Current state is "1" (enabled), requested state is "yes" (remain enabled)
    update_alarm_state(
        should_enable_alarm="yes",
        current_alarm_state="1",
        r=mock_redis
    )

    mock_redis.set.assert_not_called()
    mock_report_alarm_status_and_fetch_sheet_data.assert_not_called()

@patch('home_automation.remote_control.report_alarm_status_and_fetch_sheet_data')
def test_update_alarm_state_sync_failure(mock_report_alarm_status_and_fetch_sheet_data, capsys):
    mock_redis = MagicMock()
    # Mock the sync call to fail
    mock_report_alarm_status_and_fetch_sheet_data.return_value = (False, None)

    # Current state is "0" (disabled), requested state is "yes" (enable)
    update_alarm_state(
        should_enable_alarm="yes",
        current_alarm_state="0",
        r=mock_redis
    )

    # Redis should still be updated
    mock_redis.set.assert_called_once_with("alarm_state", "1")

    # Error should be printed to stderr
    captured = capsys.readouterr()
    assert "Could not push change of alarm state to the sheet (new state: 1)" in captured.err

@patch('home_automation.remote_control.redis.Redis')
@patch('home_automation.remote_control.report_alarm_status_and_fetch_sheet_data')
def test_run_success(mock_report_alarm_status_and_fetch_sheet_data, mock_redis_class):
    # Setup redis mock
    mock_redis = MagicMock()
    mock_redis.get.return_value = "1"
    mock_redis_class.return_value = mock_redis

    # Setup report mock (requesting alarm to be disabled)
    mock_report_alarm_status_and_fetch_sheet_data.return_value = (True, {"shouldEnableAlarm": "no", "shouldReboot": ""})

    result = run()

    assert result is True
    mock_redis.get.assert_called_with("alarm_state")
    
    # Verify the new state was passed to Redis
    mock_redis.set.assert_called_with("alarm_state", "0")

    # Verify both calls to the report function
    from unittest.mock import call
    mock_report_alarm_status_and_fetch_sheet_data.assert_has_calls([
        call(is_alarm_enabled="yes"), # First to fetch the data from the cell
        call(is_alarm_enabled="no") # Then to update again the last status to the spreadsheet, following the local update
    ])

@patch('home_automation.remote_control.redis.Redis')
@patch('home_automation.remote_control.report_alarm_status_and_fetch_sheet_data')
def test_run_failure(mock_report_alarm_status_and_fetch_sheet_data, mock_redis_class, capsys):
    # Setup redis mock
    mock_redis = MagicMock()
    mock_redis.get.return_value = "0"
    mock_redis_class.return_value = mock_redis

    # Setup report mock to return failure
    mock_report_alarm_status_and_fetch_sheet_data.return_value = (False, None)

    result = run()

    assert result is False
    mock_redis.get.assert_called_with("alarm_state")
    mock_report_alarm_status_and_fetch_sheet_data.assert_called_with(is_alarm_enabled="no")
    captured = capsys.readouterr()
    assert "Error when fetching sheet data" in captured.err
    assert "Failed to fetch 'remote_control' from App Script" in captured.err

@patch('home_automation.remote_control.redis.Redis')
@patch('home_automation.remote_control.report_alarm_status_and_fetch_sheet_data')
@patch('home_automation.remote_control.initiate_reboot')
def test_run_triggers_reboot(mock_initiate_reboot, mock_report_alarm_status_and_fetch_sheet_data, mock_redis_class):
    # Setup redis mock
    mock_redis = MagicMock()
    mock_redis.get.return_value = "1"
    mock_redis_class.return_value = mock_redis

    # Setup report mock (requesting reboot)
    mock_report_alarm_status_and_fetch_sheet_data.return_value = (True, {"shouldEnableAlarm": "", "shouldReboot": "yes"})

    result = run()

    assert result is True
    mock_initiate_reboot.assert_called_once()
