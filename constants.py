LABEL_TRUE = 'T'
LABEL_FALSE = 'F'
LABEL_OTHER = 'X'
ALLOWED_LABELS = (LABEL_TRUE, LABEL_FALSE, LABEL_OTHER)
# the category is used to markup undecided values
OTHER_CATEGORY = "Other"
PRIVATE_KEY_CATEGORY = "PEM Private Key"
# the rules may have multiline markup and should be skipped for single line obfuscation
MULTI_PATTERN_RULES = ("AWS Multi", "Google Multi", "JWK")
# the rules may be multiline
MULTI_LINE_RULES = MULTI_PATTERN_RULES + (OTHER_CATEGORY, PRIVATE_KEY_CATEGORY)
