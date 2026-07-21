"""
ChatterLog — tracks field changes across all ERP models.

Every create/update logs old → new values for ALL fields
(no opt-in needed, unlike Odoo's tracked=True approach).
Display control is handled on the frontend via `chatter_show` field config.
"""

from django.db import models


class ChatterLog(models.Model):
    """Immutable log entry for a single field change on any record."""

    model_name = models.CharField(max_length=100, db_index=True)
    record_id = models.IntegerField(db_index=True)
    field_name = models.CharField(max_length=100)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    created_by = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'chatter_log'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['model_name', 'record_id']),
        ]

    def __str__(self):
        return f"[{self.model_name}:{self.record_id}] {self.field_name}: {self.old_value} → {self.new_value}"
