"""
Seed contoh Chart of Account (COA) — perusahaan dagang/jasa.

Idempotent: get_or_create by code — akun yang sudah ada akan di-skip (tidak
diubah). Parent harus muncul lebih dulu di daftar (dibuat berurutan).

Usage:
    python manage.py seed_coa
"""
from django.core.management.base import BaseCommand

from core.models.accounting.chart_of_account import ChartOfAccount

# (code, name, type, parent_code or None)
COA = [
    # ── ASET (1xxx) ──
    ('1-1000', 'ASET', 'asset', None),
    ('1-1100', 'Kas & Bank', 'asset', '1-1000'),
    ('1-1101', 'Kas', 'asset', '1-1100'),
    ('1-1102', 'Bank BCA', 'asset', '1-1100'),
    ('1-1200', 'Piutang Usaha', 'asset', '1-1000'),
    ('1-1201', 'Piutang Usaha', 'asset', '1-1200'),
    ('1-1300', 'Persediaan', 'asset', '1-1000'),
    ('1-1301', 'Persediaan Barang Dagang', 'asset', '1-1300'),
    ('1-1500', 'Aset Tetap', 'asset', '1-1000'),
    ('1-1501', 'Tanah', 'asset', '1-1500'),
    ('1-1502', 'Bangunan', 'asset', '1-1500'),
    ('1-1503', 'Kendaraan', 'asset', '1-1500'),
    ('1-1504', 'Peralatan Kantor', 'asset', '1-1500'),
    ('1-1600', 'Akumulasi Penyusutan', 'asset', '1-1000'),
    ('1-1601', 'Akum. Penyusutan Bangunan', 'asset', '1-1600'),
    ('1-1602', 'Akum. Penyusutan Kendaraan', 'asset', '1-1600'),
    ('1-1603', 'Akum. Penyusutan Peralatan', 'asset', '1-1600'),
    # ── KEWAJIBAN (2xxx) ──
    ('2-2000', 'KEWAJIBAN', 'liability', None),
    ('2-2100', 'Utang Usaha', 'liability', '2-2000'),
    ('2-2101', 'Utang Usaha', 'liability', '2-2100'),
    ('2-2200', 'Utang Bank', 'liability', '2-2000'),
    ('2-2201', 'Utang Bank', 'liability', '2-2200'),
    ('2-2300', 'Utang Lain-lain', 'liability', '2-2000'),
    ('2-2301', 'Utang Lain-lain', 'liability', '2-2300'),
    # ── EKUITAS (3xxx) ──
    ('3-3000', 'EKUITAS', 'equity', None),
    ('3-3100', 'Modal', 'equity', '3-3000'),
    ('3-3101', 'Modal Pemilik', 'equity', '3-3100'),
    ('3-3200', 'Laba Ditahan', 'equity', '3-3000'),
    ('3-3201', 'Laba Ditahan', 'equity', '3-3200'),
    # ── PENDAPATAN (4xxx) ──
    ('4-4000', 'PENDAPATAN', 'revenue', None),
    ('4-4100', 'Pendapatan Penjualan', 'revenue', '4-4000'),
    ('4-4101', 'Pendapatan Penjualan', 'revenue', '4-4100'),
    ('4-4200', 'Pendapatan Lain-lain', 'revenue', '4-4000'),
    ('4-4201', 'Pendapatan Lain-lain', 'revenue', '4-4200'),
    # ── BEBAN (5xxx) ──
    ('5-5000', 'BEBAN', 'expense', None),
    ('5-5100', 'Beban Operasional', 'expense', '5-5000'),
    ('5-5101', 'Beban Gaji', 'expense', '5-5100'),
    ('5-5102', 'Beban Sewa', 'expense', '5-5100'),
    ('5-5103', 'Beban Listrik & Air', 'expense', '5-5100'),
    ('5-5104', 'Beban Transportasi', 'expense', '5-5100'),
    ('5-5105', 'Beban Perlengkapan Kantor', 'expense', '5-5100'),
    ('5-5106', 'Beban Penyusutan', 'expense', '5-5100'),
    ('5-5200', 'Beban Lain-lain', 'expense', '5-5000'),
    ('5-5201', 'Beban Lain-lain', 'expense', '5-5200'),
]


class Command(BaseCommand):
    help = 'Seed contoh Chart of Account (idempotent — skip akun yang sudah ada)'

    def handle(self, *args, **options):
        created, skipped = 0, 0
        by_code = {}
        for code, name, acct_type, parent_code in COA:
            parent = by_code.get(parent_code) if parent_code else None
            obj, is_new = ChartOfAccount.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'type': acct_type,
                    'parent': parent,
                    'is_active': True,
                },
            )
            if is_new:
                created += 1
            else:
                skipped += 1
            by_code[code] = obj

        self.stdout.write(self.style.SUCCESS(
            f'Seed COA selesai: {created} dibuat, {skipped} sudah ada (skip). '
            f'Total: {ChartOfAccount.objects.filter(is_deleted=False).count()} akun.'
        ))
