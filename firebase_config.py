import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime
import os
import json


# ✅ Load Firebase key from Render Environment Variable
firebase_key = os.environ.get("FIREBASE_KEY")

if not firebase_key:
    raise ValueError("FIREBASE_KEY environment variable not found")

# ✅ Convert JSON string to dictionary
cred = credentials.Certificate(json.loads(firebase_key))

# ✅ Initialize Firebase only once
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        "databaseURL":
        "https://faceattendancesystem-d475a-default-rtdb.asia-southeast1.firebasedatabase.app/"
    })

# ✅ Database reference
attendance_ref = db.reference("attendance")


# ✅ Save attendance function
def save_attendance_firebase(name):

    now = datetime.now()

    data = {
        "name": name,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "status": "Present"
    }

    attendance_ref.push(data)