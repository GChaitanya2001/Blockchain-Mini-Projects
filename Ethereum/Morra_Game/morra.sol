//Contract address: 0xdd88160d7bd37ea8c0136c26d9bb863ffccf8534
//Roll No: 18CS30018

pragma solidity >=0.7.0 <0.9.0;

contract morra{
    address p1;
    address p2;
    mapping(address => uint) private bet;
    mapping(address => bytes32) private hash;
    mapping(uint => bool) private commit;
    mapping(uint => int) private reveal;
    uint players;
    bool init;
    
    constructor()
    {
        players = 0;
        reveal[1] = reveal[2] = -1;
        init = false;
    }
    
    function getBalance() public view returns (uint)
    {
        return address(this).balance;
    }
    
    function getPlayerId() public view returns (uint)
    {
        if(msg.sender == p1) return 1;
        else if(msg.sender == p2) return 2;
        return 0;
    }

    // function getPlayers() public view returns (uint)
    // {
    //     return players;
    // }
    
    // function getcommits() public view returns (uint)
    // {
    //     if(commit[1] == true && commit[2] == true) return 2;
    //     else if(commit[1] == true || commit[2] == true) return 1;
    //     return 0; 
    // }
     
    // function getreveals() public view returns (uint)
    // {
    //     if(reveal[1] != -1 && reveal[2] != -1) return 2;
    //     else if(reveal[1] != -1 || reveal[2] != -1) return 1;
    //     return 0; 
    // }
    
    function initialize() public payable returns (uint)
    {
        require(msg.value > 1e-3 ether, "Minimum bet is 1e-3 ether");
        if(players == 0 && init == false)
        {
            init = true;
            players++;
            p1 = msg.sender;
            bet[p1] = msg.value;
            return 1;
        }
        else if(players == 1 && init == true)
        {
            if(msg.value >= bet[p1])
            {
                if(getPlayerId() == 1) revert("Can't initialize twice!!");
                players++;
                p2 = msg.sender;
                bet[p2] = msg.value;
                return 2;
            }
            else revert("Bet must be >= player 1!!");
        }
        else revert("Not allowed! Players Full");
    }
    
    function commitmove(bytes32 hashMove) public returns (bool)
    {
       if((players == 2) && (getPlayerId() == 1 || getPlayerId() == 2) && commit[getPlayerId()] == false)
       {
            commit[getPlayerId()] = true;
            hash[msg.sender] = hashMove;
            return true;
       }
       return false;
    }
    
    function getFirstChar(string memory str) private pure returns (int) 
    {
        if (bytes(str)[0] == 0x30) return 0;
        else if (bytes(str)[0] == 0x31) return 1; 
        else if (bytes(str)[0] == 0x32) return 2;
        else if (bytes(str)[0] == 0x33) return 3; 
        else if (bytes(str)[0] == 0x34) return 4;
        else if (bytes(str)[0] == 0x35) return 5;
        return -1;
    }
    
    function de_initialize() private
    {
        players = 0;
        reveal[1] = reveal[2] = -1;
        commit[1] = commit[2] = false;
        bet[p1] = bet[p2] = 0;
        init = false;
        hash[p1] = hash[p2] = bytes32(0x0);
        p1 = p2 = address(bytes20(0x0));
    }
    
    
    function revealmove(string memory revealedMove) public returns (int)
    {
        int ret_move;
        if(getPlayerId() == 1 || getPlayerId() == 2){
            if((commit[1] == true) && (commit[2] == true) && reveal[getPlayerId()] == -1){
                 bytes32 temp = sha256(bytes(revealedMove));
                 if(temp == hash[msg.sender]) {reveal[getPlayerId()] = getFirstChar(revealedMove);}
                 else return -1;
            }
            else return -1;
            ret_move = reveal[getPlayerId()];
            if(reveal[1] != -1 && reveal[2] != -1){
                if(reveal[1] == reveal[2]) {
                    address payable addr = payable(p2);
                    addr.transfer(getBalance());
                }
                else {
                    address payable addr = payable(p1);
                    addr.transfer(getBalance());
                }
                de_initialize();
            }
            return ret_move;
        }
        return -1;
    }
}