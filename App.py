from datetime import datetime
import sqlite3
import urllib.parse
import pandas as pd
import pyttsx3
import streamlit as st

# --- CONFIGURATION DE LA PAGE (MOBILE-FRIENDLY) ---
st.set_page_config(
    page_title="SmartBudget FCFA",
    page_icon="💳",
    layout="centered",  # Centré pour imiter le format d'une application mobile
    initial_sidebar_state="collapsed",
)

# --- DESIGN CSS SPÉCIAL FORMAT ANDROID / MOBILE ---
st.markdown("""
    <style>
    /* Fond général épuré style Fintech */
    .main {
        background-color: #F8FAFC;
    }
    
    /* Optimisation pour les écrans tactiles et mobiles */
    @media (max-width: 768px) {
        .stTextInput, .stNumberInput, .stSelectbox, .stDateInput {
            width: 100% !important;
        }
        h1 {
            font-size: 1.5rem !important;
        }
        h2, h3 {
            font-size: 1.2rem !important;
        }
    }

    /* Cartes métriques au design moderne */
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 14px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.03);
        border: 1px solid #E2E8F0;
        text-align: center;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)


# --- FONCTION D'ALARME VOCALE ---
def declencher_alarme_vocale(montant):
  try:
    engine = pyttsx3.init()
    engine.setProperty("rate", 150)
    engine.setProperty("volume", 1.0)
    texte = f"Attention ! Votre dépense vient d'atteindre {montant:,.0f} Francs CFA. Seuil critique de 35 000 francs dépassé !"
    engine.say(texte)
    engine.runAndWait()
  except Exception as e:
    print(f"Erreur vocale : {e}")


# --- BASE DE DONNÉES ---
def init_db():
  conn = sqlite3.connect("budget_innovant.db")
  cursor = conn.cursor()
  cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            description TEXT,
            amount REAL,
            category TEXT
        )
    """)
  conn.commit()
  conn.close()


init_db()

# --- INITIALISATION DE L'ÉTAT DE SESSION ---
if "derniere_alerte" not in st.session_state:
  st.session_state.derniere_alerte = None

# --- HEADER MOBILE-FRIENDLY ---
st.title("💳 SmartBudget — Mobile")
st.caption("Pilotez vos finances personnelles directement depuis votre mobile.")

# --- FORMULAIRE DE SAISIE OPTIMISÉ MOBILE ---
with st.expander(
    "➕ Ajouter une dépense (Appuyez ici)", expanded=True
):  # Ouvert par défaut sur mobile pour aller plus vite
  with st.form("expense_form", clear_on_submit=True):
    # Sur mobile, on empile les champs verticalement pour éviter l'effet serré
    description = st.text_input(
        "Description", placeholder="Ex: Transport, Repas..."
    )
    amount = st.number_input(
        "Montant (en FCFA)", min_value=0.0, step=500.0, format="%.0f"
    )
    category = st.selectbox(
        "Catégorie",
        [
            "🍔 Alimentation & Restauration",
            "🏠 Logement & Charges",
            "🚗 Transport",
            "🎉 Loisirs & Sorties",
            "💊 Santé",
            "💡 Factures & Abonnements",
            "📦 Autre",
        ],
    )
    expense_date = st.date_input("Date", value=datetime.today())

    st.markdown("<br>", unsafe_allow_html=True)
    submit_button = st.form_submit_button(
        label="✨ Enregistrer", use_container_width=True
    )

    if submit_button:
      if description and amount > 0:
        conn = sqlite3.connect("budget_innovant.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO expenses (date, description, amount, category) VALUES"
            " (?, ?, ?, ?)",
            (expense_date.strftime("%Y-%m-%d"), description, amount, category),
        )
        conn.commit()
        conn.close()

        # --- GESTION DE L'ALERTE SEUIL (35 000 FCFA) ---
        if amount >= 35000:
          st.session_state.derniere_alerte = {
              "amount": amount,
              "description": description,
              "category": category,
          }
          declencher_alarme_vocale(amount)
        else:
          st.session_state.derniere_alerte = None
          st.success(f"Dépense de **{amount:,.0f} FCFA** ajoutée !")

        st.rerun()
      else:
        st.error("⚠️ Entrez une description et un montant valide.")

