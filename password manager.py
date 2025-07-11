import os
import random as rd
import json
import string

password_file = "password.json"

def load_password():
    if os.path.exists(password_file):
        with open(password_file, "r") as file:
            return json.load(file)
    return {}

def save_password(passwords):
    with open(password_file, "w") as file:
         json.dump(passwords,file, indent=4)
    
def add_password():
    website = input("Enter website ULR: ").strip()
    email = input("Enter email: ").strip()
    username = input("username: ").strip()
    password = input("password: ").strip()

    passwords = load_password()

    passwords[website] ={
        "email" : email,
        "username" : username ,
        "password" : password
    }

    save_password(passwords)
    print("the password has been saved ")

def generate_password(lenght = 12):
    chars = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(rd.choice(chars) for _ in range(lenght))
    print(f"\n Generated password: {password}\n")


    
def view_password():
    passwords = load_password()
    if not passwords:
        print("no password saved yet .")
    else:
        for wedsite, details in passwords.items():
            print(f"{wedsite} -> username = {details['username']} ->password = {details['password']}")
    


def search_password():
    website = input('Enter website name: ')
    passwords = load_password()
    if website in passwords:
        details = passwords[website]
        print(f"{website} username = {details['username']} -> password = {details['password']}")

    else: 
        print("No password found on this website ")


def main():
    while (True):

        print("\n password manager \n")
        print("1. Add New Password")
        print("2. Generate Random Password")
        print("3. View Saved Passwords")
        print("4. Search Password by Website")
        print("5. Exit \n")

        option = input("Enter an option: ").strip()

        if option == '1':
            add_password()
        elif option == '2':
            try:
                length = int(input("Enter length of password: ")or "12")
                generate_password(length)
            except ValueError:
                print("only integer are allow: ")
        elif option == '3':
            view_password()

        elif option == '4':
            search_password()

        elif option == '5':
            print ("\n Good bye \n\n\n")
            break

        else:
            print("Enter a valid option (1 - 5) ")

if __name__ == "__main__":
    main()

