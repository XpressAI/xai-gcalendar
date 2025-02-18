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
    - `impersonate_user_account` (str, optional): The email address of the user to impersonate. If provided,
      the service account credentials will delegate access to this user account.

    ## Outputs
    - Adds `service` (the authenticated Google Calendar service object) to the context for further use by other components.
    """
    service_account_json: InArg[str]
    impersonate_user_account: InArg[str]

    def execute(self, ctx) -> None:
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        SERVICE_ACCOUNT_FILE = self.service_account_json.value
        if SERVICE_ACCOUNT_FILE and os.path.exists(SERVICE_ACCOUNT_FILE):
            print(f"Using provided service account JSON: {SERVICE_ACCOUNT_FILE}")
            credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        else:
            encoded_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS")
            if not encoded_json:
                raise ValueError("Neither a valid file path nor GOOGLE_SERVICE_ACCOUNT_CREDENTIALS environment variable was found.")
            
            gcal_creds = json.loads(base64.b64decode(encoded_json).decode())
            credentials = service_account.Credentials.from_service_account_info(gcal_creds, scopes=SCOPES)
            
        if self.impersonate_user_account.value is not None:
            delegated_credentials = credentials.with_subject(self.impersonate_user_account.value)
            service = build('calendar', 'v3', credentials=delegated_credentials)
        else:
            service = build('calendar', 'v3', credentials=credentials)
            
        ctx.update({'service': service})
        print("Google Calendar authentication completed successfully.")


@xai_component()
class GetGoogleCalendarEvents(Component):
    """
    A component that fetches and structures events from a specified Google Calendar within a given time range.

    ## Inputs
    - `calendar_id` (str): The ID of the Google Calendar from which to retrieve events.
    - `start_time` (str): The start time (in ISO format) for the search range.
    - `end_time` (str): The end time (in ISO format) for the search range.

    ## Outputs
    - `events` (dict): A dictionary containing a list of events under the key "events",
      or a message if no events are found.
    """
    calendar_id: InArg[str]
    start_time: InCompArg[str]
    end_time: InCompArg[str]
    events: OutArg[dict]

    def execute(self, ctx) -> None:

        service = ctx["service"]
        events_result = service.events().list(
            calendarId=self.calendar_id.value,
            timeMin=self.start_time.value,
            timeMax=self.end_time.value,
            singleEvents=True
        ).execute()

        events = events_result.get('items', [])
        if not events:
            self.events.value = {"message": "No events found for the specified time range."}
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
    - `summary` (str): The event summary or title (compulsory).
    - `description` (str, optional): A description for the event.
    - `start_time` (str): The start time of the event in ISO format (compulsory).
    - `end_time` (str): The end time of the event in ISO format (compulsory).
    - `location` (str, optional): The location of the event.
    - `participants` (list, optional): A list of participant email addresses.
    - `calendar_id` (str): The ID of the Google Calendar where the event will be created.

    ## Outputs
    - `event_id` (str): The ID of the created event.
    """
    summary: InCompArg[str]
    description: InArg[str]
    start_time: InCompArg[str]
    end_time: InCompArg[str]
    location: InArg[str]
    participants: InArg[list]
    calendar_id: InArg[str]
    event_id: OutArg[str]

    def execute(self, ctx) -> None:
    
        CALENDAR_ID = self.calendar_id.value
        service = ctx["service"]

        event = {
            'summary': self.summary.value,
            'start': {'dateTime': self.start_time.value, 'timeZone': 'UTC'},
            'end': {'dateTime': self.end_time.value, 'timeZone': 'UTC'}
        }

        if self.description.value:
            event['description'] = self.description.value

        if self.location.value:
            event['location'] = self.location.value

        if self.participants.value:
            attendees = [{'email': participant} for participant in self.participants.value]
            event['attendees'] = attendees

        created_event = service.events().insert(calendarId=CALENDAR_ID, body=event, sendUpdates='all').execute()
        self.event_id.value = created_event['id']



