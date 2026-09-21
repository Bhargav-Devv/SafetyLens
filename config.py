"""
Every tunable in the project lives here. Nothing is hard-coded elsewhere.
"""
from pathlib import Path

ROOT = Path(__file__).parent
DATA_RAW = ROOT / "data" / "raw"
DATA_DIR = ROOT / "data"
OUT = ROOT / "out"

# ---------------------------------------------------------------- data
# The OSHA file is Windows-1252, not UTF-8. This is the single most common
# reason it fails to load. Order matters: cp1252 first.
ENCODINGS = ("cp1252", "latin-1", "utf-8")

TEXT_COL = "Final Narrative"
FINE_COL = "EventTitle"      # 4-digit OIICS event, 363 categories
CODE_COL = "Event"           # numeric code, used to derive the major group

MIN_NARRATIVE_CHARS = 25     # drop stubs like "Employee injured."
MIN_EXAMPLES_PER_CLASS = 150 # below this a class cannot be evaluated honestly

# --- Public-roadway events, collapsed (TASK-315, ADR-024) ------------------
# 29 CFR 1910 does not govern public highways, so a worker struck by a car on a
# public road has no applicable standard - the correct answer is the General
# Duty Clause. That rule could not be expressed, because OIICS splits public
# roadway events across 28 labels and EVERY ONE falls below the 150-example
# threshold: 63, 49, 47, 43, 31, and a long tail below 20. All of them were
# filtered out before training, so the classifier could only ever emit a
# *non*roadway label for them, and the system confidently returned
# "1910.178 Powered industrial trucks" for a mail carrier hit by a car.
#
# Collapsed, they clear the threshold comfortably and the gap becomes
# expressible. The cost is granularity nobody was getting anyway - a class with
# 9 examples cannot be learned or evaluated.
COLLAPSE_ROADWAY = True
ROADWAY_CLASS = "Roadway incident on a public road"

# OIICS major event groups - the first digit of the 4-digit event code.
MAJOR_GROUPS = {
    "1": "Violence / injury by persons or animals",
    "2": "Transportation incidents",
    "3": "Fires and explosions",
    "4": "Falls, slips, trips",
    "5": "Exposure to harmful substances/environments",
    "6": "Contact with objects and equipment",
    "7": "Overexertion and bodily reaction",
    "0": "Nonclassifiable",
    "9": "Nonclassifiable",
}

# ---------------------------------------------------------------- model
SEED = 42
TEST_SIZE = 0.2
WORD_MAX_FEATURES = 150_000
CHAR_MAX_FEATURES = 100_000
SVM_C = 1.0

# ---------------------------------------------------------------- regulations
ECFR_URL = "https://www.ecfr.gov/api/versioner/v1/full/{date}/title-29.xml?part=1910"
ECFR_DATES = ("2026-01-01", "2025-01-01", "2024-01-01")
STANDARDS_CACHE = DATA_DIR / "standards.json"

# Additional regulation corpora, merged into the retrieval index when present.
#
# 29 CFR 1910 is general industry. The OSHA severe-injury dataset contains a
# great deal of CONSTRUCTION work, which 1910.12 assigns to Part 1926 - a corpus
# this build has never had, which is why two incidents in the evaluation sets are
# scored `out_of_scope` rather than as retrieval failures.
#
# ecfr.gov is denied by network policy in both workspaces, so Part 1926 cannot be
# fetched here. It can be downloaded in a browser and added with:
#
#     python main.py add-part 1926 path/to/title-29-part-1926.xml
#
# Each extra part is cached beside standards.json and merged at load time. The
# same hard rule applies as ever: real text or nothing.
EXTRA_PART_CACHE = "standards_part_{part}.json"
EXTRA_PARTS = ("1926",)
MIN_STANDARD_CHARS = 400     # skip stub sections with no substantive text

# ---------------------------------------------------------------- retrieval
# Section bodies average ~10,000 characters, which drowns the signal in plain
# TF-IDF. Repeating the title weights the most informative field.
TITLE_WEIGHT = 8

