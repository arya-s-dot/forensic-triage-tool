import subprocess
import csv
import re
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def uses_devanagari(text):
    return bool(re.search(r'[\u0900-\u097F]', text or ''))

pdfmetrics.registerFont(TTFont('NotoDeva', 'fonts/NotoSansDevanagari-Regular.ttf'))


def export_sms_pdf(messages, filename='sms_messages.pdf'):
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    wrapped_default = ParagraphStyle(name='Latin', fontName='Helvetica', fontSize=9, leading=11, splitLongWords=True, wordWrap='CJK')
    wrapped_deva = ParagraphStyle(name='Devanagari', fontName='NotoDeva', fontSize=9, leading=11, splitLongWords=True, wordWrap='CJK')

    elements.append(Paragraph("SMS Messages Report", styles['Title']))
    elements.append(Spacer(1, 12))

    data = [['Sender', 'Message', 'Date', 'Type']]

    for msg in messages:
        date_str = ''
        if msg.get('date'):
            try:
                date_str = datetime.fromtimestamp(int(msg['date']) / 1000).strftime('%Y-%m-%d %H:%M:%S')
            except:
                date_str = msg['date']

        row = [
            Paragraph(msg.get('address', 'Unknown'), wrapped_default),
            Paragraph(msg.get('body', '')[:300], wrapped_deva if uses_devanagari(msg.get('body')) else wrapped_default),
            Paragraph(date_str, wrapped_default),
            Paragraph(get_sms_type_label(msg.get('type', '')), wrapped_default)
        ]
        data.append(row)

    table = Table(data, repeatRows=1, colWidths=[80, 240, 100, 60])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)
    print(f"SMS PDF report saved to {filename}")


def run_command(command):
    """Run a system command with better error handling."""
    try:
        result = subprocess.run(command, 
                              capture_output=True, 
                              text=True, 
                              encoding='utf-8', 
                              errors='replace',
                              timeout=30)
        if result.returncode != 0:
            print(f"Command failed with error:\n{result.stderr}")
            return None
        return result.stdout
    except subprocess.TimeoutExpired:
        print("Command timed out after 30 seconds")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None

def check_adb_permissions():
    """Verify necessary permissions are granted."""
    print("Checking required permissions...")
    permissions = run_command(['adb', 'shell', 'pm', 'list', 'permissions', '|', 'grep', 'SMS'])
    if permissions:
        print("Found SMS permissions:")
        print(permissions)
    else:
        print("Could not verify SMS permissions")
        
def get_sms_type_label(sms_type):
    return {
        '1': 'Inbox',
        '2': 'Sent',
        '3': 'Draft',
        '4': 'Outbox',
        '5': 'Failed',
        '6': 'Queued'
    }.get(sms_type, 'Unknown')


def get_sms_messages():
    """Try multiple methods to extract SMS messages."""
    print("Attempting to read SMS messages...")

    content_uris = [
        'content://sms/',
        'content://sms/inbox',
        'content://mms-sms/',
        'content://icc/adn'
    ]

    for uri in content_uris:
        print(f"\nTrying URI: {uri}")
        output = run_command(['adb', 'shell', 'content', 'query', '--uri', uri])

        if output:
            print("RAW OUTPUT FROM ADB:\n", output[:1000])

        if output and "Row:" in output:
            print(f"Found data in {uri}")
            return parse_sms_output(output)

        print(f"No data found in {uri}")

    
    print("\nTrying direct database access...")
    db_path = "/data/data/com.android.providers.telephony/databases/mmssms.db"
    output = run_command(['adb', 'shell', 'sqlite3', db_path, '"SELECT address, body FROM sms;"'])

    if output:
        print("Found messages via direct database access")
        return parse_sqlite_output(output)

    print("\nAll methods failed to retrieve SMS")
    return []

def parse_sms_output(output):
    """Parse ADB content query output with multiple fields."""
    messages = []
    row_pattern = re.compile(r'^Row: \d+ (.+)$')

    for line in output.split('\n'):
        line = line.strip()
        if not line:
            continue

        match = row_pattern.match(line)
        if not match:
            continue

        fields = match.group(1).split(', ')
        msg = {}

        for field in fields:
            if '=' in field:
                key, value = field.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"')
                if key in ['address', 'body', 'date', 'creator', 'type']:
                    msg[key] = value

        if 'address' in msg and 'body' in msg:
            messages.append(msg)

    return messages

def parse_sqlite_output(output):
    """Parse sqlite3 direct query output."""
    messages = []
    for line in output.split('\n'):
        if '|' in line:
            parts = line.split('|', 1)
            if len(parts) == 2:
                messages.append({
                    'address': parts[0].strip(),
                    'body': parts[1].strip()
                })
    return messages

def save_messages(messages, filename='sms_messages.csv'):
    """Save extended messages to CSV."""
    if not messages:
        print("No messages to save")
        return

    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Sender', 'Message', 'Date', 'Creator', 'Type'])

        for msg in messages:
            date_str = ''
            if msg.get('date'):
                try:
                    date_str = datetime.fromtimestamp(int(msg['date']) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                except Exception:
                    date_str = msg['date']
            writer.writerow([
                msg.get('address', 'Unknown'),
                msg.get('body', ''),
                date_str,
                msg.get('creator', ''),
                get_sms_type_label(msg.get('type', ''))
            ])

    print(f"Saved {len(messages)} messages to {filename}")

def main():
    print("Starting SMS extraction...")

    devices = run_command(['adb', 'devices'])
    if not devices or 'device' not in devices:
        print("No device connected or unauthorized")
        return

    
    check_adb_permissions()

    
    messages = get_sms_messages()

    if not messages:
        print("\nFailed to retrieve messages. Possible reasons:")
        print("- ADB doesn't have proper permissions")
        print("- SMS database location is different")
        print("- Device manufacturer has customized SMS storage")
        print("\nTry manually checking with:")
        print("adb shell content query --uri content://sms/inbox")
        return

    # Show sample and save
    print("\nFirst 5 messages:")
    for i, msg in enumerate(messages[:5], 1):
        print(f"{i}. From: {msg.get('address', 'Unknown')}")
        print(f"   Message: {msg.get('body', '')[:50]}...\n")

    save_messages(messages)
    print("Saving messages to CSV...")
    export_sms_pdf(messages)
    print("SMS extraction completed successfully.")

if __name__ == "__main__":
    main()