@xai_component()
class ModifyGoogleCalendarEvent(Component):
    """
    A component that modifies an existing event in Google Calendar.

    This component updates only the fields for which a new value is provided.
    If no new value is provided for a field, the original event's value remains unchanged.

    ## Inputs
    - `event_id` (str): The ID of the event to be modified.
    - `new_summary` (str, optional): The new summary or title for the event.
    - `new_description` (str, optional): The new description for the event.
    - `new_start_time` (str, optional): The new start time in ISO format.
    - `new_end_time` (str, optional): The new end time in ISO format.
    - `new_location` (str, optional): The new location for the event.
    - `new_participants` (list, optional): A new list of participant email addresses.
    - `calendar_id` (str, optional): The ID of the calendar where the event resides. Defaults to "primary" if not provided.

    ## Outputs
    - `modified_event_id` (str): The ID of the modified event.
    """
    event_id: InArg[str]
    new_summary: InArg[str]
    new_description: InArg[str]
    new_start_time: InArg[str]
    new_end_time: InArg[str]
    new_location: InArg[str]
    new_participants: InArg[list]
    calendar_id: InArg[str]
    modified_event_id: OutArg[str]

    def execute(self, ctx) -> None:
        
        service = ctx["service"]
        cal_id = self.calendar_id.value if self.calendar_id.value else "primary"
        event = service.events().get(calendarId=cal_id, eventId=self.event_id.value).execute()

        # Update only if a new value is provided
        if self.new_summary.value:
            event['summary'] = self.new_summary.value

        if self.new_description.value:
            event['description'] = self.new_description.value

        if self.new_start_time.value:
            event['start'] = {'dateTime': self.new_start_time.value, 'timeZone': 'UTC'}

        if self.new_end_time.value:
            event['end'] = {'dateTime': self.new_end_time.value, 'timeZone': 'UTC'}

        if self.new_location.value:
            event['location'] = self.new_location.value

        if self.new_participants.value:
            event['attendees'] = [{'email': participant} for participant in self.new_participants.value]

        updated_event = service.events().update(calendarId=cal_id, eventId=self.event_id.value, body=event, sendUpdates='all').execute()
        self.modified_event_id.value = updated_event['id']




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
    calendar_id: InArg[str]
    deletion_status: OutArg[str]

    def execute(self, ctx) -> None:

        service = ctx["service"]
        cal_id = self.calendar_id.value if self.calendar_id.value else "primary"

        service.events().delete(calendarId=cal_id, eventId=self.event_id.value).execute()
        self.deletion_status.value = {"status": "Event deleted successfully."}


@xai_component()
class ListGoogleCalendars(Component):
    """
    A component that retrieves a list of all Google Calendars accessible by the authenticated user.

    ## Outputs
    - `calendars` (dict): A dictionary containing the list of calendars under the key "items".

    ## Requirements
    - An authenticated Google Calendar service must be present in the context.
    """
    calendars: OutArg[dict]

    def execute(self, ctx) -> None:

        service = ctx["service"]
        calendar_list = service.calendarList().list().execute()
        self.calendars.value = calendar_list



@xai_component()
class GetCalendarDetails(Component):
    """
    A component that retrieves details for a specified Google Calendar.

    ## Inputs
    - `calendar_id` (str): The ID of the calendar to retrieve details for.

    ## Outputs
    - `details` (dict): A dictionary containing the calendar details.

    ## Requirements
    - An authenticated Google Calendar service must be present in the context.
    """
    calendar_id: InCompArg[str]
    details: OutArg[dict]

    def execute(self, ctx) -> None:

        service = ctx["service"]
        calendar_details = service.calendars().get(calendarId=self.calendar_id.value).execute()
        self.details.value = calendar_details



