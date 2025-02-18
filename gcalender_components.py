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
            credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
            service = build('calendar', 'v3', credentials=credentials)
        else:
            encoded_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS")
            if not encoded_json:
                raise ValueError("Neither a valid file path nor GOOGLE_SERVICE_ACCOUNT_CREDENTIALS environment variable was found.")
            
            gcalender_creds = json.loads(base64.b64decode(encoded_json).decode())
            creds = service_account.Credentials.from_service_account_info(gcalender_creds, scopes=SCOPES)
            service = build('calendar', 'v3', credentials=creds)

        ctx.update({'service':service})

        print("Google Calender authentication completed successfully.")


@xai_component()
class GetGcalenderEvents(Component):
    """Component to fetch and structure Google Calendar meetings."""
    calender_id: InArg[str]
    date: InArg[str]
    events: OutArg[dict]

    def execute(self, ctx) -> None:
        try:
            service = ctx["service"]

            events_result = service.events().list(
                calendarId=self.calender_id.value,
                timeMin=self.date.value + 'T00:00:00Z',
                timeMax=self.date.value + 'T23:59:59Z',
                singleEvents=True
            ).execute()

            events = events_result.get('items', [])
            if not events:
                self.events.value = {"message": "No events found for the specified day."}
            else:
                events_dict = []
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
                    events_dict.append(event_details)

                self.events.value = {"events": events_dict}
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
    service_account_json: InCompArg[str]
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
    service_account_json: InCompArg[str]
    event_id: InArg[str]
    new_summary: InArg[str]
    new_description: InArg[str]
    modified_event_id: OutArg[str]

    def execute(self, ctx) -> None:
        try:
            service = ctx["service"]

            event = service.events().get(calendarId='primary', eventId=self.event_id.value).execute()
            event['summary'] = self.new_summary.value
            event['description'] = self.new_description.value

            updated_event = service.events().update(calendarId='primary', eventId=self.event_id.value, body=event).execute()
            self.modified_event_id.value = updated_event['id']
        except Exception as e:
            self.modified_event_id.value = {"error": str(e)}


@xai_component()
class DeleteGoogleCalendarEvent(Component):
    """A component that deletes a Google Calendar event."""
    service_account_json: InCompArg[str]
    event_id: InArg[str]
    deletion_status: OutArg[str]

    def execute(self, ctx) -> None:
        try:
            service = service = ctx["service"]

            service.events().delete(calendarId='primary', eventId=self.event_id.value).execute()
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
            d = json.loads(self.json.value)
            self.summary.value = d['summary']
            self.start_time.value = d['start_time']
            self.end_time.value = d['end_time']
            self.location.value = d.get('location', '')
            self.participants.value = d.get('participants', [])
        except Exception as e:
            self.summary.value = {"error": str(e)}



