import sqlite3
conn = sqlite3.connect('qdrant_storage/collection/screen_memories/storage.sqlite')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print('Tables:', [t[0] for t in tables])

for table in tables:
    table_name = table[0]
    try:
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()[0]
        print(f'{table_name}: {count} rows')
        if table_name == 'point_vectors' and count > 0:
            cursor.execute(f'SELECT * FROM {table_name} LIMIT 3')
            rows = cursor.fetchall()
            for row in rows:
                print(f'  {row[:3]}...')  # First 3 cols
    except Exception as e:
        print(f'{table_name}: error - {e}')

conn.close()
