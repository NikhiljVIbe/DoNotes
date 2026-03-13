"""
User profile for AI personalization.

Copy this file to config/user_profile.py and customize it with your details.
This helps the AI:
  - Correctly classify work vs personal messages
  - Recognize people by name and relationship
  - Improve transcription accuracy for names and places
  - Avoid suggesting emails to yourself

This file is gitignored — your personal data stays local.
"""

# Your name (used in Whisper prompts and GPT context)
USER_NAME = "Your Name"

# Your profile context for GPT (helps classify messages accurately)
# Include your role, company, family members, close colleagues, etc.
USER_PROFILE_CONTEXT = """\
- Role: Your job title at Your Company
- Family: spouse, children, parents (names help with classification)
- Manager: Your Manager's Name
- Close colleagues: list a few key people you interact with daily
"""

# Names that refer to YOU (used to exclude yourself from email suggestions)
# Include your first name, nicknames, and common self-references
SELF_NAMES = {"your_first_name", "me", "myself", "i"}

# People you frequently mention (improves Whisper transcription accuracy)
KNOWN_PEOPLE = [
    # "Colleague Name",
    # "Family Member",
    # "Friend Name",
]

# Places you frequently mention (restaurants, offices, neighborhoods)
WHISPER_PLACES = [
    # "Favorite Restaurant",
    # "Office Location",
    # "Your Neighborhood",
]

# Companies you frequently mention
WHISPER_COMPANIES = [
    # "Your Company",
    # "Partner Company",
]

# Common names in your region (helps Whisper with transcription)
WHISPER_NAMES = [
    # "Common Name 1",
    # "Common Name 2",
]

# Categorized place context for GPT (richer than Whisper hints)
GPT_PLACE_CONTEXT = {
    # "restaurants": ["Place 1", "Place 2"],
    # "cafes": ["Cafe 1"],
    # "areas": ["Neighborhood 1", "Neighborhood 2"],
}

# Categorized company context for GPT
GPT_COMPANY_CONTEXT = {
    # "your_industry": ["Company 1", "Company 2"],
    # "tech": ["Tech Company 1"],
}
