import os
import sqlite3
import database as db
import router_engine as router

db.init_db()

# Insert a dummy team and order
team = db.create_team("Test Team", "Asfalto")
team_id = team["id"]

db.upsert_orders([{
    "os_number": "TEST-1",
    "neighborhood": "Centro",
    "category": "Asfalto"
}, {
    "os_number": "TEST-2",
    "neighborhood": "Jardim Cuiabá",
    "category": "Asfalto"
}])

db.assign_order_to_team("TEST-1", team_id)
db.assign_order_to_team("TEST-2", team_id)

orders = db.get_orders(team_id=team_id)
print(f"Orders for team {team_id}: {orders}")

res = router.roteirizar_equipe(orders)
print(res)
