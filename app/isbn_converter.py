from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoAlertPresentException

import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    """
    Replace ISBN with ISBN13 in books table using browser automation and online converter
    """

    # Initialize counter
    counter = 0

    # Set chromedriver to brower variable
    browser = webdriver.Chrome('/mnt/c/selenium/chromedriver.exe')

    # Open web page
    browser.get('http://www.loc.gov/publish/pcn/isbncnvt_pcn.html')

    # Point form to 'isbn_in' on web page
    form = browser.find_element_by_name('isbn_in')

    # Open CSV file and set to reader
    f = open("books.csv")
    reader = csv.reader(f)

    # Iterate over file
    for isbn, title, author, year in reader:

        book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).fetchone()

        if book.isbn13:

            print(f'already in db. {book.isbn}')

        else:

            # Send ISBN to input form
            form.send_keys(isbn)

            # Select convert button
            convert = browser.find_elements_by_xpath('//*[@id="main_body"]/div[4]/form/div/table/tbody/tr[3]/th/input[2]')

            # Press convert button
            convert[0].send_keys(Keys.ENTER)

            try:

                # Check for JS alerts
                alert = browser.switch_to.alert

                # If the check digit is incorrect
                if 'The check digit should be' in alert.text:

                    # Set digit to correct value
                    digit = alert.text[-2]

                    # Store old isbn
                    old_isbn = isbn

                    # Change to correct check digit to isbn
                    isbn = isbn[:9] + digit

                alert.accept()

            except NoAlertPresentException:
                pass

            finally:

                # Clear input fields 
                clear = browser.find_element_by_xpath('//*[@id="main_body"]/div[4]/form/div/table/tbody/tr[3]/th/input[1]')
                clear.send_keys(Keys.ENTER)

                # Send ISBN to input form
                form.send_keys(isbn)

                # Select convert button
                convert = browser.find_elements_by_xpath('//*[@id="main_body"]/div[4]/form/div/table/tbody/tr[3]/th/input[2]')

                # Press convert button
                convert[0].send_keys(Keys.ENTER)


            while True:
                
                # Set isbn13 to value of 'converted isbn' input field
                isbn13 = browser.find_elements_by_name('isbn_out')[0].get_attribute('value')

                # If it's not an empty string, continue the program
                if isbn13:
                    break
            
            # Update isbn in books table
            db.execute("UPDATE books SET isbn = :isbn where title = :title and author = :author",
                        {'isbn': isbn, 'title': book.title, 'author': book.author})
            db.commit()

            # Add isbn13 to books table
            db.execute("UPDATE books SET isbn13 = :isbn13 WHERE isbn = :isbn", {"isbn13": isbn13, "isbn": isbn})
            db.commit()

            # Clear input fields 
            clear = browser.find_element_by_xpath('//*[@id="main_body"]/div[4]/form/div/table/tbody/tr[3]/th/input[1]')
            clear.send_keys(Keys.ENTER)

            # Print progress as program runs
            print(f"{counter} | {isbn} | {isbn13}")

            # Increment Counter
            counter += 1

if __name__ == "__main__":
    main()