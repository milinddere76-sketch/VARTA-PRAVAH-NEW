import os
import sys

# Add backend to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database import get_session_local
from models import Anchor

def fix_anchors():
    Session = get_session_local()
    db = Session()
    try:
        # Female Anchor
        female = db.query(Anchor).filter(Anchor.gender == "female").first()
        if female:
            female.portrait_url = "assets/female_anchor.png"
            print("Set portrait for female anchor")
            
        # Male Anchor
        male = db.query(Anchor).filter(Anchor.gender == "male").first()
        if male:
            male.portrait_url = "assets/male_anchor.png"
            print("Set portrait for male anchor")
            
        db.commit()
    except Exception as e:
        print(f"Error fixing anchors: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    fix_anchors()
