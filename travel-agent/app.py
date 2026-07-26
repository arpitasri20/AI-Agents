"""
TRAVEL AGENT — AI agent with flight + hotel search tools
============================================================

This is a genuine AI agent, not a form: you chat naturally
("find me cheap flights from Lucknow to Delhi next week"), and
Gemini decides WHICH tool to call (flights, hotels, both, or
neither) and WHAT arguments to pass — same LangGraph pattern as
the weather + currency agent, just with travel-specific tools.
"""

import os
from datetime import datetime

import streamlit as st
import requests
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition

TRAVELPAYOUTS_TOKEN = os.environ.get("TRAVELPAYOUTS_API_TOKEN") or st.secrets.get(
    "TRAVELPAYOUTS_API_TOKEN", ""
)

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


def resolve_city_code(city_name: str) -> str:
    """Turn a typed city name into an IATA code using the free
    Travelpayouts autocomplete endpoint. Returns '' if no match."""
    url = "https://autocomplete.travelpayouts.com/places2"
    params = {"term": city_name, "locale": "en", "types[]": ["city", "airport"]}
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return ""
    results = response.json()
    return results[0]["code"] if results else ""


# ---------------------------------------------------------------------
# TOOL 1: Flight search
# ---------------------------------------------------------------------
@tool
def search_flights(origin_city: str, destination_city: str, departure_date: str) -> str:
    """Search for the cheapest flights between two cities.

    Args:
        origin_city: Departure city name, e.g. 'Lucknow'.
        destination_city: Arrival city name, e.g. 'Delhi'.
        departure_date: Date in YYYY-MM-DD format.
    """
    origin = resolve_city_code(origin_city)
    destination = resolve_city_code(destination_city)
    if not origin or not destination:
        return f"Could not find airport codes for {origin_city} or {destination_city}."

    url = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
    params = {
        "origin": origin,
        "destination": destination,
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
        return f"No cached flights found for {origin_city} to {destination_city} on {departure_date}."

    flights = sorted(data["data"], key=lambda f: f["price"])
    lines = []
    for f in flights:
        link = "https://www.aviasales.com" + f.get("link", "")
        lines.append(
            f"₹{f['price']} — {airline_name(f.get('airline', ''))}, "
            f"departs {f.get('departure_at', 'N/A')} — Book: {link}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------
# TOOL 2: Hotel search
# ---------------------------------------------------------------------
@tool
def search_hotels(city_name: str, check_in: str, check_out: str) -> str:
    """Search for hotels with cached prices in a city.

    Args:
        city_name: City name, e.g. 'Goa'.
        check_in: Check-in date, YYYY-MM-DD.
        check_out: Check-out date, YYYY-MM-DD (must be after check_in).
    """
    url = "https://engine.hotellook.com/api/v2/cache.json"
    params = {
        "location": city_name,
        "checkIn": check_in,
        "checkOut": check_out,
        "currency": "inr",
        "limit": 5,
        "token": TRAVELPAYOUTS_TOKEN,
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return f"No cached hotel prices found for {city_name}."

    data = response.json()
    if not isinstance(data, list) or not data:
        return f"No cached hotel prices found for {city_name} on those dates."

    hotels = sorted(data, key=lambda h: h.get("priceAvg", float("inf")))
    lines = []
    for h in hotels:
        link = f"https://search.hotellook.com/?hotelId={h.get('hotelId', '')}"
        lines.append(
            f"{h.get('hotelName', 'Unknown hotel')} — ₹{h.get('priceAvg', 'N/A')}/night, "
            f"{h.get('stars', 'N/A')}-star — View: {link}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------
# Build the LangGraph agent
# ---------------------------------------------------------------------
@st.cache_resource
def build_graph():
    tools = [search_flights, search_hotels]
    llm = ChatGoogleGenerativeAI(
        model="gemini-flash-latest",
        google_api_key=os.environ.get("GEMINI_API_KEY")
        or st.secrets.get("GEMINI_API_KEY", ""),
    )
    llm_with_tools = llm.bind_tools(tools)

    today = datetime.now().strftime("%Y-%m-%d")

    def agent_node(state: MessagesState):
        system_note = {
            "role": "system",
            "content": f"Today's date is {today}. When the user gives a relative date "
            f"like 'next week' or 'in September', convert it to an actual "
            f"YYYY-MM-DD date before calling a tool.",
        }
        response = llm_with_tools.invoke([system_note] + state["messages"])
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")
    return builder.compile()


def extract_text(message) -> str:
    if isinstance(message.content, str):
        return message.content
    return "".join(
        block["text"]
        for block in message.content
        if isinstance(block, dict) and block.get("type") == "text"
    )


# ---------------------------------------------------------------------
# Streamlit chat UI
# ---------------------------------------------------------------------
st.set_page_config(page_title="Travel Agent", page_icon="🧳")
st.title("🧳 Travel Agent")
st.caption("Ask me to find flights, hotels, or both — in plain English.")
st.caption(
    'e.g. "Find me cheap flights from Lucknow to Delhi on Aug 15" or "hotels in Goa for 3 nights starting Sept 1"'
)

graph = build_graph()

if "messages" not in st.session_state:
    st.session_state.messages = []

for role, text in st.session_state.messages:
    with st.chat_message(role):
        st.write(text)

user_input = st.chat_input("Ask about flights or hotels...")

if user_input:
    st.session_state.messages.append(("user", user_input))
    with st.chat_message("user"):
        st.write(user_input)

    graph_messages = [(role, text) for role, text in st.session_state.messages]

    with st.chat_message("assistant"):
        with st.spinner("Searching..."):
            result = graph.invoke({"messages": graph_messages})
            answer = extract_text(result["messages"][-1])
            st.write(answer)

    st.session_state.messages.append(("assistant", answer))
