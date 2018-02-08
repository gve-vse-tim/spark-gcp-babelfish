#!/usr/bin/env python3

# Python core code
import requests
import argparse
import json
import sys
import time
import datetime

# 3rd party code
from oauth2client.client import GoogleCredentials
from google.cloud import translate

# My custom code
import spark.urls
import gcp.urls

# Security provisions
from config import BOT_TOKEN, BOT_EMAIL

# Methods for Babelfish Bot
def make_header(authn):
    return { 'Authorization' : 'Bearer ' + authn }

def check_status_code(http_response):
    """
    check_status_code(requests.Response object): 
       Simple method to make sure the HTTP Server response had a status code in the 200s

    """

    if http_response.status_code // 100 != 2:
        raise Exception('Status code not "OK": {0}\n{1}'.format(http_response.status_code,http_response.text))

def create_room(room_title, authn=BOT_TOKEN):
    """
    create_room(room_title, authn): create a room with provided title and
    return its ID.  Optionally provide an authentication token if different
    from the default.
    """

    # Build the action item request to be sent to Spark to create room
    request_json = { 'title' : room_title }

    # Generate HTTP headers
    request_header = make_header( authn )

    # Attempt to create the room
    http_response = requests.post(spark.urls.rooms, headers=request_header,
                                  json=request_json)

    # Convert response to JSON
    response = json.loads(http_response.text)
 
    # Check status code
    check_status_code(http_response)

    room_id = response['id']

    # Need to return room ID for software to work
    return room_id

def get_room_id_by_title(title, authn=BOT_TOKEN):
    """
    get_room_id_by_title(title, authn): Locate the first room identified by the 
    provided title (remember, titles are not unique constraints!) and return
    the unique roomId
    """

    # Generate HTTP headers
    request_header = make_header(authn)

    # Fetch list of rooms
    http_response = requests.get(spark.urls.rooms, headers=request_header)

    # Convert response to JSON
    response = json.loads(http_response.text)

    # Check status code
    check_status_code(http_response)

    # Loop over returned items and locate matching room
    for room in response['items']:
        if room['title'] == title:
            return room['id']

    # If I get here, it was not found.  Error
    raise Exception('Could not find room title {0}'.format(title))


def delete_room(id=None, title=None, authn=BOT_TOKEN):
    """
    delete_room(id, title, authn) - delete a room based on its unique roomId
    value or its title - since the title search is based on get_room_id_by_title
    to understand how it deals with duplicates
    """

    if id == None and title == None:
        raise Exception('Must specify room ID or title')

    # Generate HTTP headers
    request_header = make_header(authn)

    # If a title was provided, convert it to an ID
    if title != None:
        room_id = get_room_id_by_title(title)
    else:
        room_id = id

    room_url = '{0}/{1}'.format(spark.urls.rooms, room_id)

    # A good (non-REST) programmer would check first if the room existed
    # This programmer will simply let Spark error out and process the error
    http_response = requests.delete(room_url, headers=request_header)

    # Check status code
    check_status_code(http_response)


def check_messages_by_room_id(id, authn=BOT_TOKEN):
    """
    check_messages_by_room_id(id, authn): given the unique roomId, fetch all
    the messages in the room.
    """

    # Generate HTTP headers
    request_header = make_header(authn)

    # Build the action item request to be sent to Spark to create room
    request_json = { 'roomId' : id }

    http_response = requests.get(spark.urls.messages, headers=request_header,
                                  params=request_json)

    # Convert response to JSON
    response = json.loads(http_response.text)

    # Check status code
    check_status_code(http_response)

    return response['items']


