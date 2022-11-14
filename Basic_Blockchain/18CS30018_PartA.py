import hashlib

def md5hash(data):
    result = hashlib.md5(data.encode())
    return result.hexdigest()

def main():
    # No of Test cases
    B = int(input())
    while B>0:
        # No of transactions
        T = int(input())
        data = []
        # Take transactions as input and append its md5 hash to "data" 
        for i in range(T):
            temp = input()
            data.append(md5hash(temp))
        # Take merkle root hash as input
        root = input()
        # If size of "data" is odd append last value
        if len(data) % 2 != 0 and len(data) != 1:
            data.append(data[-1])
        # Build merkle tree until size of "data" is 1
        while len(data) != 1:
            temp = [] #temp stores hash of values of next level
            i=0
            while i<len(data):
                h0 = str(data[i])
                h1 = str(data[i+1])
                i = i+2
                temp.append(md5hash(h0 + h1))
            # If size of temp is 1 then root is found
            if len(temp) == 1:
                data = temp
                break
            # If size of "data" is odd, append last hash value 
            elif len(temp) % 2 != 0:
                temp.append(temp[-1])
                data = temp
            else:
                data = temp
        if data[0] == root:
             print("Valid")
        else:
             print("Invalid")
        B = B-1        
        
if __name__ == "__main__":
    main()           