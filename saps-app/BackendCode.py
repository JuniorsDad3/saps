from azure.storage.blob import BlobServiceClient
from azure.cognitiveservices.speech import SpeechConfig, SpeechRecognizer
import pyodbc
import smtplib
from email.message import EmailMessage

# Azure SQL connection
connection = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};'
                            'SERVER=sectorservice.database.windows.net;'
                            'DATABASE=<sectorservice_2025-01-11T23-07Z>;'
                            'UID=<gerald.mandebvu@gmail.com>;'
                            'PWD=<Sgb3@1017>')

# Blob Storage connection
blob_service_client = BlobServiceClient.from_connection_string("<DefaultEndpointsProtocol=https;AccountName=sectorservic;AccountKey=GJvminD4Ol3fRS0qkSVeXexItyMv/WmSWpiuK+vjnv3sqGpuepPBMcLJfNjBC6jIEfdf8fBYbNd6+AStW7wMFw==;EndpointSuffix=core.windows.net>")

# Function to assign a case
def assign_case(case_id, type_of_crime):
    cursor = connection.cursor()
    cursor.execute("""
        SELECT TOP 1 UserID, Email 
        FROM Users 
        WHERE CurrentOpenCases < MaxOpenCases 
        AND Unit = ? 
        ORDER BY CurrentOpenCases ASC
    """, type_of_crime)
    user = cursor.fetchone()
    
    if user:
        user_id, email = user
        cursor.execute("""
            UPDATE Cases 
            SET AssignedTo = ?, Unit = ?, Status = 'Assigned'
            WHERE CaseID = ?
        """, email, type_of_crime, case_id)
        
        cursor.execute("""
            UPDATE Users 
            SET CurrentOpenCases = CurrentOpenCases + 1
            WHERE UserID = ?
        """, user_id)
        connection.commit()
        
        # Send notification
        send_email(email, f"New Case Assigned: {case_id}")
    else:
        print("No available user for the case.")

# Email notification
def send_email(to_email, message):
    msg = EmailMessage()
    msg.set_content(message)
    msg["Subject"] = "Case Notification"
    msg["From"] = "<your-email>"
    msg["To"] = to_email

    with smtplib.SMTP("smtp.office365.com", 587) as server:
        server.starttls()
        server.login("<gerald.mandebvu@gmail.com>", "<Sgb3@1017>")
        server.send_message(msg)
