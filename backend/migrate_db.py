import os
import sys
from sqlalchemy import text
from database import get_engine, Base
from models import Anchor

def run_migration():
    print("🚀 Starting Database Migration...")
    engine = get_engine()
    
    # 1. Create missing tables (like 'anchors')
    print("📦 Creating missing tables...")
    Base.metadata.create_all(bind=engine)
    
    # 2. Add missing columns to 'channels'
    print("📝 Syncing 'channels' table schema...")
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE channels ADD COLUMN preferred_anchor_id INTEGER REFERENCES anchors(id)"))
            conn.commit()
            print("✅ Added 'preferred_anchor_id' to 'channels'")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("ℹ️ Column 'preferred_anchor_id' already exists in 'channels'")
            else:
                print(f"⚠️ Error updating 'channels': {e}")

        # 3. Add missing columns to 'ad_campaigns'
        print("📝 Syncing 'ad_campaigns' table schema...")
        try:
            conn.execute(text("ALTER TABLE ad_campaigns ADD COLUMN preferred_anchor_id INTEGER REFERENCES anchors(id)"))
            conn.commit()
            print("✅ Added 'preferred_anchor_id' to 'ad_campaigns'")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("ℹ️ Column 'preferred_anchor_id' already exists in 'ad_campaigns'")
            else:
                print(f"⚠️ Error updating 'ad_campaigns': {e}")

    # 4. Seed a default anchor if none exists
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        if not session.query(Anchor).first():
            print("👤 Seeding default anchor...")
            default_anchor = Anchor(
                name="Default Anchor",
                gender="male",
                description="System default news anchor",
                is_active=True
            )
            session.add(default_anchor)
            session.commit()
            print("✅ Default anchor seeded.")
        else:
            print("✅ Anchors already exist.")
    except Exception as e:
        print(f"❌ Error seeding anchors: {e}")
    finally:
        session.close()

    print("\n🎉 Migration Complete!")

if __name__ == "__main__":
    run_migration()
