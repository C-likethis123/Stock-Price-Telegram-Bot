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
            }
def main():    
    #retrieves stock price of company
    def retrieve_price(url):
        browser.get(url)
        soup = BeautifulSoup(browser.page_source, "html.parser")
        result = soup.find("span", {"class": "Trsdu(0.3s) Fw(b) Fz(36px) Mb(-4px) D(ib)"})
        return result.text

    # Check if a user is registered in the database
    def is_registered(id):
        # query database
        command = "SELECT * FROM users WHERE ID='{}';".format(id)
        cur.execute(command)
        rows = cur.fetchall()
        # if there is no such id in the database, return false
        return len(rows) != 0

    @bot.message_handler(commands=['start'])
    def start_bot(message):
        print("Going into the start command")
        msg = "Hello, this is Stock Price Bot! Here are the list of commands:\n"
        for command in commands:
            msg += command + " " + commands[command] + "\n"


        bot.send_message(message.chat.id, msg)

    @bot.message_handler(commands=['delete'])
    def delete_company(message):
        print("Going into the delete_company function")
        print(message.chat.id)
        id = message.chat.id
        if not is_registered(str(id)):
            bot.send_message(id, "You have not added any stocks to your watchlist!")
        else:
            command = "SELECT * FROM WATCHLIST WHERE user_id='{}';".format(id)
            company_urls = cur.execute(command)
            rows = cur.fetchall()

            msg = "Select company (companies) to delete from the watchlist (Reply 0 to cancel this operation):\n"
            for row in rows:
                code = row[0]
                company = row[2]
                index = row[3]
                msg += "{}. {}({})\n".format(index, company, code)

            action = bot.send_message(id, msg)
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
        user_id = str(message.chat.id)

        command = '''INSERT INTO watchlist (code, company, url, user_id)
                VALUES (%s, %s, %s, %s);'''
        print(command)
        cur.execute(command, (ticker, company_name, link, user_id))
        conn.commit()
        bot.send_message(message.chat.id, company_name + " added into watchlist!")

        
    @bot.message_handler(commands=['prices'])
    def monitor_price(message):
        print("Opened a browser with PhantomJS")
        command = 'SELECT * FROM WATCHLIST;'
        company_urls = cur.execute(command)

        rows = cur.fetchall()
        final_message = "Prices of stocks:\n"
        for row in rows:
            code = row[0]
            url = row[1]
            company = row[2]
            final_message += "The price of {}({}) is {}.\n".format(company, code, retrieve_price(url))
        bot.send_message(message.chat.id, final_message)
            

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
