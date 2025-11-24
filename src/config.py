PLACE = 'Tompkins County'
ADMIN_LEVEL = 6
CENTER = (42.430682, -76.503453)
CUSTOM_FILTER = (
    '['
    '"highway"~'
    '"motorway|trunk|primary|secondary|tertiary|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link|residential"'
    ']'
)
STOPS_TAGS = {
    'public_transport': 'platform'
}

H = [5, 10, 15, 30, 60]
WALKING_DST = 500
COVER_DST = WALKING_DST
COVER_DST_FACTOR = 3
FORBIDDEN_DST_FACTOR = 4
JAC_DST = 0.75
BDGT_FACTOR = 1
QS_FACTOR = 0.5
REL_TOL = 0.1

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