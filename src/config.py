import numpy as np

PLACE = 'Tompkins County'
ADMIN_LEVEL = 6
CENTER = (42.49036732282236, -76.46329087470093)
CUSTOM_FILTER = (
    '['
    '"highway"~'
    '"motorway|trunk|primary|secondary|tertiary|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|residential"'
    ']'
)
STOPS_TAGS = {
    'public_transport': 'platform'
}


H = [5, 10, 15, 30, 45, 60]
TRANSFER_H = 10
NO_RANDOM_LINES = 250
WALK_DST = 500
WALK_COVER_FACTOR = 2
SERVICE_COVER_FACTOR = 3
WALK_TRIP_FACTOR = 4
JAC_DST = 0.0

# --- SOLVER PARAMETERS --- #
MIP_FOCUS = 1
TIME_LIMIT = 120
REL_TOL = 0.1
BDGT_FACTOR = 1
LS_FACTOR = 0.0

OPACITY = 1/6
ZOOM = 12
HEXBLACK = "#000000"
HEXORANGE = "#E69F00"
HEXSKYBLUE = "#56B4E9"
HEXBLUISHGREEN = "#009E73"
HEXYELLOW = "#F0E442"
HEXBLUE = "#0072B2"
HEXVERMILLION = "#D55E00"
HEXREDDISHPURPUPLE = "#CC79A7"
HEXCOLORS = [
    HEXBLUE,
    HEXYELLOW,
    HEXVERMILLION,
    HEXSKYBLUE,
    HEXORANGE,
    HEXBLUISHGREEN,
    HEXREDDISHPURPUPLE,
]

C_FREQ = {
    'TCAT 10 Cornell - Commons Shuttle': 10,
    'TCAT 11 Outbound College Circle Apts via Southside and IC': 60,
    'TCAT 11 Inbound Downtown via Southside': None,
    'TCAT 13 Outbound -> Ithaca Mall': 45,
    'TCAT 13 Outbound -> TCAT Garage': None,
    'TCAT 13 Inbound -> Downtown': None,
    'TCAT 13 Outbound -> Stewart Park': None,
    'TCAT 14 Outbound -> Hospital via West Hill': 30,
    'TCAT 14 Outbound -> Hospital Express': None,
    'TCAT 14 Inbound -> Downtown Express': None,
    'TCAT 14 Inbound -> Downtown via West Hill': None,
    'TCAT 15 Outbound Southside Shopper': 60,
    'TCAT 15 Outbound Shopper Express': None,
    'TCAT 15 Inbound Southside Shopper': None,
    'TCAT 17 Inbound -> Vet School via Downtown': None,
    'TCAT 17 Inbound -> Downtown': None,
    'TCAT 30 Outbound Commons - Ithaca Mall': 30,
    'TCAT 30 Inbound Ithaca Mall - Commons': None,
    'TCAT 30 (Weekend) Outbound Commons - Ithaca Mall': None,
    'TCAT 30 (Weekend) Inbound Ithaca Mall - Commons': None,
    'TCAT 31 Winston Crt - Etna - Cornell (Normal Routing)': 60,
    'TCAT 31 Winston Crt - Guthrie - Cornell (Guthrie Loop)': 60,
    'TCAT 32 Outbound: Commons - Cornell - Airport': 60,
    'TCAT 32 Inbound: Airport - Cornell - Commons': None,
    'TCAT 32 (Weekend) Outbound Downtown - Cornell - Village Solars': None,
    'TCAT 32 (Weekend) Inbound Village Solars - Airport - Downtown': None,
    'TCAT 37 Inbound Lansing Town Hall - Springbrook @ Farrell': 60,
    'TCAT 37 Outbound Lansing Town Hall - Springbrook @ Farrell': None,
    'TCAT 51 Eastern Heights - Cornell - Commons': 60,
    'TCAT 77 Northbound to Warren Rd and Lansing': None,
    'TCAT 77 Eastbound to Winston Court, Hanshaw, Etna': None,
    'TCAT 81 Cornell Campus Service': 30,
    'TCAT 82 ornell Campus Service / East Hill Office Building': 60,
    'TCAT 83 Cornell Campus Service': None,
    'TCAT 90 Outbound North Campus via Feeney Way': 15,
    'TCAT 90 Inbound Downtown via West Campus': None,
}
