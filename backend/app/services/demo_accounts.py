from __future__ import annotations


DEMO_USERS = [
    {
        "email": f"role{role_number:02d}@local.dev",
        "name": f"Role {role_number:02d} Demo User",
        "password": f"role{role_number:02d}-demo",
        "persona_id": f"role-{role_number:02d}",
        "persona_name": persona_name,
        "role": f"role-{role_number:02d}",
    }
    for role_number, persona_name in [
        (1, "CC Customer"),
        (2, "CC Inventory"),
        (3, "CC Warranty"),
        (4, "BO Customer"),
        (5, "BO Inventory"),
        (6, "BO Warranty"),
        (7, "CC Manager"),
        (8, "BO Manager"),
        (9, "Operations Manager"),
        (10, "Quality Analyst"),
        (11, "Admin Executive"),
        (12, "Surgeon"),
        (13, "Office Manager"),
        (14, "Sales Rep"),
        (15, "CSR"),
        (16, "Patient"),
        (17, "Manager"),
    ]
]

DEMO_USERS_BY_EMAIL = {user["email"]: user for user in DEMO_USERS}
