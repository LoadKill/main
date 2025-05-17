import sqlite3

conn = sqlite3.connect('illegal_vehicle.db')
cursor = conn.cursor()

cursor.execute("SELECT * FROM illegal_vehicles")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()