# --- AFFICHAGE PERSISTANT DE L'ALERTE WHATSAPP ---
if st.session_state.derniere_alerte:
  alerte = st.session_state.derniere_alerte
  st.error(
      f"🚨 SEUIL CRITIQUE : {alerte['amount']:,.0f} FCFA (Seuil de 35 000 FCFA"
      " atteint) !"
  )

  num_whatsapp = st.text_input(
      "📱 Votre numéro WhatsApp (ex: 2250700000000)", value=""
  )

  if num_whatsapp:
    message_wa = (
        f"🚨 *ALERTE BUDGET SMARTBUDGET*\n"
        f"Grosse dépense enregistrée :\n"
        f"📌 *Desc:* {alerte['description']}\n"
        f"💰 *Montant:* {alerte['amount']:,.0f} FCFA\n"
        f"📂 *Catégorie:* {alerte['category']}"
    )
    encoded_message = urllib.parse.quote(message_wa)
    wa_link = f"https://wa.me/{num_whatsapp}?text={encoded_message}"

    st.markdown(
        f"📲 **Action :** [Envoyer l'alerte sur WhatsApp]({wa_link})",
        unsafe_allow_html=True,
    )
  else:
    st.info("👆 Entrez votre numéro WhatsApp pour générer le lien.")

  if st.button("Fermer l'alerte", use_container_width=True):
    st.session_state.derniere_alerte = None
    st.rerun()

# --- CHARGEMENT DES DONNÉES ---
conn = sqlite3.connect("budget_innovant.db")
df = pd.read_sql_query(
    "SELECT id, date, description, amount, category FROM expenses ORDER BY date"
    " DESC",
    conn,
)
conn.close()

# --- TABLEAU DE BORD & ANALYSE ---
if not df.empty:
  st.markdown("---")
  df["date_dt"] = pd.to_datetime(df["date"])

  st.subheader("📊 Tableau de Bord")
  available_periods = sorted(
      df["date_dt"].dt.to_period("M").unique(), reverse=True
  )
  period_options = [str(p) for p in available_periods]

  selected_period = st.selectbox(
      "📅 Filtrer par mois", ["Tous les mois"] + period_options
  )

  df_filtered = df.copy()
  if selected_period != "Tous les mois":
    df_filtered = df_filtered[
        df_filtered["date_dt"].dt.to_period("M").astype(str) == selected_period
    ]

  if not df_filtered.empty:
    total_spent = df_filtered["amount"].sum()
    total_trans = len(df_filtered)
    top_cat = df_filtered.groupby("category")["amount"].sum().idxmax()

    # KPIs empilés proprement sur mobile
    st.metric(
        label="💸 Dépenses Totales",
        value=f"{total_spent:,.0f} FCFA".replace(",", " "),
    )
    col_kpi2, col_kpi3 = st.columns(2)
    with col_kpi2:
      st.metric(label="📝 Transactions", value=total_trans)
    with col_kpi3:
      st.metric(label="🔥 Top Catégorie", value=top_cat)

    st.markdown("---")

    # Historique et Graphique empilés pour un affichage vertical Android nickel
    st.markdown("### 📋 Historique")
    df_display = df_filtered[
        ["id", "date", "description", "amount", "category"]
    ].copy()
    df_display["amount"] = df_display["amount"].apply(
        lambda x: f"{x:,.0f} FCFA".replace(",", " ")
    )
    st.dataframe(df_display, use_container_width=True, height=250)

    with st.expander("🗑️ Supprimer une dépense"):
      exp_ids = df_filtered["id"].tolist()
      if exp_ids:
        sel_id = st.selectbox("ID à supprimer", exp_ids)
        if st.button("Supprimer définitivement", type="primary"):
          conn = sqlite3.connect("budget_innovant.db")
          cursor = conn.cursor()
          cursor.execute("DELETE FROM expenses WHERE id = ?", (sel_id,))
          conn.commit()
          conn.close()
          st.toast("Dépense supprimée !", icon="🗑️")
          st.rerun()
      else:
        st.write("Aucune dépense à supprimer.")

    st.markdown("### 📈 Répartition")
    cat_totals = df_filtered.groupby("category")["amount"].sum()
    st.bar_chart(cat_totals, color="#059669")
  else:
    st.info(f"Aucune dépense pour la période ({selected_period}).")

else:
  st.markdown("---")
  st.info(
      "💡 **Commencez par ajouter votre première dépense** ci-dessus pour"
      " démarrer !"
  )