def parse_message_for_command(entry):
    """
    parse_message_for_command(entry) - look at the given message and determine
    if it was a bot command.  If so, return the following information:
        action, personId, personEmail, language

       - action      : the string to return so that the calling method know how to 
                       proceed. such as 'add' or 'delete'
       - personId    : the unique string identifying a user
       - personEmail : the email address associated with the message
       - language    : Google Translate abbreviation for translated language, i.e.
                       to which language does the user what the message translated

    """

    # Here - we need to accept an GCP language argument ('en','de','es' )
    if entry['text'].startswith('/translate'):
        #  Default to German 'de'
        if len( entry['text'] ) < 12:
            user_lang = 'de'
        else: 
            user_lang = entry['text'][11:]

        return 'add', entry['personId'], entry['personEmail'], user_lang

    if entry['text'] == '/stop':
        return 'delete', entry['personId'], entry['personEmail'], None

    return None, None, None, None

    
def get_xlate_room_id(title, user_email, authn=BOT_TOKEN):
    """
    get_xlate_room_id(title, user_meail, authn): return the unique roomId of the
    Spark room into which the translated messages will be written. 

    If the room exists, the get_room_id_by_title method is used to locate the 
    room_id.

    If the room does not yet exists, create it and return the provide roomId from
    the create_room method

    """

    # Generate HTTP headers
    request_header = make_header(authn)

    # Define translation room name standard here
    room_name = '{0}-{1}'.format( title, user_email )

    # Does the room exist already?
    try:
        room_id = get_room_id_by_title( room_name )
    except:
        room_id = create_room( room_name )

    return room_id


def send_message_by_room_id(room_id, message, authn=BOT_TOKEN):
    """
    send_message_by_room_id(room_id, message, authn): Yes, given the unique roomId
    and the text message (Markdown currently not supported), sent it to the room.
    
    Method is generic enough to send to any room to which the bot has access, not
    just the xlate rooms.
    """

    # Generate HTTP headers
    request_header = make_header(authn)

    # Build the action item request to be sent to Spark to create room
    request_json = { 'roomId' : room_id, 'text' : message }

    # Attempt to send the message
    http_response = requests.post(spark.urls.messages, headers=request_header,
                                  json=request_json)

    # Convert response to JSON
    response = json.loads(http_response.text)

    # Check status code
    check_status_code(http_response)

    return response['id']


def poll_messages_by_room_id(source_room_id, latest_message_id, authn=BOT_TOKEN):
    """
    poll_messages_by_room_id(source_room_id, latest_message_id, authn)
       - for a given roomId (the 'source' is the primary room in which all participants
         are talking), fetch all the messages and return those *newer* than 
         latest_message_id.
       - BIG ASSUMPTION - messages are return in reverse chronological order and
         the same order every time.

         return values are the message list and the unique string id for the latest message

    """

    # Get all messages for the room (newest ones come first)
    current_messages = check_messages_by_room_id(source_room_id)
    current_messages.reverse()

    new_messages = []

    if latest_message_id == None:
        disabled = False
    else:
        disabled = True

    # Loop over all messages and translate to English (or CLI specified)
    for message in current_messages:
        # A little logic to read all messages on first loop
        if disabled == True:
            # Skip messages until we reach the last processed message
            if message['id'] == latest_message_id:
                disabled = False
            continue

        new_messages.append( message )

    latest_message_id = current_messages[-1]['id']
    return new_messages, latest_message_id


def simulation_step(source_room_id, count, args):
    """
    simulation_step(source_room_id, loop_count, script_cli_args)
      - pay no attention to the man behind the curtain.
    """

    if count == 0:
        send_message_by_room_id( source_room_id, '/translate de' )
        send_message_by_room_id( source_room_id, "Hi Bob! How's that estimate going?" )
        send_message_by_room_id( source_room_id, 'Como esta? Habla ingles?' )
    if count == 1:
        send_message_by_room_id( source_room_id, 'That is fantastic!' )
        send_message_by_room_id( source_room_id, 'Parlez vous francais?' )
    if count == 3:
        send_message_by_room_id( source_room_id, '/stop' )
        send_message_by_room_id( source_room_id, 'My German is getting rusty' )
        send_message_by_room_id( source_room_id, 'Where is the kaboom?' )
    if count == 5:
        send_message_by_room_id( source_room_id, '/translate ru' )
        send_message_by_room_id( source_room_id, 'Eppure si muove' )
        send_message_by_room_id( source_room_id, 'Como se dice butter' )


