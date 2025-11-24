PLACE = 'Tompkins County'
ADMIN_LEVEL = 6
CENTER = (42.4396096, -76.4968760)
CUSTOM_FILTER = (
    '['
    '"highway"~'
    '"motorway|trunk|primary|secondary|tertiary|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|residential"'
    ']'
)
STOPS_TAGS = {
    'highway': 'bus_stop'
}

H = [5, 10, 15, 30, 60]
WALKING_DST = 1000
JAC_DST = 0.75
BDGT_FACTOR = 1
QS_FACTOR = 0.5
REL_TOL = 0.1

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
HEXCOLORS = [
    HEXBLUE,
    HEXYELLOW,
    HEXVERMILLION,
    HEXSKYBLUE,
    HEXORANGE,
    HEXBLUISHGREEN,
    HEXREDDISHPURPUPLE,
]