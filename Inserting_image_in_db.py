import mysql.connector
import requests
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def insert_student_data(studentid, name, password, email, gender, year, contact):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="Exam"
        )
        cursor = conn.cursor()

        # Fetch the image from the URL
        url = f"https://intranet.rguktn.ac.in/SMS/usrphotos/user/{studentid.upper()}.jpg"
        response = requests.get(url)
        image = response.content  # Fixed: Removed ()

        # Corrected SQL Query
        sql = "INSERT INTO Student(studentid, name, password, email, gender, year, contact, image) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        
        # Execute Query with Correct Parameters
        cursor.execute(sql, (studentid, name, password, email, gender, year, contact, image))
        conn.commit()

        print("Data inserted successfully!")

    except mysql.connector.Error as err:
        print("Error:", err)
    
    finally:
        cursor.close()
        conn.close()

studentid = "n200963"
name = "Adnan Sami"
password = "Sami@123"
email = "n200963@rguktn.ac.in"
gender = "Male"
year = 3
contact = "6304692429"
hashed_pwd = hash_password(password)
# Calling function with correct arguments
insert_student_data(studentid, name, hashed_pwd, email, gender, year, contact)