@xai_component()
class QuickAddGoogleCalendarEvent(Component):
    """
    A component that quickly adds an event to a Google Calendar using a natural language text description.

    This component leverages the Google Calendar API's quickAdd method to parse a natural language description
    and automatically schedule an event. If the text does not specify a start time or duration, the event
    will be created to start immediately (i.e., "now") and will use the default duration set in your calendar
    (typically one hour, depending on your calendar's settings).

    ## Inputs
    - `query` (str): A natural language description of the event (e.g., "Lunch with John tomorrow at noon for 2 hours").
    - `calendar_id` (str): The ID of the calendar where the event will be added.

    ## Outputs
    - `event_id` (str): The ID of the created event.

    ## Requirements
    - An authenticated Google Calendar service must be present in the context.
    """
    query: InCompArg[str]
    calendar_id: InArg[str]
    event_id: OutArg[str]

    def execute(self, ctx) -> None:

        service = ctx["service"]
        result = service.events().quickAdd(calendarId=self.calendar_id.value, text=self.query.value).execute()
        self.event_id.value = result.get('id', '')




@xai_component()
class SearchGoogleCalendarEvents(Component):
    """
    A component that searches for events in a Google Calendar based on a query and time range.

    ## Inputs
    - `query` (str): The search query string.
    - `time_min` (str): The start time (in ISO format) for the search range.
    - `time_max` (str): The end time (in ISO format) for the search range.
    - `calendar_id` (str): The ID of the calendar to search in.

    ## Outputs
    - `events` (dict): A dictionary containing the list of matching events.

    ## Requirements
    - An authenticated Google Calendar service must be present in the context.
    """
    query: InCompArg[str]
    time_min: InCompArg[str]
    time_max: InCompArg[str]
    calendar_id: InArg[str]
    events: OutArg[dict]

    def execute(self, ctx) -> None:

        service = ctx["service"]
        result = service.events().list(
            calendarId=self.calendar_id.value,
            q=self.query.value,
            timeMin=self.time_min.value,
            timeMax=self.time_max.value,
            singleEvents=True
        ).execute()
        self.events.value = result



@xai_component()
class MoveGoogleCalendarEvent(Component):
    """
    A component that moves an event from one Google Calendar to another.

    ## Inputs
    - `event_id` (str): The ID of the event to move.
    - `source_calendar_id` (str): The ID of the calendar where the event currently resides.
    - `destination_calendar_id` (str): The ID of the calendar to which the event should be moved.

    ## Outputs
    - `moved_event` (dict): A dictionary containing details of the moved event.

    ## Requirements
    - An authenticated Google Calendar service must be present in the context.
    """
    event_id: InCompArg[str]
    source_calendar_id: InCompArg[str]
    destination_calendar_id: InCompArg[str]
    moved_event: OutArg[dict]

    def execute(self, ctx) -> None:

        service = ctx["service"]
        result = service.events().move(
            calendarId=self.source_calendar_id.value,
            eventId=self.event_id.value,
            destination=self.destination_calendar_id.value
        ).execute()
        self.moved_event.value = result



@xai_component()
class UpdateGoogleCalendarEventAttendees(Component):
    """
    A component that updates the attendee list of a specified Google Calendar event.

    ## Inputs
    - `event_id` (str): The ID of the event to update.
    - `attendees` (list): A list of attendee email addresses to set for the event.
    - `calendar_id` (str, optional): The ID of the calendar where the event resides. Defaults to "primary" if not provided.

    ## Outputs
    - `updated_event_id` (str): The ID of the updated event.

    ## Requirements
    - An authenticated Google Calendar service must be present in the context.
    """
    event_id: InCompArg[str]
    attendees: InCompArg[list]
    calendar_id: InArg[str]
    updated_event_id: OutArg[str]

    def execute(self, ctx) -> None:

        service = ctx["service"]
        cal_id = self.calendar_id.value if self.calendar_id.value else "primary"
        event = service.events().get(calendarId=cal_id, eventId=self.event_id.value).execute()
        # Update the attendees list
        event['attendees'] = [{'email': email} for email in self.attendees.value]
        updated_event = service.events().update(calendarId=cal_id, eventId=self.event_id.value, body=event).execute()
        self.updated_event_id.value = updated_event.get('id', '')


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

        data = json.loads(self.json.value)
        self.summary.value = data['summary']
        self.start_time.value = data['start_time']
        self.end_time.value = data['end_time']
        self.location.value = data.get('location', '')
        self.participants.value = data.get('participants', [])

