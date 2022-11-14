// Import web3
var Web3 = require('web3');
var Contract = require('web3-eth-contract');
// set provider
Contract.setProvider( new Web3.providers.HttpProvider( 'http://127.0.0.1:8545' ));
var myContract = new Contract([
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "addr",
				"type": "address"
			}
		],
		"name": "get",
		"outputs": [
			{
				"internalType": "string",
				"name": "",
				"type": "string"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "getmine",
		"outputs": [
			{
				"internalType": "string",
				"name": "",
				"type": "string"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"name": "roll",
		"outputs": [
			{
				"internalType": "string",
				"name": "",
				"type": "string"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "newRoll",
				"type": "string"
			}
		],
		"name": "update",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	}
], '0x709830edf8feF92B0d879dE9ee9BdB2400BB5662' , // address of the contract
{
from: '0xe38BdBAE7777304f6f4391d508F8253223741237' , // address from which you want to transact
gasPrice: '20000000000' // default gas price in wei, 20 gwei in this case
});
myContract.methods.update('18CS30018').send()
.then(function(receipt){
console.log(receipt)
});