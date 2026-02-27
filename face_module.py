import cv2
import face_recognition
import os
import numpy as np
import csv
from datetime import datetime

from firebase_config import attendance_ref


# ================= LOAD STUDENT FACES =================
path = "images"
encodeList = []
names = []

print("Loading student faces...")

for file in os.listdir(path):

    if "_" not in file:
        continue

    img = cv2.imread(f"{path}/{file}")

    if img is None:
        continue

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    faces = face_recognition.face_locations(rgb)

    if len(faces) > 0:
        encodes = face_recognition.face_encodings(rgb, faces)
        encodeList.append(encodes[0])
        names.append(os.path.splitext(file)[0])

print("✅ Faces Loaded Successfully")


# ================= DAILY MEMORY =================
marked_today = {}

# LIVE DISPLAY VARIABLES
last_detected_name = "Scanning..."
last_face_box = None


# ================= MARK ATTENDANCE =================
def mark_attendance(sid, name):

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M")

    # ✅ RAM duplicate protection
    if sid in marked_today:
        if marked_today[sid] == today:
            return

    # ✅ Firebase duplicate protection
    data = attendance_ref.get()

    if data:
        for record in data.values():
            if record.get("id") == sid and record.get("date") == today:
                marked_today[sid] = today
                return

    # ================= CSV SAVE =================
    file = "attendance.csv"

    if not os.path.exists(file):
        with open(file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Date", "Time"])

    with open(file, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            sid,
            name.upper(),
            today,
            time
        ])

    # ================= FIREBASE SAVE =================
    attendance_ref.push({
        "id": sid,
        "name": name.upper(),
        "date": today,
        "time": time,
        "status": "Present"
    })

    marked_today[sid] = today
    print(f"✅ Attendance Marked: {name}")


# =====================================================
# ✅ PROCESS FRAME FROM MOBILE / WEB CAMERA
# =====================================================
def process_web_frame(frame):

    global last_detected_name, last_face_box

    try:

        small = cv2.resize(frame, (0, 0), None, 0.25, 0.25)
        rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)

        faces = face_recognition.face_locations(rgb_small)
        encodes = face_recognition.face_encodings(rgb_small, faces)

        if len(faces) == 0:
            last_detected_name = "Scanning..."
            last_face_box = None
            return

        for encodeFace, faceLoc in zip(encodes, faces):

            faceDis = face_recognition.face_distance(
                encodeList, encodeFace)

            matchIndex = np.argmin(faceDis)

            # ✅ GET ORIGINAL FRAME SIZE
            h, w, _ = frame.shape

            y1, x2, y2, x1 = faceLoc

            # ✅ CONVERT TO SCREEN PERCENTAGE
            top = (y1 * 4) / h
            right = (x2 * 4) / w
            bottom = (y2 * 4) / h
            left = (x1 * 4) / w

            last_face_box = [left, top, right, bottom]

            if faceDis[matchIndex] < 0.45:

                student = names[matchIndex]
                sid, name = student.split("_")

                last_detected_name = f"{sid} - {name.upper()}"

                mark_attendance(sid, name)
                return

        # ✅ UNKNOWN FACE
        last_detected_name = "Unknown Face"

    except Exception as e:
        print("Face Process Error:", e)
        
# ================= RESET MEMORY =================
def reset_memory():
    global marked_today
    marked_today.clear()