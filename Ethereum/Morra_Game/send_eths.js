// Import web3
var Web3 = require('web3');
// Connect to local Geth client
var web3 = new Web3('http://localhost:8545');
// Prepare transaction
var transaction = {
from: "0xe38BdBAE7777304f6f4391d508F8253223741237",
to: "0xD2D3CBa5Ce8ebF8e043454CfC968fEB20c1e8fA2",
value: "0x1158E460913D00000"
}
// Send the transaction
web3.eth.sendTransaction(transaction).then(console.log);