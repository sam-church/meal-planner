import os
from datetime import datetime, timedelta
import pytz
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'data', 'credentials.json')
TOKEN_PATH = os.path.join(BASE_DIR, 'data', 'token.json')

# Map slot key prefix to day offset from Monday (0=Mon)
DAY_OFFSETS = {'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sunday': 6}


def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)


def find_calendar_id(service, calendar_name):
    calendars = service.calendarList().list().execute()
    for cal in calendars.get('items', []):
        if cal['summary'] == calendar_name:
            return cal['id']
    return None


def _delete_week_events(service, calendar_id, week_key):
    """Delete all events previously synced for this week (identified by private extended property)."""
    page_token = None
    while True:
        results = service.events().list(
            calendarId=calendar_id,
            privateExtendedProperty=f'meal_planner_week={week_key}',
            pageToken=page_token,
        ).execute()
        for event in results.get('items', []):
            service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
        page_token = results.get('nextPageToken')
        if not page_token:
            break


def sync_week(week_plan, slots_with_recipes, config):
    service = get_calendar_service()
    calendar_id = find_calendar_id(service, config.CALENDAR_NAME)
    if not calendar_id:
        raise ValueError(f"Calendar '{config.CALENDAR_NAME}' not found in your Google account")

    week_key = str(week_plan.week_start_date)
    _delete_week_events(service, calendar_id, week_key)

    tz = pytz.timezone(config.CALENDAR_TIMEZONE)
    week_start = week_plan.week_start_date

    for slot_key, recipe in slots_with_recipes.items():
        if not recipe:
            continue

        if slot_key == 'sunday_prep':
            day_key = 'sunday'
            start_time_str = config.SUNDAY_PREP_START
        elif slot_key.endswith('_lunch'):
            day_key = slot_key[:-6]
            start_time_str = config.LUNCH_START
        elif slot_key.endswith('_dinner'):
            day_key = slot_key[:-7]
            start_time_str = config.DINNER_START
        else:
            continue

        day_offset = DAY_OFFSETS.get(day_key)
        if day_offset is None:
            continue

        from datetime import timedelta as _td
        event_date = week_start + _td(days=day_offset)

        h, m = map(int, start_time_str.split(':'))
        start_dt = tz.localize(datetime(event_date.year, event_date.month, event_date.day, h, m))
        duration_mins = (recipe.prep_time_mins or 0) + (recipe.cook_time_mins or 0)
        if duration_mins == 0:
            duration_mins = 60
        end_dt = start_dt + timedelta(minutes=duration_mins)

        event = {
            'summary': recipe.name,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': config.CALENDAR_TIMEZONE},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': config.CALENDAR_TIMEZONE},
            'extendedProperties': {'private': {'meal_planner_week': week_key}},
        }
        service.events().insert(calendarId=calendar_id, body=event).execute()
