import mysql.connector
import cv2
import numpy as np

def fetch_and_display_image(studentid):
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="Exam"
        )
        cursor = conn.cursor()

        query = "SELECT image FROM student WHERE studentid = %s"
        cursor.execute(query, (studentid,))
        result = cursor.fetchone()

        if result and result[0]:
            image_data = result[0]

            # Convert binary to NumPy array
            nparr = np.frombuffer(image_data, np.uint8)

            # Decode image using OpenCV
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # Show image
            cv2.imshow("Student Image", img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        else:
            print("No image found for student:", studentid)

    except mysql.connector.Error as err:
        print("Error:", err)

    finally:
        cursor.close()
        conn.close()

# Example usage
fetch_and_display_image("n200579")
