from app.services.tenant_migrations.v2026_03_01_1 import migration_2026_03_01_1
from app.services.tenant_migrations.v2026_03_01_2 import migration_2026_03_01_2


TENANT_MIGRATIONS = [
    ("2026.03.01.1", migration_2026_03_01_1),
    ("2026.03.01.2", migration_2026_03_01_2),
]
