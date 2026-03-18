import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# 🔥 JSONを環境変数から読み込む（Railway対応）
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)


def _open_spread(server_name):
    return client.open(server_name)


def _get_sheet(server_name):
    sh = _open_spread(server_name)
    try:
        ws = sh.worksheet("Interviews")
    except:
        ws = sh.add_worksheet(title="Interviews", rows=1000, cols=10)
        ws.append_row(["UserID", "UserName", "Date", "Time"])
    return ws


def _get_log_sheet(server_name):
    sh = _open_spread(server_name)
    try:
        ws = sh.worksheet("Logs")
    except:
        ws = sh.add_worksheet(title="Logs", rows=1000, cols=10)
        ws.append_row(["Timestamp", "Action", "User", "Detail"])
    return ws


def _get_settings_sheet(server_name):
    sh = _open_spread(server_name)
    try:
        ws = sh.worksheet("Settings")
    except:
        ws = sh.add_worksheet(title="Settings", rows=10, cols=2)
        ws.append_row(["Key", "Value"])
    return ws


def save_log(server_name, action, user, detail):
    ws = _get_log_sheet(server_name)
    ws.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        action,
        user,
        detail,
    ])


def is_time_conflict(server_name, date, time_str):
    ws = _get_sheet(server_name)
    rows = ws.get_all_values()[1:]
    for r in rows:
        if r[2] == date and r[3] == time_str:
            return True
    return False


def save_interview(server_name, user_id, user_name, date, time_str):
    ws = _get_sheet(server_name)
    ws.append_row([user_id, user_name, date, time_str])
    save_log(server_name, "RESERVE", user_name, f"{date} {time_str}")


def cancel_interview(server_name, user_id):
    ws = _get_sheet(server_name)
    cell = ws.find(user_id)
    if cell:
        ws.delete_rows(cell.row)
        save_log(server_name, "CANCEL", user_id, "Interview cancelled")
        return True
    return False


def list_interviews(server_name):
    ws = _get_sheet(server_name)
    return ws.get_all_values()[1:]


def set_notify_channel(server_name, channel_id):
    ws = _get_settings_sheet(server_name)
    data = ws.get_all_values()
    for i, row in enumerate(data):
        if row[0] == "notify_channel":
            ws.update_cell(i + 1, 2, channel_id)
            return
    ws.append_row(["notify_channel", channel_id])


def get_notify_channel(server_name):
    ws = _get_settings_sheet(server_name)
    data = ws.get_all_values()
    for row in data:
        if row[0] == "notify_channel":
            return int(row[1])
    return None