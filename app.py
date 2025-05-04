from flask import Flask, render_template, request
import cv2
import numpy as np
import face_recognition
import os
from datetime import datetime, date
import sqlite3
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText

app = Flask(__name__)

@app.route('/new', methods=['GET', 'POST'])
def new():
    if request.method == "POST":
        return render_template('index.html')
    else:
        return "Everything is okay!"

@app.route('/name', methods=['GET', 'POST'])
def name():
    if request.method == "POST":
        name1 = request.form['name1']
        cam = cv2.VideoCapture(0)

        while True:
            ret, frame = cam.read()
            if not ret:
                break
            cv2.imshow("Press Space to capture image", frame)
            k = cv2.waitKey(1) & 0xFF
            if k == 27:
                break
            elif k == 32:
                img_name = name1 + ".png"
                path = 'Training images'
                cv2.imwrite(os.path.join(path, img_name), frame)
                break

        cam.release()
        cv2.destroyAllWindows()
        return render_template('image.html')
    else:
        return 'All is not well'

@app.route("/", methods=["GET", "POST"])
def recognize():
    if request.method == "POST":
        path = 'Training images'
        images = []
        classNames = []
        myList = os.listdir(path)
        for cl in myList:
            curImg = cv2.imread(os.path.join(path, cl))
            images.append(curImg)
            classNames.append(os.path.splitext(cl)[0])

        def findEncodings(images):
            encodeList = []
            for img in images:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                encodings = face_recognition.face_encodings(img)
                if encodings:
                    encodeList.append(encodings[0])
            return encodeList

        def markData(name):
            now = datetime.now()
            dtString = now.strftime('%H:%M')
            today = date.today()
            conn = sqlite3.connect('information.db')
            conn.execute('''CREATE TABLE IF NOT EXISTS Attendance
                            (NAME TEXT NOT NULL, Time TEXT NOT NULL, Date TEXT NOT NULL)''')
            conn.execute("INSERT INTO Attendance (NAME, Time, Date) values (?, ?, ?)", (name, dtString, today))
            conn.commit()
            conn.close()

        encodeListKnown = findEncodings(images)

        cap = cv2.VideoCapture(0)
        recognized = set()

        while True:
            success, img = cap.read()
            if not success:
                break

            imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
            imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

            facesCurFrame = face_recognition.face_locations(imgS)
            encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)

            for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
                matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
                faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
                matchIndex = np.argmin(faceDis) if len(faceDis) > 0 else -1

                if matchIndex != -1 and faceDis[matchIndex] < 0.50:
                    name = classNames[matchIndex].upper()
                    if name not in recognized:
                        markData(name)
                        recognized.add(name)
                else:
                    name = 'Unknown'

                y1, x2, y2, x1 = [v * 4 for v in faceLoc]
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.rectangle(img, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
                cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)

            cv2.imshow('Punch your Attendance', img)
            if cv2.waitKey(1) & 0xFF == 32:
                break

        cap.release()
        cv2.destroyAllWindows()
        return render_template('first.html')
    else:
        return render_template('main.html')

@app.route('/how', methods=["GET", "POST"])
def how():
    return render_template('form.html')

@app.route('/data', methods=["GET", "POST"])
def data():
    if request.method == "POST":
        today = date.today()
        conn = sqlite3.connect('information.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cursor = cur.execute("SELECT DISTINCT NAME, Time, Date FROM Attendance WHERE Date=?", (today,))
        rows = cur.fetchall()
        conn.close()
        return render_template('form2.html', rows=rows)
    else:
        return render_template('form1.html')

@app.route('/whole', methods=["GET", "POST"])
def whole():
    conn = sqlite3.connect('information.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cursor = cur.execute("SELECT DISTINCT NAME, Time, Date FROM Attendance")
    rows = cur.fetchall()
    conn.close()
    return render_template('form3.html', rows=rows)

@app.route('/dashboard', methods=["GET", "POST"])
def dashboard():
    return render_template('dashboard.html')

@app.route('/sendmail_form', methods=["GET", "POST"])
def sendmail_form():
    if request.method == "POST":
        sender_email = request.form['sender_email']
        sender_pass = request.form['sender_pass']
        receiver_email = request.form['receiver_email']

        try:
            conn = sqlite3.connect('information.db')
            df = pd.read_sql_query("SELECT * FROM Attendance", conn)
            df.to_csv("attendance.csv", index=False)
            conn.close()

            msg = MIMEMultipart()
            msg['Subject'] = "Student Attendance Report"
            msg['From'] = sender_email
            msg['To'] = receiver_email

            html = """\
            <html>
              <body>
                <p>Hi,<br>
                   Please find attached the latest attendance report.<br>
                   <b>Regards,<br>Attendance System</b>
                </p>
              </body>
            </html>
            """
            msg.attach(MIMEText(html, 'html'))

            with open("attendance.csv", 'rb') as f:
                part = MIMEApplication(f.read(), Name="attendance.csv")
                msg.attach(part)

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, sender_pass)
            server.send_message(msg)
            server.quit()

            return "Mail sent successfully!"
        except Exception as e:
            return f"Error sending mail: {str(e)}"

    return render_template("sendmail_form.html")


if __name__ == '__main__':
    app.run(debug=True)


# blrk yasi uhpp lbvb