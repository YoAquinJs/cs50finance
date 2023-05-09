import os

from re import search
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash
from dotenv import load_dotenv

from helpers import apology, login_required, lookup, usd, timestamp, timestamp_sort, fetchCompany

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

app.secret_key = "test"

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

load_dotenv()
if not os.getenv("APISTOCKS_KEY"):# Make sure API key is set
    raise RuntimeError("Stock api key not set")

# Stock buy or stock with positive income
GREEN = "#d6ffda"
# Stock sell or stock with negative income
RED = "#ffcccc"
# 0 income
BLANCK = "#ffffff"

# Lookup response intern status
SUCCESFULL=1
CACHED=2
FAILED=3
NOTFOUND=4

"""
TODO
-delete page
-analysis revenue failing (in stocks maybe also in transfers)
-security questions failing (not working and cant delete sec question)
-host in pythhon anywhere
"""

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not username:
            flash("must provide username")
            return render_template("login.html")

        # Ensure password was submitted
        if not password:
            flash("must provide password")
            return render_template("login.html")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists
        if len(rows) != 1:
            flash("username not found")
            return render_template("login.html")

        # Ensure password is correct
        if not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("incorrect password")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
    

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Get user input, username, password and confirmation
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure username was submitted
        if not username:
            flash("must provide username")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        # Ensure password was submitted
        if not password:
            flash("must provide password")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        # Ensure password confirmation was submitted
        if not confirmation:
            flash("must provide password confirmation")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        # Ensure username dont already exists
        if len(db.execute("SELECT * FROM users WHERE username = ?", username)) > 0:
            return apology("username already in use", 403)

        if password != confirmation:
            flash("confirmation not matching password")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        # Ensure password is secure, password contains at least 8 characters, letters, numbers and symbols
        if len(password) < 8:
            flash("password must be at least 8 characters long")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        if search("\d", password) == None:
            flash("password must include numbers")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        if search("\D", password) == None:
            flash("password must include letters")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        if search("[+,*.|()${}]", password) == None:
            flash("password must include special characters '+,*.|()${}'")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        # Insert user in database
        id = db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, generate_password_hash(password))

        # Remember which user has logged in
        session["user_id"] = id

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html"), 200
    

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # Get user stocks
    stocks = db.execute("SELECT stock, shares FROM stocks WHERE user_id=?", session["user_id"])

    # Get user cash
    user = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]

    stocks_response = []
    total = user["cash"]
    for row in stocks:
        # Query latest stock data
        stock = lookup(row["stock"])

        # Data to be send to user
        stock_total = stock["price"] * row["shares"]
        stocks_response.append({
            "symbol": row["stock"],
            "name": stock["name"],
            "shares": row["shares"],
            "price": stock["price"],
            "pricetxt": stock["pricetxt"],
            "total": stock_total
        })
        total += stock_total

    return render_template("index.html", cash=user["cash"], total=total, stocks=stocks_response), 200


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Get user input, stock symbol
        search = request.form.get("search")
        type = request.form.get("type")
        # Ensure symbol was submitted
        if not search:
            flash("must provide stock symbol")
            return render_template("quote.html")

        if not type:
            return apology("Invalid action", 403)
        
        # Search for stock
        companyResult = fetchCompany(search, type)
        # Verify that a stock was found
        if companyResult["status"] == FAILED or companyResult["status"] == NOTFOUND:
            return render_template("quote.html", search=search, not_found=True)

        result = lookup(search if type=="symbol" else companyResult["result"])
        # Search for stock and return the result to user
        return render_template("quote.html", result=result)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html"), 200
    

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # User post sell via main page (index)
        symbol = request.form.get("symbol")
        if request.form.get("from_index") != None:
            # Ensure symbol was submitted
            if not symbol:
                return redirect("/"), 400
            return render_template("buy.html", symbol=symbol, shares=1)

        # Get user input, stock symbol and amount
        shares = request.form.get("shares")

        # Ensure symbol was submitted
        if not symbol:
            flash("must provide stock symbol")
            return render_template("buy.html", symbol=symbol, shares=shares)

        # Ensure shares was submitted
        if not shares:
            flash("must provide shares amount")
            return render_template("buy.html", symbol=symbol, shares=shares)

        # Ensure that shares is a positive integer
        try:
            if int(shares) < 1:
                flash("must provide a valid shares amount")
                return render_template("buy.html", symbol=symbol, shares=shares)
            shares = int(shares)
        except:
            flash("must provide a valid shares amount")
            return render_template("buy.html", symbol=symbol, shares=shares)

        # Search for stock
        stock = lookup(symbol)
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]

        # Ensure stock was found
        if stock["pricetxt"] == "Not found":
            flash("must provide a valid stock symbol")
            return render_template("buy.html", symbol=symbol, shares=shares)

        if stock["status"] != SUCCESFULL:
            return apology("Couldn't fetch latests price", 400)
        # Cost of transaction
        cost = stock["price"] * shares

        # Ensure that user can aford transaction
        if cost > cash:
            return apology(f"balance is not enough to afford {shares} {stock['name']} shares", 403)

        # Change user balance
        db.execute("UPDATE users SET cash=? WHERE id=?", cash - cost, session["user_id"])

        #change user stocks
        stock_db = db.execute("SELECT shares FROM stocks WHERE user_id=? AND stock=?", session["user_id"], stock["symbol"])
        if len(stock_db) != 1:
            db.execute("INSERT INTO stocks (user_id, stock, shares) VALUES (?,?,?)", session["user_id"], stock["symbol"], shares)
        else:
            db.execute("UPDATE stocks SET shares=? WHERE user_id=? AND stock=?", shares + stock_db[0]["shares"], session["user_id"], stock["symbol"])

        # Save transaction in database
        db.execute("INSERT INTO transactions (user_id, timestamp, symbol, shares, price) VALUES (?,?,?,?,?)", \
            session["user_id"], timestamp(), stock["symbol"], shares, stock["price"])

        flash("Stock bought!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("buy.html", shares=1), 200


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    stocks_db = db.execute("SELECT stock FROM stocks WHERE user_id=?", session["user_id"])
    stocks = [row["stock"] for row in stocks_db]

    for row in stocks_db:
        stocks.append(row["stock"])

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Get user input, stock symbol and amount
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        # Ensure symbol was submitted
        if not symbol:
            flash("must provide stock symbol")
            return render_template("sell.html", selected=symbol, shares=shares_db, symbols=stocks)

        if symbol not in stocks:
            flash("must provide a stock you own")
            return render_template("sell.html", selected=symbol, shares=shares_db, symbols=stocks)

        shares_db = db.execute("SELECT shares FROM stocks WHERE user_id=? AND stock=?", session["user_id"], symbol)[0]["shares"]

        # User post sell via main page (index)
        if request.form.get("from_index") != None:
            return render_template("sell.html", selected=symbol, shares=shares_db, symbols=stocks)

        # Ensure shares was submitted
        if not shares:
            flash("must provide a shares amount")
            return render_template("sell.html", selected=symbol, shares=shares_db, symbols=stocks)

        # Ensure that shares is a positive integer
        try:
            if int(shares) < 1:
                flash("must provide a valid shars amount")
                return render_template("sell.html", selected=symbol, shares=shares_db, symbols=stocks)
            shares = int(shares)
        except:
            flash("must provide a valid shars amount")
            return render_template("sell.html", selected=symbol, shares=shares_db, symbols=stocks)

        if  shares > shares_db:
            return apology("must provide an amount of shares you own", 403)

        # Search for stock
        stock = lookup(symbol)

        # Ensure stock was found
        if stock["pricetxt"] == "Not found":
            return apology("must provide a valid stock symbol", 404)

        if stock["status"] != SUCCESFULL:
            return apology("Couldn't fetch latests price", 400)

        # Calculate transaction revenue
        revenue = stock["price"] * shares

        # Change user balance
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
        db.execute("UPDATE users SET cash=? WHERE id=?", cash + revenue, session["user_id"])

        # Change user stocks
        if shares_db - shares == 0:
            db.execute("DELETE FROM stocks WHERE user_id=? AND stock=?", session["user_id"], symbol)
        else:
            db.execute("UPDATE stocks SET shares=? WHERE user_id=? AND stock=?", shares_db - shares, session["user_id"], symbol)

        buys = timestamp_sort(db.execute("SELECT id, shares, selled, price, timestamp FROM transactions WHERE shares > 0 AND analisys=1 AND symbol=? AND user_id=?", \
                              symbol, session["user_id"]))
        sharesBought = 0
        rows = 1
        buy_price = 0

        for row in buys:
            sharesBought += row["shares"] - row["selled"]

            if sharesBought == shares:
                for i in range(rows):
                    db.execute("UPDATE transactions SET analisys=0 WHERE user_id=? AND id=?", session["user_id"], buys[i]["id"])

                buy_price += (row["shares"] - row["selled"]) * row["price"]
                break
            elif sharesBought > shares:
                for i in range(rows-1):
                    db.execute("UPDATE transactions SET analisys=0 WHERE user_id=? AND id=?", session["user_id"], buys[i]["id"])

                selled = (shares - sharesBought + row["shares"] - row["selled"])
                buy_price += selled * row["price"]
                db.execute("UPDATE transactions SET selled=? WHERE user_id=? AND id=?", row["selled"] + selled, session["user_id"], row["id"])

                break

            rows += 1
            buy_price += (row["shares"] - row["selled"]) * row["price"]

        # Save transaction in database
        db.execute("INSERT INTO transactions (user_id, timestamp, symbol, shares, price, buy_price) VALUES (?,?,?,?,?,?)", \
            session["user_id"], timestamp(), symbol, shares*-1, stock["price"], buy_price)

        flash("Stock Sold!")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("sell.html", shares=1, symbols=stocks), 200
    

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = timestamp_sort(db.execute("SELECT timestamp, symbol, shares, price FROM transactions WHERE user_id=?", session["user_id"]))
    funds = timestamp_sort(db.execute("SELECT timestamp, amount, alias FROM funds WHERE user_id=?", session["user_id"]))

    for tra in transactions:
        if tra["shares"] < 1:
            tra["color"] = RED
        else:
            tra["color"] = GREEN

    for tra in funds:
        if tra["amount"] < 1:
            tra["color"] = RED
        else:
            tra["color"] = GREEN

    return render_template("history.html", transactions=transactions, funds=funds), 200


@app.route("/funds", methods=["GET", "POST"])
@login_required
def funds():
    """Configure cash and funds"""

    # Get session user information
    user = db.execute("SELECT cash, hash FROM users WHERE id = ?", session["user_id"])[0]

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        action = request.form.get("action")
        account = request.form.get("account")
        amount = request.form.get("amount")
        password = request.form.get("password")
        alias = request.form.get("alias")

        if not alias:
            alias = ""

        if not action:
            flash("must provide either transfer or retire")
            return render_template("funds.html", cash=user["cash"], action=action, account=account, amount=amount, password=password, alias=alias)

        if not account:
            flash("must provide an account")
            return render_template("funds.html", cash=user["cash"], action=action, account=account, amount=amount, password=password, alias=alias)

        if not amount:
            flash(f"must provide an amount to {action}")
            return render_template("funds.html", cash=user["cash"], action=action, account=account, amount=amount, password=password, alias=alias)

        if not password:
            flash("must provide a password")
            return render_template("funds.html", cash=user["cash"], action=action, account=account, amount=amount, password=password, alias=alias)

        # Ensure password is correct
        if not check_password_hash(user["hash"], password):
            flash("invalid password")
            return render_template("funds.html", cash=user["cash"], action=action, account=account, amount=amount, password=password, alias=alias)

        # Ensure that amount is a positive number
        try:
            if float(amount) <= 0:
                flash("must provide a valid amount")
                return render_template("funds.html", cash=user["cash"], action=action, account=account, amount=amount, password=password, alias=alias)
            amount = float(amount)
        except:
            flash("must provide a valid amount")
            return render_template("funds.html", cash=user["cash"], action=action, account=account, amount=amount, password=password, alias=alias)

        # Simulate account checking

        if action.lower() == "transfer":
            # Transfer money from account to balance

            # Change user balance
            db.execute("UPDATE users SET cash=? WHERE id=?", user["cash"] + amount, session["user_id"])

            # Save transfer log in database
            db.execute("INSERT INTO funds (user_id, amount, timestamp, alias) VALUES (?,?,?,?)", session["user_id"], amount, timestamp(), alias)

            return render_template("funds.html", cash=user["cash"]+amount)
        elif action.lower() == "retire":
            if amount > user["cash"]:
                flash("must provide an amount of cash you own")
                return render_template("funds.html", cash=user["cash"], action=action, account=account, amount=amount, password=password, alias=alias)

            # Transfer money from balance to account

            # Change user balance
            db.execute("UPDATE users SET cash=? WHERE id=?", user["cash"] - amount, session["user_id"])

            # Save transfer log in database
            db.execute("INSERT INTO funds (user_id, amount, timestamp, alias) VALUES (?,?,?,?)", session["user_id"], amount*-1, timestamp(), alias)
            return render_template("funds.html", cash=user["cash"]-amount)
        else:
            flash("must provide a valid action, transfer or retire")
            return render_template("funds.html", cash=user["cash"], action=action, account=account, amount=amount, password=password, alias=alias), 200

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("funds.html", cash=user["cash"])


@app.route("/analisys", methods=["GET", "POST"])
@login_required
def analisys():
    """Stock analisys"""

    transactions=[]
    stocks=[]
    stock_data={}

    # Get user transactions
    transactions_db = timestamp_sort(db.execute("SELECT timestamp, symbol, shares, price, buy_price, analisys, selled FROM transactions WHERE user_id=?", session["user_id"]))

    # Get user stocks
    stocks_db = db.execute("SELECT stock, shares FROM stocks WHERE user_id=?", session["user_id"])

    # Format user trading data and analisys
    totalT = 0
    for row in transactions_db:
        for stck in stocks_db:
            if stck["stock"] == row["symbol"]:
                if "buy_price" not in stck.keys():
                    stck["buy_price"] = row["price"]*(row["shares"])
                else:
                    stck["buy_price"] += row["price"]*(row["shares"])

                if row["buy_price"] < 0:
                    row["buy_price"] = 0
        revcolor = GREEN
        if row["shares"] < 0:
            revenue = (row["price"]*row["shares"]*-1) - row["buy_price"]
            if revenue < 0:
                revcolor = RED
            totalT += (row["price"]*row["shares"]*-1) - row["buy_price"]
            transactions.append({
                "symbol":row["symbol"],
                "shares":row["shares"],
                "buy_price":row["buy_price"]/(row["shares"]*-1),
                "price":row["price"],
                "percentage":round((row["price"]/(row["buy_price"]/(row["shares"]*-1)))*100 - 100, 2),
                "revenue":revenue,
                "transacted":row["timestamp"],
                "type":"(sell)",
                "revcolor":revcolor
            })
            continue

        if row["analisys"] == 0:
            continue

        stock = stock_data[row["symbol"]] = lookup(row["symbol"])
        if stock["price"] is None:
            continue

        revenue = (stock["price"] - row["price"])*(row["shares"] - row["selled"])
        if revenue < 0:
            revcolor = RED
        totalT += (stock["price"] - row["price"])*(row["shares"] - row["selled"])
        transactions.append({
            "symbol":row["symbol"],
            "shares":(row["shares"] - row["selled"]),
            "buy_price":row["price"],
            "price":stock["price"],
            "pricetxt":stock["pricetxt"],
            "percentage":round((stock["price"]/row["price"])*100 - 100, 2),
            "revenue":revenue,
            "transacted":row["timestamp"],
            "type":"(buy)",
            "revcolor":revcolor
        })

    # Format user stock data and analisys
    totalStckBuyPrice = 0
    totalStckRevenue = 0

    for row in stocks_db:
        if row["stock"] not in stock_data.keys():
            stock = lookup(row["stock"])
        else:
            stock = stock_data[row["stock"]]

        revenue = (stock["price"]*row["shares"]) - row["buy_price"]
        totalStckBuyPrice += row["buy_price"]
        totalStckRevenue += revenue

        if round(revenue, 1) < 0:
            color = RED
        elif round(revenue, 1) > 0:
            color = GREEN
        else:
            color = BLANCK

        stocks.append({
            "symbol":row["stock"],
            "shares":row["shares"],
            "buy_price":row["buy_price"]/row["shares"],
            "price":stock["price"],
            "percentage":round(((stock["price"]*row["shares"])/row["buy_price"])*100 - 100, 2),
            "revenue":revenue,
            "color":color
        })

    if totalStckBuyPrice > 0:
        if round(totalStckRevenue, 1) < 0:
            color = RED
        elif round(totalStckRevenue, 1) > 0:
            color = GREEN
        else:
            color = BLANCK
        totalS = {
            "buy_price":totalStckBuyPrice,
            "price":totalStckBuyPrice + totalStckRevenue,
            "percentage":round(((totalStckBuyPrice + totalStckRevenue)/totalStckBuyPrice)*100 - 100, 2),
            "revenue":totalStckRevenue,
            "color":color
        }
    else:
        totalS = None

    return render_template("analisys.html", transactions=transactions, stocks=stocks, totalS=totalS, totalT=totalT)


@app.route("/security", methods=["GET", "POST"])
@login_required
def security():
    """Confiure app security fetuares"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        action = request.form.get("action")
        password = request.form.get("password")
        print(action)
        # Ensure password was submitted
        if not password:
            flash("must provide password")
            return render_template("security.html")

        hash = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])[0]["hash"]

        # Ensure password is correct
        if not check_password_hash(hash, password):
            flash("invalid password")
            return render_template("security.html")

        if action == "password":
            # Get user input, stock symbol and amount
            new_password = request.form.get("new_password")
            confirmation = request.form.get("confirmation")

            # Ensure confirmation was submitted
            if not confirmation:
                flash("must provide new password confirmation")
                return render_template("security.html")

            # Ensure new password and confirmation match
            if new_password != confirmation:
                flash("new password and confirmation must match")
                return render_template("security.html")

            # Ensure password is secure, password contains at least 8 characters, letters, numbers and symbols

            if len(new_password) < 8:
                flash("Must be at least 8 characters long")
                return render_template("security.html")

            if search("\d", new_password) == None:
                flash("Must include numbers")
                return render_template("security.html")

            if search("\D", new_password) == None:
                flash("Must include letters")
                return render_template("security.html")

            if search("[+,*.|()${}]", new_password) == None:
                flash("Must include special characters '+,*.|()${}'")
                return render_template("security.html")

            # Update password hash in database
            db.execute("UPDATE users SET hash=? WHERE id=?", generate_password_hash(new_password), session["user_id"])

            return logout()
        elif action == "delete":
            # Get user input
            account = request.form.get("account")
            password = request.form.get("password")

            # Get user info
            user = db.execute("SELECT cash, hash FROM users WHERE id = ?", session["user_id"])[0]

            if not password:
                flash("must provide password")
                return render_template("delete.html")

            if not account:
                flash("must provide an account to transfer the balance and stocks")
                return render_template("delete.html")

            # Ensure password is correct
            if not check_password_hash(user["hash"], password):
                flash("invalid password")
                return render_template("delete.html")

            total_funds = user["cash"]

            # Get user stocks
            stocks_db = db.execute("SELECT stock, shares FROM stocks WHERE user_id=?", session["user_id"])

            # Sell each stock
            for stock in stocks_db:
                _stock = lookup(stock["stock"])
                if _stock["status"] != SUCCESFULL:
                    return apology("Couldn't fetch latests price", 400)

                total_funds += _stock["price"] * stock["shares"]

            # Transfer money to account

            # Delete user information in database
            db.execute("DELETE FROM funds WHERE user_id=?", session["user_id"])
            db.execute("DELETE FROM recovery WHERE user_id=?", session["user_id"])
            db.execute("DELETE FROM stocks WHERE user_id=?", session["user_id"])
            db.execute("DELETE FROM transactions WHERE user_id=?", session["user_id"])
            db.execute("DELETE FROM users WHERE id=?", session["user_id"])

            session.clear()

            flash(f"${total_funds} transfered, account deleted")
            return redirect("/register")
        else:
            return apology("unvalid action", 400)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("security.html")

    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
