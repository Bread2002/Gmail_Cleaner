from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from googleapiclient import errors
from dotenv import load_dotenv
import os
import time
import random

# Load environment variables
load_dotenv()

required_env_vars = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_PROJECT_ID"]
missing_env_vars = [name for name in required_env_vars if not os.getenv(name)]
if missing_env_vars:
    missing_list = ", ".join(missing_env_vars)
    raise RuntimeError(f"Missing required environment variables: {missing_list}")

GOOGLE_AUTH_CONFIG = {
    "installed": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "project_id": os.getenv("GOOGLE_PROJECT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uris": ["http://localhost"],
    }
}

# Define OAuth 2.0 scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.settings.basic",
    "https://www.googleapis.com/auth/gmail.settings.sharing",
]

# Function to stop a specific sender from sending emails using Gmail filters
def stop_sender(sender):
    try:
        # Create a filter to delete emails from the sender
        filter_request = {
            'criteria': {
                'from': sender
            },
            'action': {
                'removeLabelIds': ['INBOX'],
                'addLabelIds': ['TRASH'],
                'delete': True
            }
        }

        # Execute filter request
        service.users().settings().filters().create(userId='me', body=filter_request).execute()
        print(f"Emails from sender {sender} will be deleted from now on.")
    except errors.HttpError as error:
        print(f"An error occurred: {error}")

# Function that returns whether the specified sender has sent at least 20 consecutive unread emails
def has_continuous_unread(sender, sender_messages):
    if not sender_messages or len(sender_messages) < 20:
        return False

    # Limit the number of messages to process for performance
    max_check = 100
    if len(sender_messages) > max_check:
        sender_messages = sender_messages[:max_check]

    # Count of consecutive unread emails
    consecutive_unread = 0

    # Helper to execute requests with exponential backoff on 429/5xx
    def safe_execute(callable_request, max_retries=5, initial_delay=1.0):
        delay = initial_delay
        for attempt in range(max_retries):
            try:
                return callable_request()
            except errors.HttpError as e:
                status = getattr(e.resp, 'status', None)
                if status in (429, 500, 503):
                    sleep_time = delay + random.random() * 0.5
                    time.sleep(sleep_time)
                    delay *= 2
                    continue
                raise
        # Last attempt
        return callable_request()

    # Iterate sequentially (avoid concurrent requests) and check labels
    for message in sender_messages:
        try:
            msg = safe_execute(lambda: service.users().messages().get(userId='me', id=message['id'], format='metadata').execute())
        except Exception as e:
            print(f"Error processing message: {e}")
            continue

        if 'labelIds' in msg and 'UNREAD' in msg['labelIds']:
            consecutive_unread += 1
        else:
            consecutive_unread = 0

        if consecutive_unread >= 20:
            return True

    return False

