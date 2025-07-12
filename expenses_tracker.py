import os 


File_name = "expenses.txt"
def add_expenses():
    Description = input("Enter the description: ")
    amount = input("Enter Amount: " )
    with open(File_name, "a") as file:
        file.write(f"{Description} - #{amount}\n")
    print ("Expenses has been added succesfully. \n")

def view_expenses():
    if not os.path.exists(File_name):
        print ("No expenses recorded yet: ")
        return
    total = 0 
    print("\n === YOUR EXPENSES ===\n")
    with open(File_name, "r") as file:
        for line in file :
            print(line.strip())
            try:
                amount = float(line.strip().split("#")[1])
                total +=amount
            except:
                pass
    print(f"\n Total Expenses: #{total}" ) 

def main():
    while(True):
        print("\n Expense Tracker ")
        print("1. Add expenses.")
        print("2. view recorded expenses: ")
        print("3. Exit ")

        option = input("Enter your option (1-3): ")
        if option == "1":
            add_expenses()
        elif option == "2":
            view_expenses()
        elif option == "3":
            print("Good bye \n\n ")
            break
        else:
             print("invalid choice, Try again: \n")


if __name__ ==  "__main__":
    main()