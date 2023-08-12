import os
from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from flask_mail import Mail,Message
from helpers import apology, login_required, lookup, usd,quotes
import matplotlib.pyplot as plt
import yfinance as yf
# Configure application
# configuring mail in flask application
app = Flask(__name__)
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'arsharora06202@gmail.com'
app.config['MAIL_PASSWORD'] = os.environ.get('PASSWORD')

# setting up which security layer to use here we are setting ssl not transport layer security TLS

app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

@app.route("/confirmation")
def confirmation():

  recipient_email = db.execute("SELECT * from users where id = ?",session["user_id"])["email"]
  print(f'\n\n\n  {recipient_email}+ \n\n\n')
  msg = Message('hello , just sending out email from flask!!!', sender =   'noreply@flaskapp.com', recipients = [recipient_email])
  msg.body = "Thanks for placing your order on protfolio management group! your order will be fulfilled shortly"
  mail.send(msg)
  flash("Message sent")
  return

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
# configuring mail

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show portfolio of stocks"""
    # extracting details for the index page
    portfolio_cash = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])[0]["cash"]
    stock_index = db.execute("SELECT U.username,stock,no_of_shares,price,P.total,cash FROM users U,portfolio P WHERE U.username = P.username ")
    final_cash  = portfolio_cash

    # calculating the total cash
    for i in range(len(stock_index)) :
        final_cash += stock_index[i]["no_of_shares"] * stock_index[i]["price"]
    return render_template("index.html", portfolio = stock_index,cash = round(portfolio_cash,2),grand_total = round(final_cash,2))

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
                # print(db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"]))
                cash_in_account = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
                total_amount_required = float(stock["price"]) * no_of_shares

                if total_amount_required > cash_in_account :
                    return apology("Not enough fund in the Account ")

                # updating in the portfolio table the stock
                else  :
                    cash_in_account -= total_amount_required
                    # helper function that is does the buying of the stock.
                    return database_buy(stock["symbol"],no_of_shares,total_amount_required,stock["name"],cash_in_account)

        # if the request method is get then rendering the page
        elif request.method == "GET" :
            return render_template("buy.html")

    except :
        return apology("error 405 Missing entries")

# a helper function for the updating the portfolio
def database_buy(stock_name,no_of_shares,amount,symbol,cash_in_account) :
    username = db.execute("SELECT username FROM users where id = ?",session["user_id"])[0]["username"]
    # checking if the stock is already in the table or not
    if db.execute("SELECT * FROM portfolio WHERE stock = ? AND username = ? ", stock_name,username) == [] :
        # inserting data into portfolio and history if its a new transaction
        db.execute("INSERT into portfolio Values (?,?,?,?,?)",username,stock_name,no_of_shares,round((amount/no_of_shares),2),round((amount),2))
        db.execute("INSERT INTO history VALUES (?,?,?,?,?,?)", username,stock_name,symbol,no_of_shares,round((amount/no_of_shares),2),datetime.now())

    # if it is already in the table then updating the details in the portfolio
    else :

        total_shares = no_of_shares + db.execute("SELECT no_of_shares FROM portfolio WHERE username = ? AND stock = ?", username,stock_name)[0]["no_of_shares"]
        average_price = (db.execute("SELECT total FROM portfolio WHERE username = ? AND Stock = ?", username,stock_name)[0]["total"] + amount) / total_shares
        total = (average_price * total_shares)
        # updating the portfolio and history
        db.execute("UPDATE  portfolio SET no_of_shares  = ? ,price = ?,total = ? WHERE stock = ? and username = ?",total_shares,round(average_price,2),round(total,2),stock_name,username)
        db.execute("INSERT INTO history VALUES (?,?,?,?,?,?)", username,stock_name,symbol,no_of_shares,round((amount/no_of_shares),2),datetime.now())
    db.execute("UPDATE  users SET cash = ? WHERE id = ? ", round(cash_in_account,2), session["user_id"])
    # confirmation() trying how to send an autmatic app
    flash("Bought the Share",200)
    return redirect("/")

@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    # showing the history by accessing the username and
    username = db.execute("SELECT * FROM users WHERE id = ?",session["user_id"])[0]["username"]
    data = db.execute("SELECT * FROM history WHERE username = ? ORDER BY date DESC",username)
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

        # getting stock price and its history to draw chart
        stock_symbol = request.form.get("stock")
        stocks = lookup(stock_symbol)  # using the provided api function to get the stock price
        stock_history = quotes(stock_symbol)

        if stocks is None :
           return apology("Sorry, But the symbol that you provided is invalid! ",404)
                                                                                                                                                                                                                                                                                                                                                                                                                                               # Close the plot to free up resources
        else :
            # determining which stock to get
            stock_symbol = request.form.get("stock")
            interval = request.form.get("duration")

            # getting the hsitory of the stock
            company = yf.Ticker(stock_symbol)
            hist = company.history(period=interval)


            # Create a line chart
            plt.figure(figsize=(10, 6))

            plt.plot(hist.index, hist['Open'], label=f'{stock_symbol} Open Price', color='blue')
            plt.xlabel('Date')
            plt.ylabel('Price')
            plt.title(f'{stock_symbol} Stock Price Over Time')
            plt.legend()
            plt.grid(True)

            # Save the chart as an image
            image_filename = f"static/stock_plot.png"
            plt.savefig(image_filename, format='png')

            # Clear the plot to free up resources
            plt.clf()

            return render_template("quoted.html",stock_data = stock_history,stock_price = stocks)
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

def database_sell(stock_name,no_of_shares,amount,symbol,cash_in_account) :
    username = db.execute("SELECT * FROM users where id = ?",session["user_id"])[0]["username"]

    # if no stocks left then deleting it from portfolio
    if db.execute("SELECT * FROM portfolio WHERE stock = ? AND username = ? ", stock_name,username)[0]["no_of_shares"] + no_of_shares == 0:
        total_shares = no_of_shares + db.execute("SELECT * FROM portfolio WHERE username = ? AND stock = ?", username,stock_name)[0]["no_of_shares"]
        average_price = (db.execute("SELECT * FROM portfolio WHERE username = ? AND stock = ?", username,stock_name)[0]["total"] - amount)/-no_of_shares
        total = (average_price * -no_of_shares)

        # updating the portfolio and history regarding the transaction
        db.execute("DELETE FROM portfolio WHERE stock = ? and username = ? ",stock_name,username)
        db.execute("INSERT INTO history VALUES (?,?,?,?,?,?)", username,stock_name,symbol,no_of_shares,round(average_price,2),datetime.now())

    # if some stocks are left
    else :

    # as the no of stocks is already negative we are just adding the stocks but not the amount
        total_shares = no_of_shares + db.execute("SELECT * FROM portfolio WHERE username = ? AND stock = ?", username,stock_name)[0]["no_of_shares"]
        average_price = (db.execute("SELECT * FROM portfolio WHERE username = ? AND stock = ?", username,stock_name)[0]["total"] - amount)/total_shares
        total = (average_price * total_shares)

        # updating the portfolio and history
        db.execute("UPDATE  portfolio SET no_of_shares  = ? ,price = ?,total = ? WHERE stock = ? and username = ?",total_shares,round(average_price,2),round(total,2),stock_name,username)
        db.execute("INSERT INTO history VALUES (?,?,?,?,?,?)", username,stock_name,symbol,no_of_shares,round((amount/no_of_shares),2),datetime.now())
        db.execute("UPDATE  users SET cash = ? WHERE id = ? ", round(cash_in_account,2), session["user_id"])

    # updating the cash in the portfolio and users account
    db.execute("UPDATE  users SET cash = ? WHERE id = ? ", round(cash_in_account,2), session["user_id"])
    # confirmation() figuring how to send autmatic email
    flash("Sold the Share",200)
    return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell() :
    username = db.execute("SELECT username FROM users where id = ?",session["user_id"])[0]["username"]
    if request.method == "POST" :
        # looking at the stock price
        symbol = request.form.get("stock")
        stock = lookup(symbol)
        shares = request.form.get("no_of_shares")

        try :
             no_of_shares = int(shares)
        except :
            return apology("enter a integer")

        # checking whether the name is vaild or not
        if stock is None :
            return apology("Stock Not Found",404)
        # checkig for the number of shares to buy
        elif   no_of_shares < 0 :
            return apology("Enter a Valid No", 403)
        # checking if there is enough fund or not in the account
        else :
            # determining if there is enough cash in the account

            cash_in_account = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
            total_amount_got= round(stock["price"],2) * no_of_shares
            stocks_holding = db.execute("SELECT * FROM portfolio WHERE username = ? and stock = ?",username,stock["symbol"])[0]["no_of_shares"]
            #
            if  no_of_shares > stocks_holding :
                return apology("NOT ENOUGH STOCKS")
            elif no_of_shares < 0 :
                return apology("Enter a valid no")

            # updating in the portfolio table the stock
            else  :
                cash_in_account += total_amount_got
                # helper function that is does the buying of the stock.
                return database_sell(stock["symbol"],-no_of_shares,total_amount_got,stock["name"],cash_in_account)

    # if the request method is get then rendering the page

    elif request.method == "GET" :
        stocks = db.execute("SELECT stock FROM portfolio WHERE username = ?", username)
        return render_template("sell.html",all_stocks = stocks)
    else :
        return apology("error 405 Missing entries")

