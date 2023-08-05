import os
from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

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
    # extracting details for the index page
    portfolio_cash = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])[0]["cash"]
    stock_index = db.execute("SELECT stock,no_of_shares,price,P.total,cash FROM users U,portfolio P WHERE U.username = P.username ")
    final_cash  = portfolio_cash

    # calculating the total cash
    for i in range(len(stock_index)) :
        final_cash += stock_index[i]["no_of_shares"] * stock_index[i]["price"]
    return render_template("index.html", portfolio = stock_index,cash = portfolio_cash,grand_total = final_cash)

# buy working
@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    #handling exceptions here if something is missing in the post method
    try :
        if request.method == "POST" :

            symbol = request.form.get("symbol")
            stock = lookup(symbol)
            no_of_shares = int(request.form.get("no_of_shares"))
            # checkign whether the name is vaild or not
            if stock is None :
                return apology("Stock Not Found",404)
            # checkig for the number of shares to buy
            elif   no_of_shares < 0 :
                return apology("Enter a Valid No", 403)
            # checking if there is enough fund or not in the account
            else :
                # determining if there is enough cash in the account
                print(db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"]))
                cash_in_account = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
                total_amount_required = float(stock["price"]) * no_of_shares

                if total_amount_required > cash_in_account :
                    return apology("Not enough fund in the Account ")

                # updating in the portfolio table the stock
                else  :
                    cash_in_account -= total_amount_required
                    # helper function that is does the buying of the stock.
                    database(stock["symbol"],no_of_shares,total_amount_required,stock["name"])
                    db.execute("UPDATE  users SET cash = ? WHERE id = ? ", cash_in_account, session["user_id"])
                    return redirect("/")

        # if the request method is get then rendering the page
        elif request.method == "GET" :
            return render_template("buy.html")

    except :
        return apology("error 405 Missing entries")

# a helper function for the updating the portfolio
def database(stock_name,no_of_shares,amount,symbol) :
    username = db.execute("SELECT username FROM users where id = ?",session["user_id"])[0]["username"]
    # checking if the stock is already in the table or not
    if db.execute("SELECT * FROM portfolio WHERE stock = ? AND username = ? ", stock_name,username) == [] :
        # inserting data into portfolio and history if its a new transaction
        db.execute("INSERT into portfolio Values (?,?,?,?,?)",username,stock_name,no_of_shares,(amount/no_of_shares),amount)
        db.execute("INSERT INTO history VALUES (?,?,?,?,?,?)", username,stock_name,symbol,no_of_shares,(amount/no_of_shares),datetime.now())

    # if it is not already in the table then updating the details in the portfolio
    else :

        total_shares = no_of_shares + db.execute("SELECT no_of_shares FROM portfolio WHERE username = ? AND stock = ?", username,stock_name)[0]["no_of_shares"]
        average_price = (db.execute("SELECT total FROM portfolio WHERE username = ? AND Stock = ?", username,stock_name)[0]["total"] + amount) / total_shares
        total = (average_price * no_of_shares)
        # updating the portfolio and history
        db.execute("UPDATE  portfolio SET no_of_shares  = ? ,price = ?,total = ? ",total_shares,average_price,total)
        db.execute("INSERT INTO history VALUES (?,?,?,?,?,?)", username,stock_name,symbol,no_of_shares,(amount/no_of_shares),datetime.now())

    flash("Bought the Share",200)
    return redirect("/")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # showing the history by accessing the username and
    username = db.execute("SELECT * FROM users WHERE id = ?",session["user_id"])[0]["username"]
    data = db.execute("SELECT * FROM history WHERE username = ?",username)
    if data is None:
        return apology("TODO")
    for row_data in data :
        print(row_data["price"])
    return render_template("history.html",data = data)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        global username
        username =  request.form.get("username")
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

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
    if request.method == "GET" :
        return render_template("quote.html")

    elif request.method == "POST" :

        stock_symbol = request.form.get("symbol")
        stocks = lookup(stock_symbol)  # using the provided api function to get the stock price

        if stocks is None :
           return apology("Sorry, But the symbol that you provided is invalid! ",404)
        else :
            # return render_template("quoted.html", stock_data = stocks)
            return render_template("quoted.html",stock_data = stocks)
    return apology("Invalid Request Method! ", 500)

# register is working now
@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    session.clear()
    """ following up the login function to make a register function , validating the inputs and """
    # if any of the details is missing then handling those
    try :
        if request.method == "POST" :
            if not request.form.get("username") :
                return apology("must provide a username", 403)

            # if anything is missing in the
            elif not request.form.get("password") :
                return apology("must provide a password", 403)
            rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

            # if the username is already acquired the not entering in the database -- handling this error
            if len(rows) != 0  :
                flash('please choose a unique username', 'error')
                return redirect('login')

            # confirming passwords and hashing them and saving in the database
            else :
                password = request.form.get("password")
                confirm_password = request.form.get("password")

                if password == confirm_password :

                    # getting hash of password and the storing it to avoid any kind of security issues
                    hash = generate_password_hash(password)
                    username  = request.form.get("username")
                    cash = 10000
                    db.execute("INSERT into users (username,hash,cash) VALUES(?,?,?)",username,hash,cash)
                    return redirect("/login")
        else :
            return render_template("register.html")
    except :
        return apology("Missing arguments ")

     # return apology("incorrect method", 500)  # 500 for internal server error.


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # showing all the stocks as an option in the page instead of whole table format
    username = (db.execute("SELECT * from users WHERE id = ?", session["user_id"]))[0]["username"]

    if request.method == "GET" :
        stocks = db.execute("SELECT stock FROM portfolio WHERE username = ?", username)
        return render_template("sell.html",all_stocks = stocks)

    elif request.method == "POST" :
        # TRYING TO match the no of shares in database and the number which we are trying to sell
        try :
            no_of_shares = int(request.form.get("no_of_shares"))
            stock = request.form.get("stock")
            stocks_holding = db.execute("SELECT * FROM portfolio WHERE username = ? and stock = ?",username,stock )[0]["no_of_shares"]

            # checking if enough stocks are there or not
            if stocks_holding < no_of_shares :
                return apology("NOT ENOUGH STOCKS")
            elif no_of_shares < 0 :
                return apology("Enter a valid no")

            else :
                stock_data = lookup(stock)
                amount = stock_data["price"] * no_of_shares
                db.execute("INSERT INTO history VALUES (?,?,?,?,?,?)", username,stock_data["name"],stock_data["symbol"],(no_of_shares - stocks_holding),(amount/no_of_shares),datetime.now())
                db.execute("UPDATE portfolio SET no_of_shares = ? WHERE username = ?",(no_of_shares - stocks_holding),username)

        except :
            return apology("Missing Symbol")
