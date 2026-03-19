import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# 🔥ここ変更
creds_dict = json.loads(os.getenv("GOOGLE_CREDENTIALS"))

creds = ServiceAccountCredentials.from_json_keyfile_dict(
    creds_dict, scope
)

client = gspread.authorize(creds)
sheet = client.open("interview_bot").sheet1

# ================= 保存 =================

def save_interview(guild_id, user_id, name, date, time):
    sheet.append_row([
        str(guild_id),
        str(user_id),
        name,
        date,
        time
    ])

# ================= 一覧 =================

def list_interviews(guild_id):
    data = sheet.get_all_values()
    result = []

    for row in data:
        if row[0] == str(guild_id):
            result.append(row)

    return result

# ================= 重複チェック =================

def is_time_conflict(guild_id, date, time):
    data = sheet.get_all_values()

    for row in data:
        if (
            row[0] == str(guild_id)
            and row[3] == date
            and row[4] == time
        ):
            return True

    return False

# ================= キャンセル（完全削除） =================

def cancel_interview(guild_id, user_id):
    data = sheet.get_all_values()
    new_data = []

    removed = False

    for row in data:
        if row[0] == str(guild_id) and row[1] == str(user_id):
            removed = True
            continue  # ←これで削除
        new_data.append(row)

    sheet.clear()

    if new_data:
        sheet.append_rows(new_data)

    return removed

# ================= 通知チャンネル =================

def set_notify_channel(guild_id, channel_id):
    try:
        config_sheet = client.open("interview_bot").worksheet("config")
    except:
        config_sheet = client.open("interview_bot").add_worksheet(title="config", rows="100", cols="2")

    data = config_sheet.get_all_values()
    updated = False

    for i, row in enumerate(data):
        if row[0] == str(guild_id):
            config_sheet.update_cell(i + 1, 2, str(channel_id))
            updated = True
            break

    if not updated:
        config_sheet.append_row([str(guild_id), str(channel_id)])


def get_notify_channel(guild_id):
    try:
        config_sheet = client.open("interview_bot").worksheet("config")
    except:
        return None

    data = config_sheet.get_all_values()

    for row in data:
        if row[0] == str(guild_id):
            return row[1]

    return None