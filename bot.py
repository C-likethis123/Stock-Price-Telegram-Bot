import telebot
import os
import sys
from bs4 import BeautifulSoup
from selenium import webdriver
import psycopg2

bot_token = os.environ['STOCK_BOT_TOKEN']
bot = telebot.TeleBot(bot_token)
print("Connected to bot API: " + bot_token)

DATABASE_URL = os.environ['DATABASE_URL']

conn = psycopg2.connect(DATABASE_URL, sslmode='require')
print("Connected to database url: " + DATABASE_URL)

#connect to server
cur = conn.cursor()
browser = webdriver.PhantomJS()
print("Opened a browser in PhantomJS!")

commands = {'/delete': 'Delete one or more companies from your watchlist.',
            '/add': 'Add a company to your watchlist',
            '/prices': 'Get the latest stock prices of companies in your watchlist.',
            '/create': 'Creates a new watchlist'}
def main():    
    #retrieves stock price of company
    def retrieve_price(url):
        browser.get(url)
        soup = BeautifulSoup(browser.page_source, "html.parser")
        result = soup.find("span", {"class": "Trsdu(0.3s) Fw(b) Fz(36px) Mb(-4px) D(ib)"})
        return result.text

    @bot.message_handler(commands=['start'])
    def start_bot(message):
        print("Going into the start command")
        msg = "Hello, this is Stock Price Bot! Here are the list of commands:\n"
        for command in commands:
            msg += command + " " + commands[command] + "\n"


        bot.send_message(message.chat.id, msg)


    @bot.message_handler(commands=['create'])
    def create_watchlist(message):
        print("Creating a watchlist!")
        command = '''CREATE TABLE WATCHLIST
            (code varchar(10),
            url varchar(1000),
            company varchar(100)
            id int SERIAL)'''
        cur.execute(command)

        bot.send_message(message.chat.id, "Watchlist created!")

    @bot.message_handler(commands=['delete'])
    def delete_company(message):
        print("Going into the delete_company function")
        command = 'SELECT * FROM WATCHLIST;'
        company_urls = cur.execute(command)
        rows = cur.fetchall()

        msg = "Select company (companies) to delete from the watchlist (Reply 0 to cancel this operation):\n"
        for row in rows:
            code = row[0]
            company = row[2]
            index = row[3]
            msg += "{}. {}({})\n".format(index, company, code)

        action = bot.send_message(message.chat.id, msg)
        bot.register_next_step_handler(action, process_deletion)

    def process_deletion(message):
        action = message.text
        if action == '0':
            bot.send_message(message.chat.id, "Deletion cancelled!")
        else:
            companies = action.split(" ")
            for company in companies:
                command = 'DELETE FROM WATCHLIST WHERE ID = %s;'
                cur.execute(command, (company))
                conn.commit()


            command = 'SELECT * FROM WATCHLIST;'
            updated_watchlist = "Updated watchlist: \n"
            cur.execute(command)

            rows = cur.fetchall()
        
            for row in rows:
                code = row[0]
                company = row[2]
                index = row[3]
                updated_watchlist += "{}. {}({})\n".format(index, company, code)


            bot.send_message(message.chat.id, updated_watchlist)

                    
        
    @bot.message_handler(commands=['add'])
    def add_company(message):
        information = bot.send_message(message.chat.id, "What is the company's name, ticker, url? Reply with each piece of information separated by a newline.")
        bot.register_next_step_handler(information, add_name)

    def add_name(message):
        information = message.text
        information = information.split("\n")

        company_name = information[0]
        ticker = information[1]
        link = information[2]

        command = '''INSERT INTO watchlist (code, company, url)
                VALUES (%s, %s, %s);'''
        print(command)
        cur.execute(command, (ticker, company_name, link))
        conn.commit()
        bot.send_message(message.chat.id, company_name + " added into watchlist!")

        
    @bot.message_handler(commands=['prices'])
    def monitor_price(message):
        print("Opened a browser with PhantomJS")
        command = 'SELECT * FROM WATCHLIST;'
        company_urls = cur.execute(command)

        rows = cur.fetchall()
        
        for row in rows:
            code = row[0]
            url = row[1]
            company = row[2]
            bot.send_message(message.chat.id, "The price of {}({}) is {}.".format(company, code, retrieve_price(url)))
            print(row)
            

    bot.polling()




try:
    main()
except KeyboardInterrupt:
    print("Press enter to stop running this bot: ")
    command = input("Press enter to stop running this bot: ")
    if command == "\n":
        browser.quit()
        cur.close()
        conn.close()
        sys.exit(0)
except NameError:
    print("Encountered a NameError, shutting down... ")
    browser.quit()
    cur.close()
    conn.close()
    sys.exit(0)
except Exception:
    print("Encountered something, shutting down... ")
    browser.quit()
    cur.close()
    conn.close()
    sys.exit(0)
