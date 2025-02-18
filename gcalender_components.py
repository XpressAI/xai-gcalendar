from xai_components.base import InArg, OutArg, Component, xai_component, InCompArg
from googleapiclient.discovery import build
from google.oauth2 import service_account
import base64
import json
import os

@xai_component()
class AuthenticateGoogleCalendar(Component):
    """Handles authentication for Google Calendar API."""
    service_account_json: InArg[str]

    def execute(self, ctx) -> None:
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        SERVICE_ACCOUNT_FILE = self.service_account_json.value
        if SERVICE_ACCOUNT_FILE and os.path.exists(SERVICE_ACCOUNT_FILE):
            print(f"Using provided service account JSON: {SERVICE_ACCOUNT_FILE}")
            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            service = build('calendar', 'v3', credentials=credentials)
        else:
            encoded_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS")
            if not encoded_json:
                raise ValueError("Neither a valid file path nor GOOGLE_SERVICE_ACCOUNT_CREDENTIALS environment variable was found.")
            
            gcal_creds = json.loads(base64.b64decode(encoded_json).decode())
            creds = service_account.Credentials.from_service_account_info(gcal_creds, scopes=SCOPES)
            service = build('calendar', 'v3', credentials=creds)

        ctx.update({'service': service})
        print("Google Calendar authentication completed successfully.")


@xai_component()
class GetGoogleCalendarEvents(Component):
    """Component to fetch and structure Google Calendar events."""
    calendar_id: InArg[str]
    date: InArg[str]
    events: OutArg[dict]

    def execute(self, ctx) -> None:
        try:
            service = ctx["service"]
            events_result = service.events().list(
                calendarId=self.calendar_id.value,
                timeMin=self.date.value + 'T00:00:00Z',
                timeMax=self.date.value + 'T23:59:59Z',
                singleEvents=True
            ).execute()

            events = events_result.get('items', [])
            if not events:
                self.events.value = {"message": "No events found for the specified day."}
            else:
                events_list = []
                for event in events:
                    event_details = {
                        "event_name": event.get('summary', 'No Title'),
                        "start_time": event['start'].get('dateTime', event['start'].get('date')),
                        "end_time": event['end'].get('dateTime', event['end'].get('date')),
                        "location": event.get('location', ''),
                        "participants": [participant['email'] for participant in event.get('attendees', [])],
                        "gmeet_link": event.get('hangoutLink', ''),
                        "meeting_id": self.extract_meeting_id(event.get('hangoutLink', ''))
                    }
                    events_list.append(event_details)

                self.events.value = {"events": events_list}
        except Exception as e:
            self.events.value = {"error": str(e)}

    @staticmethod
    def extract_meeting_id(meet_url):
        """Extract the meeting ID from the Google Meet URL."""
        if meet_url:
            return meet_url.split('/')[-1]
        return None


@xai_component()
class CreateGoogleCalendarEvent(Component):
    """A component that creates a new event in Google Calendar."""
    calendar_id: InArg[str]
    summary: InCompArg[str]
    start_time: InCompArg[str]
    end_time: InCompArg[str]
    location: InArg[str]
    participants: InArg[list]
    event_id: OutArg[str]

    def execute(self, ctx) -> None:
        try:
            CALENDAR_ID = self.calendar_id.value
            service = ctx["service"]

            event = {
                'summary': self.summary.value,
                'start': {'dateTime': self.start_time.value, 'timeZone': 'UTC'},
                'end': {'dateTime': self.end_time.value, 'timeZone': 'UTC'}
            }

            if self.location.value:
                event['location'] = self.location.value

            if self.participants.value:
                attendees = [{'email': participant} for participant in self.participants.value]
                event['attendees'] = attendees

            created_event = service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
            self.event_id.value = created_event['id']
        except Exception as e:
            self.event_id.value = {"error": str(e)}


@xai_component()
class ModifyGoogleCalendarEvent(Component):
    """A component that modifies a Google Calendar event."""
    event_id: InArg[str]
    new_summary: InArg[str]
    new_description: InArg[str]
    calendar_id: InArg[str]  # Optional: defaults to "primary" if not provided.
    modified_event_id: OutArg[str]

    def execute(self, ctx) -> None:
        try:
            service = ctx["service"]
            cal_id = self.calendar_id.value if self.calendar_id.value else "primary"

            event = service.events().get(calendarId=cal_id, eventId=self.event_id.value).execute()
            event['summary'] = self.new_summary.value
            event['description'] = self.new_description.value

            updated_event = service.events().update(calendarId=cal_id, eventId=self.event_id.value, body=event).execute()
            self.modified_event_id.value = updated_event['id']
        except Exception as e:
            self.modified_event_id.value = {"error": str(e)}


@xai_component()
class DeleteGoogleCalendarEvent(Component):
    """A component that deletes a Google Calendar event."""
    event_id: InArg[str]
    calendar_id: InArg[str]  # Optional: defaults to "primary" if not provided.
    deletion_status: OutArg[str]

    def execute(self, ctx) -> None:
        try:
            service = ctx["service"]
            cal_id = self.calendar_id.value if self.calendar_id.value else "primary"

            service.events().delete(calendarId=cal_id, eventId=self.event_id.value).execute()
            self.deletion_status.value = {"status": "Event deleted successfully."}
        except Exception as e:
            self.deletion_status.value = {"error": str(e)}


@xai_component()
class ExtractEventFromJsonString(Component):
    """Extracts event details from a JSON string."""
    json: InCompArg[str]
    summary: OutArg[str]
    start_time: OutArg[str]
    end_time: OutArg[str]
    location: OutArg[str]
    participants: OutArg[list]

    def execute(self, ctx) -> None:
        try:
            data = json.loads(self.json.value)
            self.summary.value = data['summary']
            self.start_time.value = data['start_time']
            self.end_time.value = data['end_time']
            self.location.value = data.get('location', '')
            self.participants.value = data.get('participants', [])
        except Exception as e:
            self.summary.value = {"error": str(e)}
