import os
import re
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps
from datetime import datetime
from dotenv import load_dotenv

SUCCESFULL=1
CACHED=2
FAILED=3
NOTFOUND=4

price_cache = {}
company_names = {}

load_dotenv()
APISTOCKSKEY = os.getenv("APISTOCKS_KEY")
ALPHAKEY = os.getenv("ALPHA_KEY")

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


def fetchCompany(search, type):
    result = {
        "result":search,
        "search":search,
        "status":SUCCESFULL
    }

    try:
        if search in company_names.keys() or search in company_names.values():
            if type=="symbol":
                result["result"] = company_names[search]
            else:
                for key in company_names.keys():
                    if company_names[key] == search:
                        result["result"] = key
                        break
            result["status"] = CACHED
        
        url = f'https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={search}&apikey={ALPHAKEY}'
        response = requests.get(url)

        found = False
        if len(response.json()["bestMatches"]) > 0:
            for match in response.json()["bestMatches"]:
                if match["4. region"] == "United States":
                    if type=="symbol":
                        company_names[search] = match["2. name"]
                    found = True
                    result["result"] = match["2. name" if type=="symbol" else "1. symbol"]
                    break

        if not found:
            result["status"] = NOTFOUND
    except:
        result["status"] = FAILED
    
    return result


def lookup(symbol):
    """Look up quote for symbol."""

    result = {
        "name":symbol,
        "symbol":symbol,
        "pricetxt":"",
        "status":SUCCESFULL
    }

    result["name"] = fetchCompany(symbol, "symbol")["result"]

    try:
        url = "https://apistocks.p.rapidapi.com/intraday"

        querystring = {"symbol":symbol,"interval":"1min","maxreturn":"1"}

        headers = {
        	"content-type": "application/octet-stream",
        	"X-RapidAPI-Key": APISTOCKSKEY,
        	"X-RapidAPI-Host": "apistocks.p.rapidapi.com"
        }

        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        
        if len(response.json()["Results"]) > 0:
            result["price"] = price_cache[symbol] = float(response.json()["Results"][0]["Close"])
        else:
            result["price"] = None
            result["status"] = NOTFOUND
            result["pricetxt"] = "Not found"
    except Exception as e:
        print(e)
        if symbol in price_cache.keys():
            result["price"] = price_cache[symbol]
            result["pricetxt"] = "(Outdated)"
            result["status"] = CACHED
        else:
            result["price"] = 0
            result["pricetxt"] = "Couldn't fetch"
            result["status"] = FAILED

    return result

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