import os

from re import search
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd, timestamp, timestamp_sort

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure sql database
# uri = os.getenv("DATABASE_URL")

# if uri.startswith("postgres://"):
#     uri = uri.replace("postgres://", "postgresql://")
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

# Set global colors for table display feedback

# Stock buy or stock with positive income
GREEN = "#d6ffda"

# Stock sell or stock with negative income
RED = "#ffcccc"

# 0 income
BLANCK = "#ffffff"


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


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

    msg = False
    for row in stocks:
        # Query latest stock data
        stock = lookup(row["stock"])

        if stock["price"] == 0 and msg is False:
            flash("Couldn't Fetch Stock")
            msg = True

        # Data to be send to user
        stock_total = stock["price"] * row["shares"]
        stocks_response.append({
            "symbol": row["stock"],
            "name": stock["name"],
            "shares": row["shares"],
            "price": stock["price"],
            "total": stock_total
        })
        total += stock_total

    return render_template("index.html", cash=user["cash"], total=total, stocks=stocks_response), 200


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # User post sell via main page (index)
        if request.form.get("from_index") != None:
            symbol = request.form.get("symbol")

            # Ensure symbol was submitted
            if not symbol:
                return redirect("/"), 400
            return render_template("buy.html", symbol=symbol, shares=1)

        # Get user input, stock symbol and amount
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        # Ensure symbol was submitted
        if not symbol:
            flash("Must provide symbol")
            return render_template("buy.html", shares=1)

        # Ensure shares was submitted
        if not shares:
            flash("Must provide shares")
            return render_template("buy.html", shares=1, symbol=symbol)

        # Ensure that shares is a positive integer
        try:
            if int(shares) < 1:
                flash("Must provida valid amount of shares")
                return render_template("buy.html", shares=1, symbol=symbol)
            shares = int(shares)
        except:
            flash("Must provida valid amount of shares")
            return render_template("buy.html", shares=1, symbol=symbol)

        # Search for stock
        stock = lookup(symbol)
        cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]

        # Ensure stock was found
        if stock is None:
            flash("Must include numbers")
            return render_template("buy.html", shares=1, symbol=symbol)

        if stock["price"] == 0:
            flash("Couldn't Fetch Stock")
            return render_template("buy.html", shares=1, symbol=symbol)

        # Cost of transaction
        cost = stock["price"] * shares

        # Ensure that user can aford transaction
        if cost > cash:
            flash(f"balance is not enough to afford {shares} {stock['name']} shares")
            return render_template("buy.html", shares=1, symbol=symbol)

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
            flash("Must provide username")
            return render_template("login.html", username=username, password=password)

        # Ensure password was submitted
        if not password:
            flash("Must provide password")
            return render_template("login.html", username=username, password=password)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists
        if len(rows) != 1:
            flash("Username not found")
            return render_template("login.html", username=username, password=password)

        # Ensure password is correct
        if not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Incorrect password")
            return render_template("login.html", username=username, password=password)

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Get user input, stock symbol
        symbol = request.form.get("symbol")

        # Ensure symbol was submitted
        if not symbol:
            flash("Must provide symbol")
            return render_template("quote.html")

        # Search for stock
        result = lookup(symbol)

        # Verify that a stock was found
        if result is None:
            return render_template("quote.html", symbol=symbol, not_found=True)

        if result["price"] == 0:
            flash("Couldn't Fetch Stock")
            return render_template("quote.html", symbol=symbol, not_found=True)

        # Search for stock and return the result to user
        return render_template("quote.html", result=result)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("quote.html")


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
            flash("Must provide username")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        # Ensure password was submitted
        if not password:
            flash("Must provide password")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        # Ensure password confirmation was submitted
        if not confirmation:
            flash("Must provide password confirmation")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        # Ensure username dont already exists
        if len(db.execute("SELECT * FROM users WHERE username = ?", username)) > 0:
            flash("Username already in use")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        if password != confirmation:
            flash("Passwords must match")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        # Ensure password is secure, password contains at least 8 characters, letters, numbers and symbols
        if len(password) < 8:
            flash("Must be at least 8 characters long")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        if search("\d", password) == None:
            flash("Must include numbers")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        if search("\D", password) == None:
            flash("Must include letters")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        if search("[+,*.|()${}]", password) == None:
            flash("Must include special characters '+,*.|()${}'")
            return render_template("register.html", username=username, password=password, confirmation=confirmation)

        # Insert user in database
        id = db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, generate_password_hash(password))

        # Remember which user has logged in
        session["user_id"] = id
        # session["password_respond"] = False

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    stocks_db = db.execute("SELECT stock FROM stocks WHERE user_id=?", session["user_id"])
    stocks = []

    for row in stocks_db:
        stocks.append(row["stock"])

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Get user input, stock symbol and amount
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        # Ensure symbol was submitted
        if not symbol:
            flash("Must provide a stock symbol")
            return render_template("sell.html", shares=1, symbols=stocks)

        if symbol not in stocks:
            flash("Must provide a stock you have bought")
            return render_template("sell.html", shares=1, symbols=stocks)

        shares_db = db.execute("SELECT shares FROM stocks WHERE user_id=? AND stock=?", session["user_id"], symbol)[0]["shares"]

        # User post sell via main page (index)
        if request.form.get("from_index") != None:
            return render_template("sell.html", selected=symbol, shares=shares_db, symbols=stocks)

        # Ensure shares was submitted
        if not shares:
            flash("Must provide shares amount")
            return render_template("sell.html", shares=1, symbols=stocks)

        # Ensure that shares is a positive integer
        try:
            if int(shares) < 1:
                flash("Must provide a valid shares amount")
                return render_template("sell.html", shares=1, symbols=stocks)
            shares = int(shares)
        except:
            flash("Must provide a valid shares amount")
            return render_template("sell.html", shares=1, symbols=stocks)

        if  shares > shares_db:
            flash("Must provide an amount of shares you have bought")
            return render_template("sell.html", shares=1, symbols=stocks)

        # Search for stock
        stock = lookup(symbol)

        # Ensure stock was found
        if stock is None:
            flash("Must provide a valid stock name")
            return render_template("sell.html", shares=1, symbols=stocks)

        if stock["price"] == 0:
            flash("Couldn't Fetch Stock")
            return render_template("sell.html", shares=1, symbols=stocks)

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
        return render_template("sell.html", shares=1, symbols=stocks)


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

        if row["shares"] < 0:
            revenue = (row["price"]*row["shares"]*-1) - row["buy_price"]

            if round(revenue, 1) < 0:
                revenue_color = RED
            elif round(revenue, 1) > 0:
                revenue_color = GREEN
            else:
                revenue_color = BLANCK

            totalT += revenue
            transactions.append({
                "symbol":row["symbol"],
                "shares":row["shares"],
                "buy_price":row["buy_price"]/(row["shares"]*-1),
                "price":row["price"],
                "percentage":round((row["price"]/(row["buy_price"]/(row["shares"]*-1)))*100 - 100, 2),
                "revenue":revenue,
                "transacted":row["timestamp"],
                "color":RED,
                "r-color": revenue_color
            })
            continue

        if row["analisys"] == 0:
            continue

        stock = stock_data[row["symbol"]] = lookup(row["symbol"])

        if stock["price"] == 0:
            flash("Couldn't Fetch Stock")
            return redirect("/")

        revenue = (stock["price"] - row["price"])*(row["shares"] - row["selled"])

        if round(revenue, 1) < 0:
            revenue_color = RED
        elif round(revenue, 1) > 0:
            revenue_color = GREEN
        else:
            revenue_color = BLANCK

        totalT += revenue
        transactions.append({
            "symbol": row["symbol"],
            "shares": (row["shares"] - row["selled"]),
            "buy_price": row["price"],
            "price": stock["price"],
            "percentage": round((stock["price"]/row["price"])*100 - 100, 2),
            "revenue": revenue,
            "transacted": row["timestamp"],
            "color": GREEN,
            "r-color": revenue_color
        })

    # Format user stock data and analisys
    totalStckBuyPrice = 0
    totalStckRevenue = 0

    for row in stocks_db:
        if row["stock"] not in stock_data.keys():
            stock = lookup(row["stock"])

            if stock["price"] == 0:
                flash("Couldn't Fetch Stock")
                return redirect("/")
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
            "symbol": row["stock"],
            "shares": row["shares"],
            "buy_price": row["buy_price"]/row["shares"],
            "price": stock["price"],
            "percentage": round(((stock["price"]*row["shares"])/row["buy_price"])*100 - 100, 2),
            "revenue": revenue,
            "color": color
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
        elif action == "recovery":
            questions = []
            answers = []

            # Iterate trought user input
            for i in range(1, 6):
                question = request.form.get(f"question{i}")
                answer = request.form.get(f"answer{i}")

                # Save valid questions and answers
                if question != None and question != "":
                    questions.append(question)
                if answer != None and answer != "":
                    answers.append(answer)

            # Ensure at least 1 question was submited
            if len(questions) < 1:
                flash("must provide at least one question")
                return render_template("security.html")

            if len(questions) != len(answers):
                flash("must provide same number of questions and answers")
                return render_template("security.html", pairs=len(questions), questions=questions, answers=answers)

            # Delete previous data in database
            db.execute("DELETE FROM recovery WHERE user_id=?", session["user_id"])

            # Insert new data
            for i in range(len(questions)):
                db.execute("INSERT INTO recovery (user_id, question, answer) VALUES (?,?,?)", session["user_id"], questions[i], answers[i])

            return redirect("/")
        else:
            return apology("Unvalid action", 400)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("security.html")


