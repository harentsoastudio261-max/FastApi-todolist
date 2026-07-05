"""Domain enums."""
import enum


class Priority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


#----------------------------------------------
# ajut watcher
#------------------------------------------
class SummaryTaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
#----------------------------------------------
# ajut watcher
#------------------------------------------
