import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import sqlite3
from database.connection import get_session_factory
from database.models import Camera

s = get_session_factory()()
cam4 = s.query(Camera).filter(Camera.id == 4).first()
if cam4:
    if not cam4.stream_source.endswith('/video'):
        cam4.stream_source = cam4.stream_source.rstrip('/') + '/video'
    print(f'Camera 4 updated: {cam4.name} -> {cam4.stream_source}')

dupes = s.query(Camera).filter(Camera.id > 4, Camera.name == 'entry').all()
print(f'Deleting {len(dupes)} duplicate entry cameras in Supabase...')
for d in dupes:
    s.delete(d)
s.commit()

try:
    con = sqlite3.connect('d:/LIL/data/ecolifybuddy_dev.db')
    cur = con.cursor()
    cur.execute("DELETE FROM cameras WHERE id > 4 AND name = 'entry'")
    cur.execute("UPDATE cameras SET stream_source = 'http://192.168.238.90:8080/video' WHERE id = 4")
    con.commit()
    con.close()
except Exception as e:
    print('SQLite sync note:', e)

print('Current cameras in DB:')
for c in s.query(Camera).all():
    print(f'  ID: {c.id}, Name: {c.name}, Source: {c.stream_source}')
s.close()
