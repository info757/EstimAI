"""Enums for EstimAI API."""
from enum import Enum

class CountStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"
