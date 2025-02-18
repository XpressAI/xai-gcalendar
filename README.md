<p align="center">
  <a href="https://github.com/XpressAI/xircuits/tree/master/xai_components#xircuits-component-library-list">Component Libraries</a> •
  <a href="https://github.com/XpressAI/xircuits/tree/master/project-templates#xircuits-project-templates-list">Project Templates</a>
  <br>
  <a href="https://xircuits.io/">Docs</a> •
  <a href="https://xircuits.io/docs/Installation">Install</a> •
  <a href="https://xircuits.io/docs/category/tutorials">Tutorials</a> •
  <a href="https://xircuits.io/docs/category/developer-guide">Developer Guides</a> •
  <a href="https://github.com/XpressAI/xircuits/blob/master/CONTRIBUTING.md">Contribute</a> •
  <a href="https://www.xpress.ai/blog/">Blog</a> •
  <a href="https://discord.com/invite/vgEg2ZtxCw">Discord</a>
</p>

<p align="center"><i>Xircuits Component Library for Google Calendar! Seamlessly integrate and manage your Google Calendar events and meetings.</i></p>

---

## Xircuits Component Library for Google Calendar

This library integrates Google Calendar functionalities into Xircuits, enabling seamless event management. With components for authentication, event creation, modification, deletion, calendar listing, and more, you can easily build workflows to manage your meetings and schedules.

## Table of Contents

- [Preview](#preview)
- [Prerequisites](#prerequisites)
- [Main Xircuits Components](#main-xircuits-components)
- [Try the Examples](#try-the-examples)
- [Installation](#installation)
- [Authentication](#authentication)

## Preview

### Create Event Example

<img src="https://github.com/user-attachments/assets/53dab733-2c16-4f0e-9120-5cc95a12242d" alt="Create Event Example" />

### Check Event Example

<img src="https://github.com/user-attachments/assets/102c0115-c43d-4942-9bdd-692bf0b4221d" alt="Check Event Example" />

## Prerequisites

Before you begin, ensure you have:

1. Python 3.9+.
2. An active Xircuits setup.
3. A Google Cloud project with the Google Calendar API enabled.
4. Service account credentials (or OAuth credentials if using user impersonation).

## Main Xircuits Components

### AuthenticateGoogleCalendar Component
Authenticates with Google Calendar using a service account JSON file, with an optional user impersonation feature.

<img src="https://github.com/user-attachments/assets/f6fe1646-962e-4ca4-9a05-15b1aced485f" alt="AuthenticateGoogleCalendar" width="200" height="100" />

### GetGoogleCalendarEvents Component
Retrieves events from a specified Google Calendar within a given time range.

<img src="https://github.com/user-attachments/assets/3b0aba09-9a8c-450e-8888-0bc955a53618" alt="GetGoogleCalendarEvents" width="200" height="100" />

### CreateGoogleCalendarEvent Component
Creates a new event in a Google Calendar with detailed inputs for summary, description, start/end times, location, and participants. It sends email notifications to all attendees.

<img src="https://github.com/user-attachments/assets/746ced5a-7465-4c97-a0f7-58b3130d6d16" alt="CreateGoogleCalendarEvent" width="200" height="200" />

### ModifyGoogleCalendarEvent Component
Modifies an existing event by updating only the provided fields (summary, description, start/end times, location, participants) and sends email notifications.

### DeleteGoogleCalendarEvent Component
Deletes an event from a Google Calendar.

### ListGoogleCalendars Component
Lists all Google Calendars accessible by the authenticated user.

### GetCalendarDetails Component
Retrieves detailed information for a specified Google Calendar.

### QuickAddGoogleCalendarEvent Component
Quickly adds an event to a Google Calendar using a meeting title. If no start time or duration is specified, the event starts immediately with a default duration.

### SearchGoogleCalendarEvents Component
Searches for events based on a query and time range.

### MoveGoogleCalendarEvent Component
Moves an event from one calendar to another.

### UpdateGoogleCalendarEventAttendees Component
Updates the attendee list for a specified event.

### ExtractEventFromJsonString Component
Parses a JSON string to extract event details.

## Try the Examples

Two example workflows are provided to help you get started:

### create_event.xircuits
Authenticates with Google Calendar using a service account JSON file and creates a new event with placeholder values. Replace these placeholders with your actual event details.

### check_event.xircuits
Authenticates with Google Calendar and retrieves events from a specified calendar within a given time range. Update the inputs with your own calendar ID, start time, and end time.

## Installation

To install this component library, ensure you have a working [Xircuits setup](https://xircuits.io/docs/main/Installation). You can then install the Google Calendar library via the [component library interface](https://xircuits.io/docs/component-library/installation#installation-using-the-xircuits-library-interface) or the CLI:

```bash
xircuits install gcalendar
```
Alternatively, clone and install it manually:

```bash
# Clone into your Xircuits components directory
git clone https://github.com/XpressAI/xai_gcalendar xai_components/xai_gcalendar
pip install -r xai_components/xai_gcalendar/requirements.txt
```

## Authentication

### Service Account Credentials
- Create a Google Cloud project and enable the Google Calendar API.
- Create a service account in the Google Cloud Console.
- Add this scope to your service account `https://www.googleapis.com/auth/calendar`
- Download the service account JSON file.
- Share your Google Calendar with the service account email if needed.
- Provide the path to the JSON file in the `AuthenticateGoogleCalendar` component.

### User Impersonation (Optional)
If you need to access calendar data on behalf of a user, supply the user's email in the `impersonate_user_account` input of the `AuthenticateGoogleCalendar` component. Please note that you will need to enable Domin-wide Delegation for your service account to be able to use this feature. 

For more details on using Xircuits components and project templates, visit [Xircuits Docs](https://xircuits.io/docs) and join our [Discord Community](https://discord.com/invite/vgEg2ZtxCw).

Happy Building!