if __name__ == "__main__":
    # Set up OAuth 2.0 credentials using values from .env
    flow = InstalledAppFlow.from_client_config(GOOGLE_AUTH_CONFIG, scopes=SCOPES)
    creds = flow.run_local_server()

    # Connect to Gmail API
    service = build('gmail', 'v1', credentials=creds)

    # Retrieve all unread emails
    unread_results = service.users().messages().list(userId='me', q='is:unread').execute()
    unread_messages = unread_results.get('messages', [])

    # Initialize lists for senders to be deleted
    senders_to_delete = []

    # Initialize counter for number of senders found
    num_senders_found = 0

    # Iterate through unread emails
    for message in unread_messages:
        message_info = service.users().messages().get(userId='me', id=message['id']).execute()

        # Iterate through the headers to find the element with the name set to "From"
        for header in message_info['payload']['headers']:
            if header['name'] == 'From':
                sender = header['value']
                break  # Stop iterating once the 'From' header is found

        # Find the index of '<' and '>' in the sender value
        start_index = sender.find('<')
        end_index = sender.find('>')

        # Extract the email address
        if start_index != -1 and end_index != -1:
            sender = sender[start_index + 1:end_index]  # Output: noreply@redditmail.com

        # Check if this sender has not been encountered before
        if sender not in senders_to_delete:
            sender_messages = []
            page_token = None
            while True:
                sender_results = service.users().messages().list(userId='me', q=f'from:{sender}', pageToken=page_token).execute()
                sender_messages.extend(sender_results.get('messages', []))
                page_token = sender_results.get('nextPageToken')
                if not page_token:
                    break

            if has_continuous_unread(sender, sender_messages):
                print(f"Sender {sender} has sent at least 20 consecutive unread emails.")
                senders_to_delete.append(sender)
                num_senders_found += 1

        # Check if 10 senders have been found
        if num_senders_found >= 10:
            break

    # Ask for confirmation before deleting emails
    confirm_delete_sender = None
    first_trash = True
    if senders_to_delete:
        for sender in senders_to_delete:
            while True:
                if not confirm_delete_sender:
                    sender_messages = []
                    sender_results = service.users().messages().list(userId='me', q=f'from:{sender}').execute()
                    sender_messages.extend(sender_results.get('messages', []))

                    # Preview the first message from the sender
                    first_message_id = sender_messages[0]['id']
                    first_message_info = service.users().messages().get(userId='me', id=first_message_id).execute()
                    print("--------------------------------------------------------")
                    print(f"Showing a preview of the first message from sender {sender}:")
                    print(first_message_info['snippet'])  # Print the snippet of the message
                    print("--------------------------------------------------------")

                    confirm_delete_sender = input("Do you want to move all emails from this sender to the trash? (y/n): ")
                if confirm_delete_sender.lower() == 'y':
                    sender_messages = []
                    page_token = None
                    while True:
                        sender_results = service.users().messages().list(userId='me', q=f'from:{sender}',
                                                                         pageToken=page_token).execute()
                        sender_messages.extend(sender_results.get('messages', []))
                        page_token = sender_results.get('nextPageToken')
                        if not page_token:
                            break

                    # Split sender_messages into smaller batches
                    message_batches = [sender_messages[i:i + 50] for i in range(0, len(sender_messages), 50)]

                    # Execute each batch separately
                    for batch_messages in message_batches:
                        batch = service.new_batch_http_request()
                        for message in batch_messages:
                            batch.add(service.users().messages().trash(userId='me', id=message['id']))
                        batch.execute()

                    if first_trash:
                        print(f"Attempted to trash all emails from sender {sender}.")
                    else:
                        print(f"Attempted to trash remaining emails from sender {sender}.")

                    # Check if there are more emails from the sender
                    remaining_emails = service.users().messages().list(userId='me', q=f'from:{sender}').execute()
                    if 'messages' in remaining_emails:
                        print("There are still emails in your inbox from this sender. Deleting remaining emails...")
                        first_trash = False
                        continue  # Continue to delete remaining emails
                    else:
                        trashed_emails = []
                        trashed_count = 0
                        page_token = None
                        while True:
                            # Count the number of emails trashed from the sender
                            trashed_emails = service.users().messages().list(userId='me', q=f'from:{sender}',
                                                                             labelIds=['TRASH'],
                                                                             pageToken=page_token).execute()
                            trashed_count += len(trashed_emails.get('messages', []))
                            page_token = trashed_emails.get('nextPageToken')
                            if not page_token:
                                break

                        print(f"Successfully trashed approximately {trashed_count} emails from sender {sender}.")
                        break  # Exit the while loop if no more emails from the sender

                elif confirm_delete_sender.lower() == 'n':
                    break  # Exit the loop if user chooses not to delete emails from this sender

            confirm_delete_sender = None

            # Ask to stop a sender from sending emails, if all emails have been deleted
            confirm_stop_sender = input(f"Do you want to stop receiving emails from sender {sender}? (y/n): ")
            if confirm_stop_sender.lower() == 'y':
                # Stop the sender
                stop_sender(sender)
            elif confirm_stop_sender.lower() == 'n':
                continue  # Continue to the next sender

    # Ask the user if they want to quit or continue cleaning their Gmail
    quit_program = input("Do you want to quit the program? (y/n): ")
    if quit_program.lower() == 'y':
        print("Exiting the program...")
        exit()
    else:
        print("Continuing to clean your Gmail...")
