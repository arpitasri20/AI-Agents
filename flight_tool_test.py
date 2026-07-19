"""
FLIGHT SEARCH TOOL — Travelpayouts API
=========================================
"""

import os
import requests

TRAVELPAYOUTS_TOKEN = os.environ.get("TRAVELPAYOUTS_API_TOKEN")


def search_flights(origin: str, destination: str, departure_date: str) -> str:
    """Search for the cheapest flights between two cities.

    Args:
        origin: 3-letter IATA code of the departure city, e.g. 'DEL'.
        destination: 3-letter IATA code of the arrival city, e.g. 'BOM'.
        departure_date: Date in YYYY-MM-DD format, e.g. '2026-09-15'.
    """
    url = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
    params = {
        "origin": origin.upper(),
        "destination": destination.upper(),
        "departure_at": departure_date,
        "sorting": "price",
        "direct": "false",
        "currency": "inr",
        "limit": 3,
        "token": TRAVELPAYOUTS_TOKEN,
    }

    response = requests.get(url, params=params)
    data = response.json()

    if not data.get("success") or not data.get("data"):
        return f"No flights found for {origin} to {destination} on {departure_date}."

    results = []
    for flight in data["data"]:
        price = flight["price"]
        airline = flight.get("airline", "Unknown airline")
        dep_time = flight.get("departure_at", "N/A")
        booking_link = "https://www.aviasales.com" + flight.get("link", "")

        results.append(
            f"₹{price} — {airline}, departs {dep_time}\nBook here: {booking_link}"
        )

    return "\n\n".join(results)


if __name__ == "__main__":
    print("=== Flight Search Test ===")
    print(search_flights("DEL", "DXB", "2026-08-20"))
