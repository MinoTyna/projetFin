from supabase import create_client

# ⚠️ Mets directement tes clés ici
SUPABASE_URL = "https://rcbhcqyypiaatvcyolnw.supabase.co"
SUPABASE_KEY = "sb_secret_QcfoccTAxHIjhIGC3vPakQ_pCCVdm0B"
BUCKET = "media"

# Création du client Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