# Hazard vocabulary used to boost sections whose TITLE matches the predicted
# hazard. This is a ROUTING aid, not a legal assertion: it changes which section
# is surfaced, never what that section says. The text quoted is always verbatim
# from eCFR.
HAZARD_KEYWORDS = {
    "Contact with objects and equipment": [
        "machine", "machinery", "guard", "mechanical", "power", "press", "saw",
        "conveyor", "crane", "hoist", "hazardous energy", "lockout", "material",
        "robot", "belt", "welding"],
    "Falls, slips, trips": [
        "fall", "ladder", "scaffold", "walking", "working surface", "stairway",
        "guardrail", "railing", "floor", "opening", "platform"],
    "Exposure to harmful substances/environments": [
        "air contaminant", "ventilation", "respiratory", "hazard communication",
        "toxic", "temperature", "noise", "radiation", "confined space", "substance"],
    "Transportation incidents": [
        "vehicle", "truck", "powered industrial", "motor", "rail", "aerial"],
    "Fires and explosions": [
        "fire", "explosive", "flammable", "combustible", "welding", "cutting"],
    "Overexertion and bodily reaction": [
        "material", "handling", "storage", "manual"],
    "Violence / injury by persons or animals": [],
    "Nonclassifiable": [],
}
KEYWORD_BOOST = 1.2

# Below this similarity there is no real match. The system says so rather than
# returning its three least-bad guesses - the retrieval half of abstention.
RETRIEVAL_FLOOR = 0.08

# ---------------------------------------------------------------- pipeline
# LinearSVC returns decision margins, not probabilities. Confidence here is the
# gap between the top two classes. Below this, the system refuses to classify.
MARGIN_FLOOR = 0.30

# A narrative the human coders could not categorise has no hazard to route on.
NO_RETRIEVAL_GROUPS = {"Nonclassifiable"}

N_STANDARDS = 3
N_SIMILAR = 3

PALETTE = {"accent": "#2D5BFF", "warn": "#A85D00", "good": "#14704A"}


# --- Known regulatory gaps -------------------------------------------------
# Hazards for which NO specific standard exists in 29 CFR 1910.
#
# This is the correction to a real defect. A heat-exhaustion narrative used to
# retrieve "1910.138 Hand protection" at 0.085 against a floor of 0.08, because
# that section's body mentions temperature extremes in the context of gloves.
# It was presented as the applicable rule. It is not.
#
# No threshold fixes that: the correct crane match (1910.179) and the wrong heat
# match (1910.138) both score 0.085. Where the law is genuinely silent, the
# honest answer is to say so, not to return the least-bad section.
#
# Both entries verified against primary sources on 2026-09-20.
GENERAL_DUTY_CLAUSE = "General Duty Clause, OSH Act Section 5(a)(1)"

NO_SPECIFIC_STANDARD_GROUPS = {
    "Overexertion and bodily reaction": (
        "OSHA has no ergonomics standard. The 2000 rule was rescinded by "
        "Senate Joint Resolution 6 under the Congressional Review Act in 2001, "
        "which also bars OSHA from issuing a substantially similar one. "
        "Ergonomic hazards are enforced under the General Duty Clause. "
        "Source: osha.gov/ergonomics/faqs, 2026-09-20."
    ),
    "Violence / injury by persons or animals": (
        "OSHA states it plainly: 'There are currently no specific OSHA "
        "standards for workplace violence.' Enforced under the General Duty "
        "Clause. Source: osha.gov/workplace-violence/enforcement, 2026-09-20."
    ),
}

