import mysql.connector
import cv2
import numpy as np
import tempfile
import os

# Connect to MySQL database
db = mysql.connector.connect(
    host="localhost",  # e.g., "localhost"
    user="root",
    password="",
    database="Exam"
)

cursor = db.cursor()

# Query to fetch all videos
cursor.execute("SELECT video FROM violations")
videos = cursor.fetchall()

# Loop through videos and play them
for index, (video_data,) in enumerate(videos):  # video_data is in binary format
    if video_data:
        # Save video to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video:
            temp_video.write(video_data)
            temp_video_path = temp_video.name  # Get the temp file path

        # Play the video using OpenCV
        cap = cv2.VideoCapture(temp_video_path)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow(f"Video {index+1}", frame)
            if cv2.waitKey(25) & 0xFF == ord('q'):  # Press 'q' to quit playback
                break

        cap.release()
        cv2.destroyAllWindows()

        # Remove the temp video file after playing
        os.remove(temp_video_path)

# Close database connection
cursor.close()
db.close()
