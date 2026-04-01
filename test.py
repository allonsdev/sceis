import time
import email
from imapclient import IMAPClient

EMAIL = "mazaniallons@gmail.com"
PASSWORD = "runj gjrh zelx wnfe"

def fetch_latest_emails(server, count=4):
    server.select_folder('INBOX')
    
    # Search ALL emails (not just unseen)
    all_messages = server.search(['ALL'])
    
    # Take only the last 4 UIDs
    latest_uids = all_messages[-count:] if len(all_messages) >= count else all_messages
    
    print(f"\n{'='*50}")
    print(f"📬 LATEST {count} EMAILS — {time.strftime('%H:%M:%S')}")
    print(f"{'='*50}")
    
    # Fetch in reverse so newest shows first
    for uid in reversed(latest_uids):
        message_data = server.fetch([uid], 'RFC822')
        msg = email.message_from_bytes(message_data[uid][b'RFC822'])
        
        subject  = msg['subject'] or "(no subject)"
        from_    = msg['from']    or "(unknown sender)"
        date_    = msg['date']    or "(no date)"
        
        # Extract body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")
        
        print(f"\n📩 From:    {from_}")
        print(f"   Subject: {subject}")
        print(f"   Date:    {date_}")
        print(f"   Body:    {body[:200].strip()}...")
        print(f"   {'-'*46}")


def main():
    print("🚀 Starting Gmail monitor — refreshing every 30 seconds")
    print(f"   Account: {EMAIL}\n")
    
    while True:
        try:
            with IMAPClient('imap.gmail.com', ssl=True) as server:
                server.login(EMAIL, PASSWORD)
                fetch_latest_emails(server, count=4)
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("   Retrying in 30 seconds...")
        
        # Wait 30 seconds before next fetch
        print(f"\n⏳ Next check in 30 seconds...")
        time.sleep(30)


if __name__ == "__main__":
    main()