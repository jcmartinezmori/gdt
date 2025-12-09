import numpy as np

# --- QUERY PARAMETERS --- #
ADMIN_LEVEL = 6
CENTER = (42.49036732282236, -76.46329087470093)
CUSTOM_FILTER = (
    '['
    '"highway"~'
    '"motorway|trunk|primary|secondary|tertiary|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|residential"'
    ']'
)
PLACE = 'Tompkins County'
RETAIN_ALL = False
SIMPLIFY = False
GTFS = 'tcat-ny-us'
# TAGS = {'amenity': ['bar', 'biergarten', 'cafe', 'fast_food', 'food_court', 'ice_cream', 'pub', 'restaurant']}
TAGS = {'amenity': True, 'shop': True, 'office': True}


# --- MODEL PARAMETERS --- #
COST_FACTOR = 1
DETOUR_FACTOR = 2
H = [5, 10, 15, 20, 30, 45, 60]
IC_FACTOR = 1.0
OVERLAP_THRESHOLD = 1/4
NO_RANDOM_LINES = 225
SERVICE_COVER_FACTOR = 3
TRANSFER_MIN_H = 15
SIZE_FACTOR = 1
WALK_COVER_FACTOR = 2
WALK_DIST = 500
WALK_TRIP_FACTOR = 4

# --- SOLVER PARAMETERS --- #
MIP_FOCUS = 1
TIME_LIMIT = 60 * 60
REL_TOL = 0.1

# --- PLOTTING PARAMETERS --- #
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
