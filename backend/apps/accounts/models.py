from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    """Extended profile for each user, tracking contributor priority and metadata."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    priority = models.PositiveSmallIntegerField(
        default=10000,
        help_text="Claim priority for conflict resolution. Higher beats lower.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self) -> str:
        return f"{self.user.username} (priority={self.priority})"