NO_SPECIFIC_STANDARD_EVENTS = {
    ROADWAY_CLASS: (
        "29 CFR 1910 does not govern public highways. A worker struck by a "
        "vehicle on a public road, or injured in a roadway collision, is "
        "outside the scope of the general industry standards entirely - the "
        "employer's duty runs through the General Duty Clause, and the road "
        "itself is governed by state traffic law rather than by OSHA. "
        "Note that work zones on a highway ARE covered, by 29 CFR 1926 "
        "Subpart G, which this corpus does not hold."
    ),
    "Exposure to environmental heat": (
        "No final federal OSHA heat standard exists in 29 CFR. The rule "
        "proposed in August 2024 remains unfinalised with no target date. "
        "Enforced under the General Duty Clause. Checked 2026-09-20. Note "
        "that several states (CA, CO, MD, MN, NV, OR, WA) do have their own "
        "heat standards - this corpus covers federal 29 CFR 1910 only."
    ),
}

# A section is reported only when the predicted hazard's vocabulary appears in
# its TITLE. Section bodies run to ~10,000 characters, so a narrative finds some
# lexical purchase in almost any of them; the title is what actually identifies
# the subject. This makes retrieval CONFIRM the classification rather than
# wander away from it - which is what retrieval.py always claimed to do.
REQUIRE_HAZARD_ROUTING = True

# Routing looks at the title AND the opening of the section body.
#
# Measured on the dev set (TASK-301): eight of twenty-one misses were two
# sections - 1910.22 "General requirements" and 1910.212 "General requirements
# for all machines". Between them they are among the most-cited standards in all
# of OSHA, and their TITLES carry no hazard vocabulary at all, so title-only
# routing could never nominate them.
#
# Their scope openings do carry it:
#   1910.22  -> "...passageways, storerooms, service rooms, and walking-working
#                surfaces are kept in a clean, orderly..."
#   1910.212 -> "(a) Machine guarding - (1) Types of guarding... point of
#                operation, ingoing nip points, rotating parts..."
#
# Only the OPENING, not the whole body: body-wide matching is what retrieved
# "Hand protection" for a heat narrative in the first place. A title match stays
# stronger evidence than a scope match and keeps the larger boost.
ROUTING_SCOPE_CHARS = 400
SCOPE_BOOST = 0.5


# --- Latent semantic retrieval (TASK-302a) ---------------------------------
# The measured defect is a VOCABULARY GAP, not a ranking bug. 1910.147 is the
# correct answer for cleaning or servicing a live machine and was retrieved zero
# times across both evaluation sets, because the regulation says "energy
# isolating device" and "servicing and maintenance" while the narratives say
# "cleaning", "rollers" and "fingers". Lexical overlap is near zero, so no
# amount of re-weighting TF-IDF can find it.
#
# The standard answer is dense sentence embeddings. Hugging Face is blocked by
# network policy in both workspaces, so no pretrained weights can be downloaded.
#
# Latent semantic analysis needs nothing downloaded. Fit a truncated SVD over
# TF-IDF of the 170 standards PLUS a sample of incident narratives, and terms
# that co-occur across that combined corpus collapse onto shared dimensions -
# which is precisely the bridge "cleaning a conveyor" needs to reach "servicing
# and maintenance". It is the pre-neural solution to this exact problem, it
# trains in seconds on CPU, and it is honest about what it is.
USE_LSA = True            # arm switch; measured before it is trusted
LSA_COMPONENTS = 300
LSA_FIT_NARRATIVES = 20_000   # narratives mixed in so the space learns incident language
LSA_BLEND = 0.5            # final score = (1-b)*tfidf + b*lsa; 1.0 = pure LSA


# --- Index hygiene and a floor that can actually work (TASK-312, TASK-313) --

# Sections that state no requirement about any hazard. `retrieval_labelling_guide.md`
# §5 already says these can never be a correct answer; they were nonetheless sitting
# in the index, and 1910.21 "Scope and definitions" was returned for a real incident
# on the dev set. Excluding them costs nothing and removes ~20 ways to be wrong.
ADMINISTRATIVE_SECTIONS = {
    "1910.1", "1910.2", "1910.3", "1910.4", "1910.5", "1910.6", "1910.7",
    "1910.9", "1910.11", "1910.12", "1910.15", "1910.16", "1910.17", "1910.18",
    "1910.21", "1910.34", "1910.98", "1910.122", "1910.155", "1910.211",
    "1910.241", "1910.301", "1910.331", "1910.399", "1910.401", "1910.402",
    "1910.440", "1910.505", "1910.509", "1910.1020", "1910.1201",
}

