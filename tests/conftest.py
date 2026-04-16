import os
from hypothesis import settings, HealthCheck

# CI profile: run more examples to catch rare edge cases
settings.register_profile(
    "ci",
    max_examples=1000,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)

# Default local profile: fast feedback
settings.register_profile("default", max_examples=100)

# Load profile from env var (set to "ci" in GitHub Actions)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "default"))
