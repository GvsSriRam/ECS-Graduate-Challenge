import qrcode
import socket
import pandas as pd

# Load the Excel file containing Poster and Judge IDs
file_path_posters = 'Sample_input_abstracts.xlsx'  # Update with the correct path
df_posters = pd.read_excel(file_path_posters)

# Automatically detect the local IP address
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))  # Connect to an external server to get the IP address
    local_ip = s.getsockname()[0]
    s.close()
    return local_ip

LOCAL_IP = get_local_ip()  # Get the correct local IP dynamically

# Function to generate QR code
def generate_qr(poster_id, judge_id):
    url = f"http://{LOCAL_IP}:8000/score/{poster_id}/{judge_id}"
    qr = qrcode.make(url)
    qr.save(f"poster_{poster_id}_judge_{judge_id}.png")  # Save QR code as an image
    print(f"✅ QR Code saved: poster_{poster_id}_judge_{judge_id}.png")

# Loop through the poster data and generate QR codes for assigned judges
for index, row in df_posters.iterrows():
    poster_id = row['Poster']
    judge_id_1 = row['JudgeID 1']
    judge_id_2 = row['Judge ID 2']

    if not pd.isna(judge_id_1):  # Ensure valid judge ID
        generate_qr(poster_id, int(judge_id_1))

    if not pd.isna(judge_id_2):  # Ensure valid judge ID
        generate_qr(poster_id, int(judge_id_2))

print(f"✅ QR codes generated for all posters and assigned judges!")
