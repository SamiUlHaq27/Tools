def gen_price(integer):
    array = list(str(integer))
    length = len(array)-1
    no_commas = int(length/3)

    for i in range(1,no_commas+1):
        index = (3*i)+(i-1)
        array.insert(-index,',')

    value = ''
    for i in array:
        value += i
        
    return value
