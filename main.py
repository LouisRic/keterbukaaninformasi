import requests
import smtplib
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- KONFIGURASI ---
IDX_API_URL = "https://www.idx.co.id/primary/NewsAnnouncement/GetNewsAnnouncement"
KEYWORDS = [
    "pengambilalihan", "akuisisi", "tender offer", 
    "pembelian saham", "investor strategis", "negosiasi",
    "divestasi", "pemenang tender", "kontrak baru", 
    "pelunasan utang", "menambah kepemilikan"
]

EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT")

def send_email_alert(matches):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        print("Email credentials not set.")
        return

    subject = f"🚨 IDX Alert: {len(matches)} Potensi Multibagger Baru"
    
    html_content = """
    <html><body>
        <h2>Update Saham Potensial (Last 40 Mins)</h2>
        <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f2f2f2;">
                <th>Waktu</th>
                <th>Kode</th>
                <th>Judul</th>
            </tr>
    """
    for item in matches:
        dt_object = datetime.strptime(item['date'], "%Y-%m-%dT%H:%M:%S")
        time_str = dt_object.strftime("%H:%M")
        
        html_content += f"""
            <tr>
                <td>{time_str}</td>
                <td><b>{item['code']}</b></td>
                <td>{item['title']}</td>
            </tr>
        """
    html_content += "</table></body></html>"

    msg = MIMEMultipart()
    msg['From'] = "IDX Bot <" + EMAIL_SENDER + ">"
    msg['To'] = EMAIL_RECIPIENT
    msg['Subject'] = subject
    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
        server.quit()
        print("✅ Email sent!")
    except Exception as e:
        print(f"❌ Email failed: {e}")

def check_idx_news():
    # --- UPDATE PENTING DI SINI (PENYAMARAN BARU) ---
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Referer": "https://www.idx.co.id/id/berita/keterbukaan-informasi/",
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }

    params = {"indexFrom": 0, "pageSize": 50, "year": datetime.now().year, "lang": "id"}

    print("Fetching data from IDX...")
    try:
        response = requests.get(IDX_API_URL, headers=headers, params=params)
        
        # Cek jika masih diblokir
        if response.status_code != 200:
            print(f"Error fetching: {response.status_code} - {response.text[:100]}")
            return

        data = response.json()
        results = data.get('Results', [])
    except Exception as e:
        print(f"Error fetching: {e}")
        return

    found_matches = []
    
    # Timezone Adjustment (UTC to WIB)
    now_utc = datetime.utcnow()
    time_threshold = now_utc - timedelta(minutes=40)

    print(f"Checking news published after: {time_threshold.strftime('%H:%M')} UTC")

    for item in results:
        title = item.get('Title', '').lower()
        pub_date_str = item.get('PublishedDate', '')
        
        if not pub_date_str: continue

        try:
            # Convert WIB string to UTC datetime object
            published_dt_wib = datetime.strptime(pub_date_str, "%Y-%m-%dT%H:%M:%S")
            published_dt_utc = published_dt_wib - timedelta(hours=7)
        except ValueError:
            continue

        if published_dt_utc > time_threshold:
            if any(keyword in title for keyword in KEYWORDS):
                print(f"MATCH FOUND: {item.get('EmitenCode')}")
                found_matches.append({
                    'code': item.get('EmitenCode'),
                    'title': item.get('Title'),
                    'date': pub_date_str
                })

    if found_matches:
        send_email_alert(found_matches)
    else:
        print(f"Checked {len(results)} items. No new matches in the last 40 minutes.")

if __name__ == "__main__":
    check_idx_news()
