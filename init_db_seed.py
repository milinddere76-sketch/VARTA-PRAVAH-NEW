#!/usr/bin/env python3
"""
Initialize database and seed default data
"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy.orm import Session
import database
import models

# Initialize tables
database.init_db()

# Get database session
eng = database.get_engine()
db = Session(bind=eng)

# Seed channels if needed
if db.query(models.Channel).count() == 0:
    channel = models.Channel(
        id=1,
        name="Main News Channel"
    )
    db.add(channel)
    db.commit()
    print("✅ Created main channel")

# Seed anchors if needed
if db.query(models.Anchor).count() == 0:
    anchors_data = [
        {'name': 'Alice', 'portrait_url': '/assets/alice.png'},
        {'name': 'Bob', 'portrait_url': '/assets/bob.png'},
        {'name': 'Charlie', 'portrait_url': '/assets/charlie.png'},
    ]
    
    for anchor_data in anchors_data:
        anchor = models.Anchor(
            name=anchor_data['name'],
            portrait_url=anchor_data['portrait_url'],
            description=f"{anchor_data['name']} is a professional news anchor"
        )
        db.add(anchor)
    
    db.commit()
    print(f"✅ Seeded {len(anchors_data)} anchors")
else:
    count = db.query(models.Anchor).count()
    print(f"ℹ️ Anchors already exist ({count} total)")

db.close()
print("✅ Database initialization complete")
