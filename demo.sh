#!/usr/bin/env bash

DEMO_ROOM=ContestTestRoom
XLT_ROOM=${DEMO_ROOM}-timmil@cisco.com

# Clean up previous work - ignore errors
python babelfish.py -d -t ${XLT_ROOM} 2>/dev/null
python babelfish.py -d -t ${DEMO_ROOM} 2>/dev/null

# Create the room
python babelfish.py -a -t ${DEMO_ROOM}

# Run the simulation
python babelfish.py -f -t ${DEMO_ROOM}

