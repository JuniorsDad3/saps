from sqlalchemy import create_engine, text

# Use your updated connection string:
DATABASE_URL = "mssql+pyodbc://CloudSA658f47dd:Sgb3%401017@sectorservice.database.windows.net:1433/sectorservice_2025-01-11T23-07Z?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no&timeout=60"

engine = create_engine(DATABASE_URL, echo=True, connect_args={'timeout': 60})

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("Connection successful:", result.fetchone())
except Exception as e:
    print("Connection failed:", e)
