import numpy as np

# --- QUERY PARAMETERS --- #
ADMIN_LEVEL = 6
CENTER = (39.746430, -105.002494)
CUSTOM_FILTER = (
    '['
    '"highway"~'
    '"motorway|trunk|primary|secondary|tertiary|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|residential|living_street"'
    ']'
)
PLACE = 'DENVER'
RETAIN_ALL = False
SIMPLIFY = True
CONSOLIDATE_TOL = 25
GTFS = 'rtd-co-us'
TAGS = {'amenity': True, 'shop': True, 'office': True, 'building:levels': True}
RAIL_DIRS = [
    './data/{0}/rail/direct-light/'.format(GTFS),
    './data/{0}/rail/direct-commuter/'.format(GTFS),
    './data/{0}/rail/purchased-commuter/'.format(GTFS),
]


# --- MODEL PARAMETERS --- #
BUDGET_FACTOR = 1.0
RIDERSHIP_FACTOR = 0.6
DETOUR_FACTOR = 2
COVERAGE_H = 60
H = [10, 15, 20, 30, 45, 60, 120]
WALK_COVER_FACTOR = 2
WALK_DIST = 400
WALK_TRIP_FACTOR = 4
RHO_CUTOFF = 4
W_CUTOFF = 1
T_CUTOFF = 1
SPEED = {
    'sidewalk': 5,
    'street': 40,
    'highway': 100
}
TIME_PER_STOP = 1/4
OUTLIER_STOP_CUTOFF = 1
SERVICE_START = '15:00:00'
SERVICE_END = '20:00:00'
FORBIDDEN_L = [
    'FREE'
]


# --- SOLVER PARAMETERS --- #
MIP_FOCUS = 0
TIME_LIMIT = 60 * 60
THREADS = 32
REL_TOL = 0.1

# --- PLOTTING PARAMETERS --- #
OPACITY = 1/6
ZOOM = 11
HEXBLACK = "#000000"
HEXORANGE = "#E69F00"
HEXSKYBLUE = "#56B4E9"
HEXBLUISHGREEN = "#009E73"
HEXYELLOW = "#F0E442"
HEXBLUE = "#0072B2"
HEXVERMILLION = "#D55E00"
HEXREDDISHPURPUPLE = "#CC79A7"
HEXGRAY = "#999999"
HEXCOLORS = [
    HEXBLUE,
    HEXYELLOW,
    HEXVERMILLION,
    HEXSKYBLUE,
    HEXORANGE,
    HEXBLUISHGREEN,
    HEXREDDISHPURPUPLE,
    HEXGRAY
]
