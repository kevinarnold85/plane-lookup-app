import io
import os
import csv
import zipfile
import requests
from supabase import create_client, Client

# FAA Database URL
FAA_URL = "https://registry.faa.gov/database/ReleasableAircraft.zip"

# Supabase Credentials
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials in environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_and_sync():
    print("Downloading FAA Aircraft Registry ZIP...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(FAA_URL, headers=headers)
    response.raise_for_status()

    print("Extracting MASTER.txt from archive...")
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        # Find MASTER.txt file in the zip archive
        master_file = [f for f in z.namelist() if 'MASTER.txt' in f.upper()][0]
        
        with z.open(master_file) as f:
            lines = [line.decode('utf-8', errors='ignore') for line in f.readlines()]

    print("Parsing CSV data...")
    reader = csv.reader(lines)
    header = [col.strip().lower() for col in next(reader)]

    batch = []
    batch_size = 500
    total_processed = 0

    for row in reader:
        if not row or len(row) < 5:
            continue
        
        # Clean up whitespace and map key fields
        clean_row = [field.strip() for field in row]
        
        record = {
            "n_number": clean_row[0],
            "serial_number": clean_row[1] if len(clean_row) > 1 else "",
            "mfr_mdl_code": clean_row[2] if len(clean_row) > 2 else "",
            "eng_mfr_code": clean_row[3] if len(clean_row) > 3 else "",
            "year_mfr": clean_row[4] if len(clean_row) > 4 else "",
            "type_registrant": clean_row[5] if len(clean_row) > 5 else "",
            "name": clean_row[6] if len(clean_row) > 6 else "",
            "street": clean_row[7] if len(clean_row) > 7 else "",
            "street2": clean_row[8] if len(clean_row) > 8 else "",
            "city": clean_row[9] if len(clean_row) > 9 else "",
            "state": clean_row[10] if len(clean_row) > 10 else "",
            "zip_code": clean_row[11] if len(clean_row) > 11 else "",
            "region": clean_row[12] if len(clean_row) > 12 else "",
            "county": clean_row[13] if len(clean_row) > 13 else "",
            "country": clean_row[14] if len(clean_row) > 14 else "",
            "certification": clean_row[15] if len(clean_row) > 15 else "",
            "type_aircraft": clean_row[16] if len(clean_row) > 16 else "",
            "type_engine": clean_row[17] if len(clean_row) > 17 else "",
            "status_code": clean_row[18] if len(clean_row) > 18 else "",
            "mode_s_code": clean_row[32] if len(clean_row) > 32 else "",
            "fractional_owner": clean_row[33] if len(clean_row) > 33 else "",
            "last_action_date": clean_row[30] if len(clean_row) > 30 else "",
            "expiration_date": clean_row[31] if len(clean_row) > 31 else "",
        }

        batch.append(record)

        if len(batch) >= batch_size:
            supabase.table("aircraft").upsert(batch, on_conflict="n_number").execute()
            total_processed += len(batch)
            print(f"Upserted {total_processed} records...")
            batch = []

    if batch:
        supabase.table("aircraft").upsert(batch, on_conflict="n_number").execute()
        total_processed += len(batch)

    print(f"Sync complete. Total records updated: {total_processed}")

if __name__ == "__main__":
    fetch_and_sync()
