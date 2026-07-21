"""
SequenceEngine — auto-numbering untuk dokumen.

Cara pakai:
    from core.sequence_engine import SequenceEngine
    
    ref = SequenceEngine.next_by_code('purchase.order.local')
    # → 'PO/L/2026/001'

    ref = SequenceEngine.next_by_id(sequence_pk)
    # → 'PO/IM/2026/001'
"""
import re
from datetime import date

from django.db import transaction


class SequenceEngine:
    """Generate next sequence number with prefix/suffix interpolation."""

    FORMAT_PATTERNS = {
        '%(year)s':  lambda d: f'{d.year:04d}',
        '%(y)s':     lambda d: f'{d.year % 100:02d}',
        '%(month)s': lambda d: f'{d.month:02d}',
        '%(day)s':   lambda d: f'{d.day:02d}',
    }

    @classmethod
    def _interpolate(cls, template: str, ref_date: date) -> str:
        """Replace %(key)s patterns in template with date values."""
        result = template
        for pattern, fn in cls.FORMAT_PATTERNS.items():
            result = result.replace(pattern, fn(ref_date))
        return result

    @classmethod
    def _get_or_create_date_range(cls, sequence, ref_date: date):
        """Find or create a SequenceDateRange for the given date."""
        from core.models.settings.sequence import SequenceDateRange

        reset = sequence.reset_period

        if reset == 'yearly':
            date_from = ref_date.replace(month=1, day=1)
            try:
                date_to = ref_date.replace(year=ref_date.year + 1, month=1, day=1)
            except ValueError:
                date_to = None
        elif reset == 'monthly':
            date_from = ref_date.replace(day=1)
            if ref_date.month == 12:
                date_to = ref_date.replace(year=ref_date.year + 1, month=1, day=1)
            else:
                date_to = ref_date.replace(month=ref_date.month + 1, day=1)
        else:  # no_reset
            date_from = ref_date
            date_to = None  # never resets

        range_obj, _created = SequenceDateRange.objects.get_or_create(
            sequence_id=sequence,
            date_from=date_from,
            defaults={'number_next': 1, 'date_to': date_to},
        )
        return range_obj

    @classmethod
    @transaction.atomic
    def next_by_id(cls, sequence_id: int, ref_date: date = None) -> str:
        """
        Generate the next sequence number for a given Sequence PK.

        Returns the fully formatted reference string, e.g. 'PO/L/2026/001'.
        """
        from core.models.settings.sequence import Sequence

        sequence = Sequence.objects.get(pk=sequence_id, active=True)
        return cls._generate(sequence, ref_date or date.today())

    @classmethod
    @transaction.atomic
    def next_by_code(cls, code: str, ref_date: date = None) -> str:
        """Generate next sequence number by code (e.g. 'purchase.order.local')."""
        from core.models.settings.sequence import Sequence

        sequence = Sequence.objects.get(code=code, active=True)
        return cls._generate(sequence, ref_date or date.today())

    @classmethod
    def _generate(cls, sequence, ref_date: date) -> str:
        """Core logic: increment counter and format reference."""
        range_obj = cls._get_or_create_date_range(sequence, ref_date)

        # Atomic increment
        from django.db.models import F
        from core.models.settings.sequence import SequenceDateRange

        # Use select_for_update + update to ensure atomicity
        SequenceDateRange.objects.filter(pk=range_obj.pk).update(
            number_next=F('number_next') + 1
        )
        range_obj.refresh_from_db()
        number = range_obj.number_next - 1  # value BEFORE increment

        prefix = cls._interpolate(sequence.prefix, ref_date)
        suffix = cls._interpolate(sequence.suffix, ref_date)

        return f'{prefix}{number:0{sequence.padding}d}{suffix}'
