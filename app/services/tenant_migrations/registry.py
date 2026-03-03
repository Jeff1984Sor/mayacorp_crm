from app.services.tenant_migrations.v2026_03_01_1 import migration_2026_03_01_1
from app.services.tenant_migrations.v2026_03_01_2 import migration_2026_03_01_2
from app.services.tenant_migrations.v2026_03_01_3 import migration_2026_03_01_3
from app.services.tenant_migrations.v2026_03_03_4 import migration_2026_03_03_4


TENANT_MIGRATIONS = [
    ("2026.03.01.1", migration_2026_03_01_1),
    ("2026.03.01.2", migration_2026_03_01_2),
    ("2026.03.01.3", migration_2026_03_01_3),
    ("2026.03.03.4", migration_2026_03_03_4),
]