# TRIED AND REVERTED (TASK-312b). The idea: PPE sections describe every hazard
# they protect against, so their scope text matches almost any hazard vocabulary,
# and 1910.138 "Hand protection" was being admitted that way. Excluding them from
# SCOPE routing looked obviously right.
#
# Measured on dev, it cost 3 points of recall@3 (0.485 -> 0.455) and gained
# nothing at rank 1. The reason is the part worth keeping: **PPE sections are
# genuinely the correct answer sometimes.** A hydroblasting laceration and a
# bleach splash to the face are both labelled to 1910.132/1910.133 as the
# controlling duty, and neither title carries the hazard's vocabulary, so scope
# routing was the only way to reach them.
#
# The over-admission is real and the cure was worse than the disease. Left empty
# deliberately; do not re-derive it.
NO_SCOPE_ROUTING: set[str] = set()

# The floor, reconsidered (ADR-021).
#
# RETRIEVAL_FLOOR was an absolute cut on a raw TF-IDF cosine. It cannot work on
# the current score for two compounding reasons:
#   1. the score is a lexical/latent blend on a different scale (ADR-019), and
#   2. it is then multiplied by a routing boost of 1.5x to 3.4x, so the number
#      encodes HOW A SECTION WAS ROUTED more than how well it matched.
#
# An absolute threshold on that quantity is meaningless. What is meaningful is
# how far a section stands above the other candidates for the SAME query, which
# is scale-free and survives any future change to the blend.
USE_SIGMA_FLOOR = False
FLOOR_SIGMA = 1.0   # keep candidates at least this many SD above the routed mean
#
# Chosen at 1.0 on the dev set, and chosen on principle rather than on the
# metric, because the metric says the floor only ever costs recall:
#
#   sigma   rec@1   rec@3   returned-nothing
#   0.0     0.333   0.455   0.000   <- never fires
#   0.5     0.333   0.455   0.000   <- never fires
#   1.0     0.303   0.424   0.121   <- smallest value that actually declines
#   1.5     0.273   0.394   0.273
#   2.0     0.242   0.364   0.303
#
# precision@1 - of the times it answers, how often the lead is right - moves
# 0.333 -> 0.345 -> 0.375 -> 0.347 across that range, which is noise at n=33.
# A floor does not buy recall and was never supposed to. It buys the ability to
# decline, and 1.0 is the cheapest setting that restores it (ADR-009).


# --- Routing on the predicted EVENT, not only the hazard group -------------
# HAZARD_KEYWORDS is one hand-written list per major group - eight lists for
# 86,000 incidents. The fine-grained prediction is far more specific and is
# already computed: "Caught in running equipment or machinery during
# maintenance, cleaning" contains "maintenance" and "cleaning", and 1910.147
# opens with "the servicing and maintenance of machines and equipment".
#
# So the label the classifier already produces carries routing vocabulary that
# the hand-written list never will, for free and for all 77 classes.
# TRIED AND REJECTED, twice, both measured on dev:
#   as title + scope keywords : recall@1 0.333 -> 0.242, MRR 0.404 -> 0.354.
#       Generic event words like "equipment" landed in tier 0 and crowded the
#       lead slot, which is reserved for the strongest evidence.
#   as scope keywords only    : identical on every metric. No gain, no loss.
# LSA already bridges the gap this was meant to bridge - 1910.147 surfaces for
# a cleaning narrative without it. Kept, disabled, so it is not re-derived.
EVENT_ROUTING = False
EVENT_STOPWORDS = {
    "unspecified", "other", "single", "episode", "multiple", "types",
    "involving", "without", "incident", "same", "level", "during", "regular",
    "n.e.c", "nec", "from", "with", "into", "against", "due", "than", "this",
    "that", "when", "while", "person", "worker", "employee", "body", "part",
}
EVENT_MIN_WORD = 4

