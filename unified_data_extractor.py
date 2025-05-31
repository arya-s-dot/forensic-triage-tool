import os
import subprocess
import shutil
from datetime import datetime

WHATSAPP_DB_PATH = "/sdcard/Android/media/com.whatsapp/WhatsApp/Databases"
WHATSAPP_MEDIA_PATH = "/sdcard/Android/media/com.whatsapp/WhatsApp/Media"

LOCAL_EXTRACT_PATH = "extracted/whatsapp"
DB_DEST = os.path.join(LOCAL_EXTRACT_PATH, "databases")
MEDIA_DEST = os.path.join(LOCAL_EXTRACT_PATH, "media")

EXTRA_SOCIAL_MEDIA_PATHS = {
    "telegram": "/sdcard/Android/media/org.telegram.messenger/Telegram",
    "instagram": "/sdcard/Android/media/com.instagram.android"
}


def run_adb_command(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return "", str(e)


def ensure_directories()::
    os.makedirs(DB_DEST, exist_ok=True)
    os.makedirs(MEDIA_DEST, exist_ok=True)


def pull_whatsapp_databases():
    print("\n📦 Pulling WhatsApp databases...")
    out, err = run_adb_command(["adb", "shell", "ls", WHATSAPP_DB_PATH])
    if "No such file" in err or not out:
        print("⚠️  No WhatsApp database files found.")
        return

    for filename in out.splitlines():
        remote_path = f"{WHATSAPP_DB_PATH}/{filename.strip()}"
        print(f"➡️  Pulling {filename.strip()}...")
        subprocess.run(["adb", "pull", remote_path, DB_DEST])


def pull_whatsapp_media():
    print("\n🖼️ Pulling WhatsApp media...")
    out, err = run_adb_command(["adb", "shell", "ls", WHATSAPP_MEDIA_PATH])
    if "No such file" in err or not out:
        print("⚠️  No WhatsApp media folders found.")
        return

    for folder in out.splitlines():
        folder_name = folder.strip()
        remote_media_folder = f"{WHATSAPP_MEDIA_PATH}/{folder_name}"
        local_media_folder = os.path.join(MEDIA_DEST, folder_name)
        os.makedirs(local_media_folder, exist_ok=True)
        print(f"➡️  Pulling media folder: {folder_name}")
        subprocess.run(["adb", "pull", remote_media_folder, local_media_folder])


def pull_additional_social_data():
    for name, path in EXTRA_SOCIAL_MEDIA_PATHS.items():
        print(f"\n🔍 Checking for {name.title()} data...")
        out, err = run_adb_command(["adb", "shell", "ls", path])
        if "No such file" in err or not out:
            print(f"⚠️  {name.title()} data not found.")
            continue

        dest_path = os.path.join("extracted", name)
        os.makedirs(dest_path, exist_ok=True)
        print(f"➡️  Pulling {name.title()} data...")
        subprocess.run(["adb", "pull", path, dest_path])

import zipfile
def zip_exported_data():
    archive_name = f"forensic_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk("extracted"):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, "extracted")
                zipf.write(full_path, arcname=rel_path)
    print(f"\n🗜️  Data zipped to {archive_name}")


def main():
    print("\n📱 Starting Forensic Extractor...")
    ensure_directories()
    pull_whatsapp_databases()
    pull_whatsapp_media()
    pull_additional_social_data()
    zip_exported_data()
    print("\n✅ Extraction complete. Encrypted & media data is saved in ./extracted/")
    print("\n🔐 Reminder: Decryption of WhatsApp .crypt14 files requires the key from /data/data/com.whatsapp/files/key")


if __name__ == "__main__":
    main()
