import subprocess
import csv
from datetime import datetime
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

def export_call_logs_pdf(logs, filename='call_logs.pdf')::
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    title = Paragraph("Call Logs Report", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    table_text_style = ParagraphStyle(
        name='TableText',
        fontSize=8,
        leading=10
    )    

    
    data = [['Number', 'Name', 'Type', 'Date', 'Duration']]

    for log in logs:
        date_str = ''
        if log.get('date'):
            try:
                date_str = datetime.fromtimestamp(int(log['date']) / 1000).strftime('%Y-%m-%d %H:%M:%S')
            except:
                date_str = log['date']
        name_para = Paragraph(log.get('name', ''), table_text_style)
        
        data.append([
            log.get('number', ''),
            name_para,
            get_call_type_label(log.get('type', '')),
            date_str,
            format_duration(log.get('duration', ''))
        ])

    table = Table(data, repeatRows=1, colWidths=[100, 100, 60, 110, 60])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    elements.append(table)
    doc.build(elements)
    print(f"PDF report saved to {filename}")






def run_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=30)
        if result.returncode != 0:
            print(f"Command failed: {result.stderr}")
            return None
        return result.stdout
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def parse_call_logs(output):
    call_logs = []
    row_pattern = re.compile(r'^Row: \d+ (.+)$')

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        match = row_pattern.match(line)
        if not match:
            continue

        fields = match.group(1).split(', ')
        log = {}

        for field in fields:
            if '=' in field:
                key, value = field.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"')
                if key in ['number', 'name', 'type', 'date', 'duration']:
                    log[key] = value

        if 'number' in log and 'date' in log:
            call_logs.append(log)

    return call_logs

def get_call_type_label(call_type):
    return {
        '1': 'Incoming',
        '2': 'Outgoing',
        '3': 'Missed',
        '4': 'Voicemail',
        '5': 'Rejected',
        '6': 'Blocked',
        '7': 'External'
    }.get(call_type, 'Unknown')
    
def format_duration(seconds_str):
    try:
        total = int(seconds_str)
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60

        parts = []
        if h > 0:
            parts.append(f"{h}h")
        if m > 0 or h > 0:  
            parts.append(f"{m}m")
        parts.append(f"{s}s")
        return ' '.join(parts)
    except:
        return seconds_str


def save_call_logs(logs, filename='call_logs.csv'):
    if not logs:
        print("No call logs found.")
        return

    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Number', 'Name', 'Type', 'Date', 'Duration (sec)'])

        for log in logs:
            date_str = ''
            if log.get('date'):
                try:
                    date_str = datetime.fromtimestamp(int(log['date']) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                except:
                    date_str = log['date']

            writer.writerow([
                "'" + log.get('number', ''), 
                log.get('name', ''),
                get_call_type_label(log.get('type', '')),
                date_str,
                format_duration(log.get('duration', ''))
            ])

    print(f"Saved {len(logs)} call logs to {filename}")

def main():
    print("Fetching call logs...")
    output = run_command(['adb', 'shell', 'content', 'query', '--uri', 'content://call_log/calls'])
    if not output:
        print("Failed to retrieve call logs")
        return

    logs = parse_call_logs(output)
    logs.sort(key=lambda x: int(x.get('date', '0')), reverse=True)

    if logs:
        save_call_logs(logs)
    else:
        print("No valid call logs parsed.")
        
    export_call_logs_pdf(logs)

if __name__ == '__main__':
    main()
