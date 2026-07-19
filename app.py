"""
TRAVEL PLANNER — Flight Search with Dynamic UI Inputs
==========================================================

NEW CONCEPT: st.form + input widgets, so the user provides origin,
destination, and date through the browser instead of hardcoded values.

st.form groups multiple inputs together so the app only re-runs ONCE,
when the "Search" button is clicked — not on every single keystroke,
which is what would happen with ungrouped widgets.
"""

import streamlit as st
from streamlit_searchbox import st_searchbox
import requests
import os

TRAVELPAYOUTS_TOKEN = os.environ.get("TRAVELPAYOUTS_API_TOKEN") or st.secrets.get(
    "TRAVELPAYOUTS_API_TOKEN", ""
)

# Airlines are returned as 2-letter IATA codes, not names. This lookup
# covers major carriers relevant to Indian/international routes; any
# code not in this dict just falls back to showing the raw code.
AIRLINE_NAMES = {
    "IX": "Air India Express",
    "AI": "Air India",
    "6E": "IndiGo",
    "SG": "SpiceJet",
    "UK": "Vistara",
    "G8": "Go First",
    "I5": "AirAsia India",
    "EK": "Emirates",
    "EY": "Etihad Airways",
    "QR": "Qatar Airways",
    "SQ": "Singapore Airlines",
    "TG": "Thai Airways",
    "LH": "Lufthansa",
    "BA": "British Airways",
    "AF": "Air France",
    "KL": "KLM",
    "TK": "Turkish Airlines",
    "EI": "Aer Lingus",
    "VS": "Virgin Atlantic",
    "DL": "Delta Air Lines",
    "UA": "United Airlines",
    "AA": "American Airlines",
    "CX": "Cathay Pacific",
    "JL": "Japan Airlines",
    "NH": "All Nippon Airways",
    "MH": "Malaysia Airlines",
    "TR": "Scoot",
    "FZ": "flydubai",
    "WY": "Oman Air",
    "KU": "Kuwait Airways",
    "GF": "Gulf Air",
    "SV": "Saudia",
}


def airline_name(code: str) -> str:
    return AIRLINE_NAMES.get(code, code)


def search_city(query: str) -> list[dict]:
    """Look up cities/airports matching a typed name. Returns a list of
    dicts with 'name', 'code', 'country', 'type' — no API key needed,
    this is a free public Travelpayouts endpoint."""
    if not query or len(query) < 2:
        return []

    url = "https://autocomplete.travelpayouts.com/places2"
    params = {"term": query, "locale": "en", "types[]": ["city", "airport"]}
    response = requests.get(url, params=params)

    if response.status_code != 200:
        return []

    results = []
    for item in response.json():
        results.append(
            {
                "name": item.get("name", ""),
                "code": item.get("code", ""),
                "country": item.get("country_name", ""),
                "type": item.get("type", ""),
            }
        )
    return results


def city_search_options(query: str) -> list[tuple[str, str]]:
    """Called by st_searchbox on every keystroke. Returns a list of
    (display_label, value) tuples — value is what gets stored when the
    user clicks a suggestion; display_label is what they see in the
    dropdown. This is what makes it a single live-search box instead
    of a separate text input + selectbox + confirm button."""
    matches = search_city(query)
    return [(f"{m['name']} ({m['code']}) — {m['country']}", m["code"]) for m in matches]


def city_picker(label: str, state_key: str):
    """Single searchable box: type a city name, live suggestions appear,
    click one, done — the IATA code is stored in st.session_state[state_key]."""
    selected_code = st_searchbox(
        city_search_options,
        placeholder=f"{label} — type a city name",
        key=f"{state_key}_searchbox",
    )
    st.session_state[state_key] = selected_code or ""


def search_flights(origin: str, destination: str, departure_date: str) -> list[dict]:
    """Search for the cheapest flights between two cities. Returns a list
    of flight dicts (empty list if none found), not a formatted string,
    so the UI can render each result as its own card."""
    url = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
    params = {
        "origin": origin.upper(),
        "destination": destination.upper(),
        "departure_at": departure_date,
        "sorting": "price",
        "direct": "false",
        "currency": "inr",
        "limit": 5,
        "token": TRAVELPAYOUTS_TOKEN,
    }

    response = requests.get(url, params=params)
    data = response.json()

    if not data.get("success") or not data.get("data"):
        return []

    return data["data"]


# ---------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------
st.set_page_config(page_title="Flight Finder", page_icon="✈️")
st.title("✈️ Flight Finder")
st.caption("Find the cheapest flights between two cities.")

col1, col2 = st.columns(2)
with col1:
    city_picker("From", "origin_code")
with col2:
    city_picker("To", "destination_code")

with st.form("flight_search_form"):
    departure_date = st.date_input("Departure date")
    submitted = st.form_submit_button("Search Flights")

origin = st.session_state.get("origin_code", "")
destination = st.session_state.get("destination_code", "")

if submitted:
    if not origin or not destination:
        st.warning("Please select both a departure and arrival city above.")
    else:
        with st.spinner(f"Searching flights from {origin} to {destination}..."):
            date_str = departure_date.strftime("%Y-%m-%d")
            flights = search_flights(origin, destination, date_str)

        if not flights:
            st.info(
                f"No cached fares found for {origin} → {destination} on {date_str}. "
                "Try a more commonly searched route, or a nearer date."
            )
        else:
            # Results already come sorted by price from the API (sorting="price"),
            # but sort again here defensively in case that ever changes
            flights = sorted(flights, key=lambda f: f["price"])
            st.success(f"Found {len(flights)} option(s), cheapest first:")
            for flight in flights:
                price = flight["price"]
                airline = airline_name(flight.get("airline", ""))
                dep_time = flight.get("departure_at", "N/A")
                booking_link = "https://www.aviasales.com" + flight.get("link", "")

                with st.container(border=True):
                    st.markdown(f"### ₹{price}")
                    st.write(f"**Airline:** {airline}")
                    st.write(f"**Departs:** {dep_time}")
                    st.link_button("Book this flight", booking_link)