@app.route("/recovery", methods=["GET", "POST"])
def recovery():
    """password recovery"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        action = request.form.get("action")

        if action == "search":
            username = request.form.get("username")

            # Ensure username was submitted
            if not username:
                flash("must provide a username")
                return render_template("recovery.html", action="search")

            row = db.execute("SELECT id FROM users WHERE username=?", username)

            # Ensure user is found
            if len(row) != 1:
                flash("username not found")
                return render_template("recovery.html", action="search")

            pairs = db.execute("SELECT question, answer FROM recovery WHERE user_id=?", row[0]["id"])

            if len(pairs) < 1:
                flash("password recovery not setup")
                return render_template("recovery.html", action="search")

            return render_template("recovery.html", action="submit", id=row[0]["id"], pairs=pairs)

        elif action == "submit":
            id = request.form.get("id")

            if not id:
                flash("unvalid request")
                return render_template("recovery.html", action="search")

            pairs = db.execute("SELECT question, answer FROM recovery WHERE user_id=?", id)

            for a in pairs:
                answer = request.form.get(f"answer{pairs.index(a)+1}")

                if not answer:
                    flash(f"must provide answer {pairs.index(a)+1}")
                    return render_template("recovery.html", action="submit", id=id, pairs=pairs)

                if answer != a["answer"]:
                    flash(f"answer {pairs.index(a)+1} incorrect")
                    return render_template("recovery.html", action="submit", id=id, pairs=pairs)

            return render_template("recovery.html", action="change", id=id)

        elif action == "change":
            # Get user input, stock symbol and amount
            id = request.form.get("id")
            new_password = request.form.get("new_password")
            confirmation = request.form.get("confirmation")

            # Ensure confirmation was submitted
            if not id:
                flash("unvalid request")
                return render_template("recovery.html", action="change", id=id)

            # Ensure confirmation was submitted
            if not new_password:
                flash("must provide new password")
                return render_template("recovery.html", action="change", id=id)

            # Ensure confirmation was submitted
            if not confirmation:
                flash("must provide new password confirmation")
                return render_template("recovery.html", action="change", id=id)

            # Ensure new password and confirmation match
            if new_password != confirmation:
                flash("new password and confirmation must match")
                return render_template("recovery.html", action="change", id=id)

            # Ensure password is secure, password contains at least 8 characters, letters, numbers and symbols

            if len(new_password) < 8:
                flash("Must be at least 8 characters long")
                return render_template("recovery.html", action="change", id=id)

            if search("\d", new_password) == None:
                flash("Must include numbers")
                return render_template("recovery.html", action="change", id=id)

            if search("\D", new_password) == None:
                flash("Must include letters")
                return render_template("recovery.html", action="change", id=id)

            if search("[+,*.|()${}]", new_password) == None:
                flash("Must include special characters '+,*.|()${}'")
                return render_template("recovery.html", action="change", id=id)

            # Update password hash in database
            db.execute("UPDATE users SET hash=? WHERE id=?", generate_password_hash(new_password), id)

            flash("password changed")
            return redirect("/")
        else:
            return apology("Unvalid action", 400)

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("recovery.html", action="search")


@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Get user input
        account = request.form.get("account")
        password = request.form.get("password")

        # Get user info
        user = db.execute("SELECT cash, hash FROM users WHERE id = ?", session["user_id"])[0]

        if not password:
            flash("must provide an account to transfer the balance and stocks")
            return render_template("funds.html", cash=user["cash"], _account=account, _password=password)

        if not account:
            flash("must provide password")
            return render_template("funds.html", cash=user["cash"], _account=account, _password=password)

        # Ensure password is correct
        if not check_password_hash(user["hash"], password):
            flash("invalid password")
            return render_template("funds.html", cash=user["cash"], _account=account, _password=password)

        total_funds = user["cash"]

        # Get user stocks
        stocks_db = db.execute("SELECT stock, shares FROM stocks WHERE user_id=?", session["user_id"])

        # Sell each stock
        for stock in stocks_db:
            stock = lookup(stock["stock"])

            if stock["price"] == 0:
                flash("Couldn't Fetch Stock")
                return render_template("funds.html", cash=user["cash"], _account=account, _password=password)

            total_funds += stock["price"] * stock["shares"]


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

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return redirect("/funds")