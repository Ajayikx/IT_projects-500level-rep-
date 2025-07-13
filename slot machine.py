
def deposit ():
    while True :
        amount = input ('Enter the amount you want to deposit. $')
        if amount.isdigit():
            amount = int(amount)
            if amount < 0:
                print('Amount must be more than $0')
            else :
                break
        else :
            print ('You can only enter a numerical digit ')
    return amount

start = input('you can start the game : ')
if start== 'y':
    price = deposit()
    print (f"the amount you entered is {price} ")