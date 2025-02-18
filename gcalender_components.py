from xai_components.base import InArg, OutArg, Component, xai_component, InCompArg
from googleapiclient.discovery import build
from google.oauth2 import service_account
import base64
import json
import os

@xai_component()
class AuthenticateGoogleCalendar(Component):
    """
    A component that handles authentication for the Google Calendar API.

    ## Inputs
    - `service_account_json` (str): Path to the service account JSON file. If not provided or invalid,
      the component will attempt to read credentials from the `GOOGLE_SERVICE_ACCOUNT_CREDENTIALS` environment variable.

    ## Outputs
    - Adds `service` (the authenticated Google Calendar service object) to the context for further use by other components.
    """
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
    """
    A component that fetches and structures events from a specified Google Calendar for a given day.

    ## Inputs
    - `calendar_id` (str): The ID of the Google Calendar.
    - `date` (str): The date (in YYYY-MM-DD format) for which to retrieve events.

    ## Outputs
    - `events` (dict): A dictionary containing a list of events under the key "events",
      or a message if no events are found.
    """
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
    """
    A component that creates a new event in a Google Calendar.

    ## Inputs
    - `calendar_id` (str): The ID of the Google Calendar where the event will be created.
    - `summary` (str): The event summary or title (compulsory).
    - `start_time` (str): The start time of the event in ISO format (compulsory).
    - `end_time` (str): The end time of the event in ISO format (compulsory).
    - `location` (str, optional): The location of the event.
    - `participants` (list, optional): A list of participant email addresses.

    ## Outputs
    - `event_id` (str): The ID of the created event.
    """
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
    """
    A component that modifies an existing event in Google Calendar.

    ## Inputs
    - `event_id` (str): The ID of the event to be modified.
    - `new_summary` (str): The new summary or title for the event.
    - `new_description` (str): The new description for the event.
    - `calendar_id` (str, optional): The ID of the calendar where the event resides. Defaults to "primary" if not provided.

    ## Outputs
    - `modified_event_id` (str): The ID of the modified event.
    """
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
    """
    A component that deletes an event from a Google Calendar.

    ## Inputs
    - `event_id` (str): The ID of the event to be deleted.
    - `calendar_id` (str, optional): The ID of the calendar from which the event will be deleted. Defaults to "primary" if not provided.

    ## Outputs
    - `deletion_status` (str): A status message indicating whether the event was successfully deleted or an error occurred.
    """
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
    """
    A component that extracts event details from a JSON string.

    ## Inputs
    - `json` (str): A JSON string containing event details.

    ## Outputs
    - `summary` (str): The event summary or title.
    - `start_time` (str): The event start time.
    - `end_time` (str): The event end time.
    - `location` (str): The event location.
    - `participants` (list): A list of participant email addresses.
    """
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
