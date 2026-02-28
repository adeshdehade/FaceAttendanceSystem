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

from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = "secretkey"


# ✅ Test route (VERY IMPORTANT for Render)
@app.route("/")
def home():
    return "✅ Face Attendance Running Successfully on Render"


# ================= ADMIN LOGIN =================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "1234"


# ================= LOGIN =================
@app.route('/')
def home():
    return render_template("login.html")


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


# ================= DELETE =================
@app.route('/delete_student/<filename>')
def delete_student(filename):

    filepath = os.path.join("images", filename)

    if "_" not in filename:
        return redirect('/students')

    sid, name = filename.replace(".jpg","").split("_")

    # ===== DELETE IMAGE =====
    if os.path.exists(filepath):
        os.remove(filepath)

    # ===== DELETE CSV RECORD =====
    if os.path.exists("attendance.csv"):

        import pandas as pd

        df = pd.read_csv("attendance.csv")

        df = df[df["ID"] != sid]

        df.to_csv("attendance.csv", index=False)

    # ===== DELETE FIREBASE RECORD =====
    from firebase_config import attendance_ref

    data = attendance_ref.get()

    if data:
        for key, value in data.items():
            if value.get("id") == sid:
                attendance_ref.child(key).delete()

    return redirect('/students')


# ================= EDIT STUDENT =================
@app.route('/edit_student/<filename>', methods=['GET','POST'])
def edit_student(filename):

    old_path = os.path.join("images", filename)

    if "_" not in filename:
        return redirect('/students')

    old_sid, old_name = filename.replace(".jpg","").split("_")

    if request.method == "POST":

        new_sid = request.form['sid'].strip()
        new_name = request.form['name'].strip()

        new_filename = f"{new_sid}_{new_name}.jpg"
        new_path = os.path.join("images", new_filename)

        # ========= RENAME IMAGE =========
        if os.path.exists(old_path):
            os.rename(old_path, new_path)

        # ========= UPDATE CSV =========
        if os.path.exists("attendance.csv"):

            df = pd.read_csv("attendance.csv")

            df.loc[df["ID"].astype(str) == old_sid, "ID"] = new_sid
            df.loc[df["Name"].str.upper() == old_name.upper(),
                   "Name"] = new_name.upper()

            df.to_csv("attendance.csv", index=False)

        # ========= UPDATE FIREBASE =========
        data = attendance_ref.get()

        if data:
            for key, value in data.items():

                if value.get("id") == old_sid:

                    attendance_ref.child(key).update({
                        "id": new_sid,
                        "name": new_name.upper()
                    })

        return redirect('/students')

    return render_template(
        "edit_student.html",
        sid=old_sid,
        name=old_name,
        filename=filename
    )
# ================= SHOW IMAGE =================
@app.route('/images/<filename>')
def images(filename):
    return send_from_directory("images", filename)


# ================= ATTENDANCE PAGE =================
@app.route('/attendance')
def attendance():

    if 'admin' not in session:
        return redirect('/')

    return render_template("attendance.html")


# ================= RECEIVE MOBILE CAMERA FRAME =================
@app.route("/process_frame", methods=["POST"])
def process_frame():

    try:
        data = request.data.decode("utf-8")
        image_data = data.split(",")[1]

        img_bytes = base64.b64decode(image_data)
        np_arr = np.frombuffer(img_bytes, np.uint8)

        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        # ✅ Face recognition
        process_web_frame(frame)

        return "OK"

    except Exception:
        return "ERROR"


# ================= LIVE ATTENDANCE =================
@app.route('/attendance_data')
def attendance_data():

    try:
        data = attendance_ref.get()

        if not data:
            return "<h5 class='text-center'>No Attendance Yet</h5>"

        records = list(data.values())

        df = pd.DataFrame(records)
        df = df.iloc[::-1]

        return df.to_html(
            classes="table table-bordered table-striped text-center align-middle",
            index=False
        )

    except Exception:
        return "<h5 class='text-center'>Loading Attendance...</h5>"
# ================= LIVE FACE BOX =================
@app.route("/live_face")
def live_face():

    from face_module import last_detected_name, last_face_box

    return {
        "name": last_detected_name,
        "box": last_face_box
    }

# ================= DOWNLOAD EXCEL =================
@app.route('/download')
def download():

    try:
        data = attendance_ref.get()

        if not data:
            return "No Attendance Found"

        df = pd.DataFrame(list(data.values()))

        file_name = "Attendance_Report.xlsx"

        with pd.ExcelWriter(file_name, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)

        return send_file(file_name, as_attachment=True)

    except Exception:
        return "Download Error"
 # ================= RESET ATTENDANCE =================
@app.route('/reset_attendance')
def reset_attendance():

    if 'admin' not in session:
        return redirect('/')

    # ===== DELETE CSV FILE =====
    if os.path.exists("attendance.csv"):
        os.remove("attendance.csv")

    # ===== DELETE FIREBASE DATA =====
    data = attendance_ref.get()

    if data:
        for key in data.keys():
            attendance_ref.child(key).delete()

    return redirect('/attendance')



# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True, threaded=True)