from flask import Flask, render_template, request, redirect, session, send_file, send_from_directory
import os
import pandas as pd
import base64
import cv2
import numpy as np

# ✅ Firebase
from firebase_config import attendance_ref

# ✅ Face processing
from face_module import (
    process_web_frame,
    last_detected_name,
    last_face_box,
    reset_memory
)

# ================= FLASK APP =================
app = Flask(__name__)
app.secret_key = "secretkey"


# ================= LOGIN PAGE =================
@app.route('/')
def home():
    return render_template("login.html")


# ================= ADMIN LOGIN =================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"


@app.route('/login', methods=['POST'])
def login():

    if request.form['username'] == ADMIN_USERNAME and \
       request.form['password'] == ADMIN_PASSWORD:

        session['admin'] = True
        return redirect('/dashboard')

    return "Invalid Login"


# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():

    if 'admin' in session:
        return render_template("dashboard.html")

    return redirect('/')


# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():

    message = ""

    if request.method == 'POST':

        sid = request.form['sid']
        name = request.form['name']
        file = request.files['image']

        filename = f"{sid}_{name}.jpg"
        filepath = f"images/{filename}"

        os.makedirs("images", exist_ok=True)

        if os.path.exists(filepath):
            message = "⚠ Student Already Registered"
        else:
            file.save(filepath)
            message = "✅ Student Registered Successfully"

    return render_template("register.html", message=message)


# ================= STUDENTS =================
@app.route('/students')
def students():

    if 'admin' not in session:
        return redirect('/')

    students_list = []

    if os.path.exists("images"):
        for file in os.listdir("images"):

            if "_" not in file:
                continue

            try:
                sid, name = file.replace(".jpg", "").split("_")

                students_list.append({
                    "sid": sid,
                    "name": name,
                    "image": file
                })

            except:
                continue

    return render_template("students.html", students=students_list)


# ================= DELETE STUDENT =================
@app.route('/delete_student/<filename>')
def delete_student(filename):

    filepath = os.path.join("images", filename)

    if os.path.exists(filepath):
        os.remove(filepath)

    if os.path.exists("attendance.csv"):
        df = pd.read_csv("attendance.csv")
        sid = filename.split("_")[0]
        df = df[df["ID"] != sid]
        df.to_csv("attendance.csv", index=False)

    data = attendance_ref.get()

    if data:
        for key, value in data.items():
            if value.get("id") == filename.split("_")[0]:
                attendance_ref.child(key).delete()

    return redirect('/students')


# ================= IMAGE SERVE =================
@app.route('/images/<filename>')
def images(filename):
    return send_from_directory("images", filename)


# ================= ATTENDANCE PAGE =================
@app.route('/attendance')
def attendance():

    if 'admin' not in session:
        return redirect('/')

    return render_template("attendance.html")


# ================= PROCESS CAMERA FRAME =================
@app.route("/process_frame", methods=["POST"])
def process_frame():

    try:
        data = request.data.decode("utf-8")
        image_data = data.split(",")[1]

        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)

        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        process_web_frame(frame)

        return "OK"

    except:
        return "ERROR"


# ================= LIVE ATTENDANCE =================
@app.route('/attendance_data')
def attendance_data():

    try:
        data = attendance_ref.get()

        if not data:
            return "<h5>No Attendance Yet</h5>"

        df = pd.DataFrame(list(data.values()))
        df = df.iloc[::-1]

        return df.to_html(index=False)

    except:
        return "Loading..."


# ================= LIVE FACE =================
@app.route("/live_face")
def live_face():

    return {
        "name": last_detected_name,
        "box": last_face_box
    }


# ================= DOWNLOAD =================
@app.route('/download')
def download():

    data = attendance_ref.get()

    if not data:
        return "No Attendance"

    df = pd.DataFrame(list(data.values()))

    file_name = "Attendance_Report.xlsx"

    with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)

    return send_file(file_name, as_attachment=True)


# ================= RESET =================
@app.route('/reset_attendance')
def reset_attendance():

    if os.path.exists("attendance.csv"):
        os.remove("attendance.csv")

    data = attendance_ref.get()

    if data:
        for key in data.keys():
            attendance_ref.child(key).delete()

    return redirect('/attendance')


# ================= RENDER RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)