if __name__ == '__main__':
    """
    This is where the script begins taking action
    """

    # Support the use of command line arguments
    parser = argparse.ArgumentParser()

    parser.add_argument('-t', '--title', help='Specify room title')
    parser.add_argument('-i', '--id', help='Specify room ID')
    parser.add_argument('-n', '--native', help='Specify native/target language')

    parser.add_argument('-l', '--list', help='Get room ID', action='store_true')
    parser.add_argument('-a', '--add', help='Create room', action='store_true')
    parser.add_argument('-d', '--delete', help='Delete room', action='store_true')

    parser.add_argument('-m', '--messages', help='Get messages', action='store_true')
    parser.add_argument('-f', '--fish', help='Translate Loop', action='store_true')

    args = parser.parse_args()

    # Check to see if user invoked the -l option
    if args.list:
        if args.title != None:
            print( get_room_id_by_title(args.title) )
            sys.exit(0)

        sys.exit(0)

    # After this point, one of title or ID MUST be specified for the remaining
    # arguments/actions
    if not args.title and not args.id:
        raise Exception('Need a room title or ID')

    # Fetch all the messages from a given room - prints JSON DUMPS
    if args.messages:
        if args.title != None:
            room_id = get_room_id_by_title(args.title)

            messages = check_messages_by_room_id(room_id)
            messages.reverse()

            print( json.dumps(messages, indent=4) )

            sys.exit(0)

    # Delete the room specified by the roomID (priority) or title
    if args.delete:
        if args.id:
            room_id = args.id
        else:
            room_id = get_room_id_by_title(args.title)

        delete_room(id = room_id)

        sys.exit(0)   

    # Add a new room to Spark
    if args.add:
        if not args.title:
            raise Exception('Need a room title for this action')

        new_id = create_room( args.title )

        sys.exit(0)

    # Main BabelFish operation block here
    if args.fish:
        credentials = GoogleCredentials.get_application_default()
        translate_client = translate.Client()

        if args.id:
            source_room_id = args.id
        else:
            source_room_id = get_room_id_by_title(args.title)

        # Set up the simulation (assumes clean demo room created, empty, and 
        # no xlate rooms created

        simulation_step(source_room_id, 0, args)
        time.sleep(5)

        # Did not want to mess with webhooks this iteration, so I developed a
        # crude, basic polling mechanism

        latest_message_id = None
        xlate_rooms = { }
        loop_counter = 0

        while loop_counter < 10:

            # Poll for new messages from the room
            latest_messages, latest_message_id = poll_messages_by_room_id(source_room_id, latest_message_id)

            # Process the latest messages
            for message in latest_messages:

                # At first eligible message - is it a command?
                command, user_id, user_email, user_lang = parse_message_for_command( message )

                # Handle command
                if command != None:
                    xlate_room_id = get_xlate_room_id( args.title, user_email )

                    if command == 'add':
                        xlate_rooms[xlate_room_id] = { 'user_id' : user_id,
                                                       'user_lang' : user_lang }

                    if command == 'delete':
                        if xlate_room_id in xlate_rooms:
                            del xlate_rooms[xlate_room_id]

                    # Since message was a command, skip to next message
                    continue

                # This message is an actual message - let's translate it - unique to each person
                for targets in xlate_rooms.keys():
                    gcp_result = translate_client.translate( message['text'], 
                                                             target_language=xlate_rooms[targets]['user_lang'] )

                    # I'm a bad boy Abbott.  I didn't error check Google.
                    # But they don't make mistakes, right? I know I don't. :)
                    send_message_by_room_id(targets, gcp_result['translatedText'])


            # Set up for the next polling iteration, wait some time to see the effects
            loop_counter = loop_counter + 1
            time.sleep(10)

            # Deploy the next set of demo messages, wait
            simulation_step(source_room_id, loop_counter, args)
            time.sleep(10)

            # End of polling while loop!
        # End of BabelFish actions
    #End of __main__

### My only friend... that's right: the end

