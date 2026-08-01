# Manual migration: master project.project_category + convert project.category
# SelectionField (string) -> Many2OneField (FK) dengan konversi data existing.
#
# Urutan aman:
#  1. CreateModel ProjectCategory
#  2. Seed 5 kategori default (Konstruksi, Infrastruktur, Interior, Renovasi, Lainnya)
#  3. AddField category_temp (FK baru, nullable)
#  4. Konversi data: salin nilai string lama -> FK
#  5. RemoveField category (kolom varchar lama, data sudah disalin)
#  6. RenameField category_temp -> category

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

# nilai lama (Selection) -> (nama kategori master, kode)
CATEGORY_MAP = {
    'konstruksi': ('Konstruksi', 'KST'),
    'infrastruktur': ('Infrastruktur', 'INF'),
    'interior': ('Interior', 'INT'),
    'renovasi': ('Renovasi', 'REN'),
    'lainnya': ('Lainnya', 'LNY'),
}


def seed_categories(apps, schema_editor):
    ProjectCategory = apps.get_model('core', 'ProjectCategory')
    for _old_val, (name, code) in CATEGORY_MAP.items():
        ProjectCategory.objects.get_or_create(name=name, defaults={'code': code})


def migrate_category_data(apps, schema_editor):
    Project = apps.get_model('core', 'Project')
    ProjectCategory = apps.get_model('core', 'ProjectCategory')
    cats = {c.name: c for c in ProjectCategory.objects.all()}
    for p in Project.objects.filter(category__isnull=False):
        if p.category in CATEGORY_MAP:
            target = cats.get(CATEGORY_MAP[p.category][0])
            if target is not None:
                p.category_temp = target
                p.save(update_fields=['category_temp'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0066_milestone'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('is_deleted', models.BooleanField(default=False, verbose_name='Deleted')),
                ('name', models.CharField(default=None, max_length=255, verbose_name='Nama Kategori')),
                ('code', models.CharField(blank=True, default=None, max_length=255, null=True, verbose_name='Kode Kategori')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
            ],
            options={
                'verbose_name': 'Project Category',
                'verbose_name_plural': 'Project Categories',
                'ordering': ['-updated_at'],
                'abstract': False,
            },
        ),
        migrations.RunPython(seed_categories, migrations.RunPython.noop),
        migrations.AddField(
            model_name='project',
            name='category_temp',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='core.projectcategory', verbose_name='Kategori'),
        ),
        migrations.RunPython(migrate_category_data, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='project',
            name='category',
        ),
        migrations.RenameField(
            model_name='project',
            old_name='category_temp',
            new_name='category',
        ),
    ]
