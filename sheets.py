import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import json

# ================= Google認証 =================

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

creds_json = os.getenv("GOOGLE_CREDENTIALS")
if not creds_json:
    raise Exception("GOOGLE_CREDENTIALS が設定されていません")

creds_dict = json.loads(creds_json)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# ================= サーバーごとのシートID =================
# 🔥 ここに追加していく（guild.idベースで最強安定）

SPREADSHEET_IDS = {
    1386159891835523183: "1bcdgi3qx7w_N_cLk8WIGRgxUs36zbRp8dXvIedg2Pw0",
    1479778341673242644: "13ItG4a4wETfTzrLhEKIxpYtSMwbAWzw4cucx_e7Dxug",
    1455791709920301232: "1xIvlmYVN793QIU5-XK10NaTLltRkJ72Rm74E7JcwxJI",
    1473657965834928190: "1WWknEx3rkS8rsd_olECSeycJ7FMHZqSpFtY2FF2WVpI",
    1091970427351465984: "1pj9D_8GhpYnDPtZWiYxgbp_-xtzfyny6xhPevGVBSlo",
    1480209775596798014: "1P26rGeTCMoVD8gdnx9X4HSLMURliuMZauWZLoNYhlkg",
    1433031788250534021: "1rhtJLjGAezk_6O_mgntb3H2CD4Gd6p5O-xyFpuluTsQ",
    1389737957187125248: "178UTrFAkRc_YgEVC1orRB7wbsqBMDVDsf4mjRYkC2z4",
    1479735252636405875: "11S_0clxAT1xq2cfNOajsGynXstosFTYlWevpeoHq5SA",
}


  
# ================= 共通 =================

def _open_spread(guild_id):
    sheet_id = SPREADSHEET_IDS.get(guild_id)

    if not sheet_id:
        print(f"未対応サーバー: {guild_id}")
        return None

    return client.open_by_key(sheet_id)


def _get_sheet(guild_id):
    sh = _open_spread(guild_id)
    try:
        ws = sh.worksheet("Interviews")
    except:
        ws = sh.add_worksheet(title="Interviews", rows=1000, cols=10)
        ws.append_row(["UserID", "UserName", "Date", "Time"])
    return ws


def _get_log_sheet(guild_id):
    sh = _open_spread(guild_id)
    try:
        ws = sh.worksheet("Logs")
    except:
        ws = sh.add_worksheet(title="Logs", rows=1000, cols=10)
        ws.append_row(["Timestamp", "Action", "User", "Detail"])
    return ws


def _get_settings_sheet(guild_id):
    sh = _open_spread(guild_id)
    if sh is None:
        return None

    try:
        ws = sh.worksheet("Settings")
    except:
        ws = sh.add_worksheet(title="Settings", rows=10, cols=2)
        ws.append_row(["Key", "Value"])
    return ws


# ================= 機能 =================

def save_log(guild_id, action, user, detail):
    ws = _get_log_sheet(guild_id)
    ws.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        action,
        user,
        detail,
    ])


def is_time_conflict(guild_id, date, time_str):
    ws = _get_sheet(guild_id)
    rows = ws.get_all_values()[1:]
    for r in rows:
        if r[2] == date and r[3] == time_str:
            return True
    return False


def save_interview(guild_id, user_id, user_name, date, time_str):
    ws = _get_sheet(guild_id)
    ws.append_row([user_id, user_name, date, time_str])
    save_log(guild_id, "RESERVE", user_name, f"{date} {time_str}")


def cancel_interview(guild_id, user_id):
    ws = _get_sheet(guild_id)
    cell = ws.find(user_id)
    if cell:
        ws.delete_rows(cell.row)
        save_log(guild_id, "CANCEL", user_id, "Interview cancelled")
        return True
    return False


def list_interviews(guild_id):
    ws = _get_sheet(guild_id)
    return ws.get_all_values()[1:]


def set_notify_channel(guild_id, channel_id):
    ws = _get_settings_sheet(guild_id)
    data = ws.get_all_values()
    for i, row in enumerate(data):
        if row[0] == "notify_channel":
            ws.update_cell(i + 1, 2, channel_id)
            return
    ws.append_row(["notify_channel", channel_id])


def get_notify_channel(guild_id):
    ws = _get_settings_sheet(guild_id)
    if ws is None:
        return None

    data = ws.get_all_values()
    for row in data:
        if row[0] == "notify_channel":
            return int(row[1])
    return None