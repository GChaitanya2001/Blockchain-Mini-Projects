import hashlib

def md5hash(data):
    result = hashlib.md5(data.encode())
    return result.hexdigest()

class Block:
    def __init__(self, prev_hash):
        self.merkle = None
        self.version = '02000000'
        self.prev = prev_hash
        self.hash = None
    
    def find_curr_hash(self):
        M = self.version + self.prev + self.merkle
        self.hash = md5hash(M)
        
    def find_merkle_root(self, data):
        # If size of "data" is odd, append last hash value 
        if len(data) % 2 != 0 and len(data) != 1:
            data.append(data[-1])   
        #Find merkle root
        while len(data) != 1:
            temp = []; i=0
            while i<len(data):
                h0 = str(data[i])
                h1 = str(data[i+1])
                i = i+2
                temp.append(md5hash(h0 + h1))
            # If size of "data" is odd, append last hash value 
            if len(temp) % 2 != 0 and len(temp) != 1:
                temp.append(temp[-1])
            data = temp
        self.merkle = data[0]

def construct_blockchain(B, genesis):
    blockchain = [genesis]
    prev_hashes = list()
    #Construct blockchain
    while B>0:
        # No of transactions
        T = int(input())
        data = []
        # Take transactions as input and append its md5 hash to "data" 
        for i in range(T):
            temp = input()
            data.append(md5hash(temp))
        # Take previous block header hash as input
        prev_hash = input()
        prev_hashes.append(prev_hash)
        #Create new block with these transactions with "calculated" hash of previous block
        block = Block(blockchain[-1].hash)
        block.find_merkle_root(data)
        block.find_curr_hash()
        #Append the created block to the blockchain
        blockchain.append(block)
        B = B-1
    return prev_hashes, blockchain

def main():
    # No of Blocks
    B = int(input())
    version = '02000000'
    
    #Genesis block
    genesis = Block(None)
    genesis.find_merkle_root(['coinbase'])
    genesis.hash = md5hash(version + md5hash('coinbase'))
    
    #Construct blockchain; prev_hashes are the inputs and blockchain is a list of blocks
    prev_hashes, blockchain = construct_blockchain(B, genesis)
    
    #Assert for integrity
    assert len(prev_hashes) + 1 == len(blockchain)
    
    #Check for validity
    for i in range(len(prev_hashes)):
        if(prev_hashes[i] == blockchain[i+1].prev):
            print("Valid")
        else:
            print("Invalid")
        
        
if __name__ == "__main__":
    main()           