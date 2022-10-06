import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps
from datetime import datetime


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/1.1.x/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        url = f"https://cloud.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}"
        response = requests.get(url)

        response.raise_for_status()
    except requests.RequestException as e:
        if str(e)[:3] == "402":
            return {
            "name": "Couldn't Fetch",
            "price": 0,
            "symbol": symbol
        }
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def timestamp():
    """Return the current date and time formatted"""
    date = datetime.now()
    return f"{date.year}-{date.month}-{date.day} {date.hour}:{date.minute}:{date.second}"

def timestamp_sort(elements: list, desc=False):
    def calc_time(datetime:list):
        return (int(datetime[0])*3214.08) + (int(datetime[1])*267.84) + (int(datetime[2])*8.64) + (int(datetime[3])*0.36) + (int(datetime[4])*0.006) + (int(datetime[5])*0.0001)

    for elem in elements:
        print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        print(elem["timestamp"])
        print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

        elem["timestamp"] = elem["timestamp"].replace(" ", "-").replace(":", "-").split("-")

    count = 1
    while(count > 0):
        count = 0
        for i in range(len(elements)-1):
            if desc:
                if calc_time(elements[i]["timestamp"]) < calc_time(elements[i+1]["timestamp"]):
                    count += 1
                    temp = elements[i]["timestamp"]
                    elements[i]["timestamp"] = elements[i+1]["timestamp"]
                    elements[i+1]["timestamp"] = temp
            else:
                if calc_time(elements[i]["timestamp"]) > calc_time(elements[i+1]["timestamp"]):
                    count += 1
                    temp = elements[i]["timestamp"]
                    elements[i]["timestamp"] = elements[i+1]["timestamp"]
                    elements[i+1]["timestamp"] = temp

    for elem in elements:
        elem["timestamp"] = "#".join(elem["timestamp"]).replace("#", "-", 2).replace("#", " ", 1).replace("#", ":")

    return elements
