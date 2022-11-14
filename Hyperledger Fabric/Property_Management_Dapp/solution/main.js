const FabricCAServices = require('fabric-ca-client');
const { Wallets, Gateway } = require('fabric-network');
const fs = require('fs');
const path = require('path');

async function main(){

   var path1 = '../organizations/peerOrganizations/org1.example.com/connection-org1.json';
   var path2 = '../organizations/peerOrganizations/org2.example.com/connection-org2.json';
   var testcase = 'testcase.txt';
   var cmdArgs = process.argv;

   if(cmdArgs.length == 5)
   {
   	  path1 = cmdArgs[2];
   	  path2 =  cmdArgs[3];
   	  testcase = cmdArgs[4];
   }
   else if(cmdArgs.length == 1)
   {
   	  testcase = cmdArgs[2];
   }

   //================================== Org1 ============================================
   const ccpPath1 = path.resolve(path1);
   const ccp1 = JSON.parse(fs.readFileSync(ccpPath1, 'utf8'));
   const caInfo1 = ccp1.certificateAuthorities['ca.org1.example.com'];
   const caTLSCACerts1 = caInfo1.tlsCACerts.pem;
   const ca1 = new FabricCAServices(caInfo1.url, { trustedRoots: caTLSCACerts1, verify: false }, caInfo1.caName);
   const walletPath1 = path.join(process.cwd(), 'wallet1');
   const wallet1 = await Wallets.newFileSystemWallet(walletPath1);

   //Admin creation
   var adminId1 = await wallet1.get('admin');
   const enroll1 = await ca1.enroll({ enrollmentID: 'admin', enrollmentSecret: 'adminpw'});
   const x509Id1 = {
      credentials: {
      	certificate: enroll1.certificate,
      	privateKey: enroll1.key.toBytes(),
      },
      mspId: 'Org1MSP',
      type: 'X.509',
   };
   await wallet1.put('admin', x509Id1);
   console.log('Succesfully enrolled admin user and imported it into wallet1');
   adminId1 = await wallet1.get('admin');
 
   //Client creation
   var userId1 = await wallet1.get('appUser');
   if (userId1) {
        console.log('Id "appUser" already exists in wallet1');
   } else {
   	  try {
        const prov = wallet1.getProviderRegistry().getProvider(adminId1.type);
        const adminUser = await prov.getUserContext(adminId1, 'admin');

        const secret = await ca1.register({
            affiliation: 'org1.department1',
            enrollmentID: 'appUser',
            role: 'client'
        }, adminUser);

        const enrollment = await ca1.enroll({
             enrollmentID: 'appUser',
             enrollmentSecret: secret
        });

        const x509Id = {
              credentials: {
		      	certificate: enrollment.certificate,
		      	privateKey: enrollment.key.toBytes(),
		      },
		      mspId: 'Org1MSP',
		      type: 'X.509',
        };

        await wallet1.put('appUser', x509Id);
        console.log('Succesfully registered and enrolled client "appUser" and enrolled it into wallet1!');
        userId1 = await wallet1.get('appUser');

     } catch(error) {
        console.log(error.message);
     }
   }

   //Gateway Creation
   const gateway1 = new Gateway();
   await gateway1.connect(ccp1, {wallet: wallet1, identity:'appUser', discovery: {enabled: true, asLocalhost: true}});

   //================================== Org2 ================================================
   const ccpPath2 = path.resolve(path2);
   const ccp2 = JSON.parse(fs.readFileSync(ccpPath2, 'utf8'));
   const caInfo2 = ccp2.certificateAuthorities['ca.org2.example.com'];
   const caTLSCACerts2 = caInfo2.tlsCACerts.pem;
   const ca2 = new FabricCAServices(caInfo2.url, { trustedRoots: caTLSCACerts2, verify: false }, caInfo2.caName);
   const walletPath2 = path.join(process.cwd(), 'wallet2');
   const wallet2 = await Wallets.newFileSystemWallet(walletPath2);

   //Admin creation
   var adminId2 = await wallet2.get('admin');
   const enroll2 = await ca2.enroll({ enrollmentID: 'admin', enrollmentSecret: 'adminpw'});
   const x509Id2 = {
      credentials: {
      	certificate: enroll2.certificate,
      	privateKey: enroll2.key.toBytes(),
      },
      mspId: 'Org2MSP',
      type: 'X.509',
   };
   await wallet2.put('admin', x509Id2);
   console.log('Succesfully enrolled admin user and imported it into wallet2');
   adminId2 = await wallet2.get('admin');

   //Client creation
   var userId2 = await wallet2.get('appUser');
   if(userId2) {
        console.log('Id "appUser" already exists in wallet2');
   } else {
   	  try {
        const provider = wallet2.getProviderRegistry().getProvider(adminId2.type);
        const adminUser2 = await provider.getUserContext(adminId2, 'admin');

        const secret = await ca2.register({
            affiliation: 'org2.department1',
            enrollmentID: 'appUser',
            role: 'client'
        }, adminUser2);

        const enrollment2 = await ca2.enroll({
             enrollmentID: 'appUser',
             enrollmentSecret: secret
        });

        const x509Id = {
              credentials: {
		      	certificate: enrollment2.certificate,
		      	privateKey: enrollment2.key.toBytes(),
		      },
		      mspId: 'Org2MSP',
		      type: 'X.509',
        };

        await wallet2.put('appUser', x509Id);
        console.log('Succesfully registered and enrolled client "appUser" and enrolled it into wallet2!');
        userId2 = await wallet2.get('appUser');

     } catch(error) {
        console.log(error.message);
     }
   }
   
   //Gateway Creation
   const gateway2 = new Gateway();
   await gateway2.connect(ccp2, {wallet: wallet2, identity:'appUser', discovery: {enabled: true, asLocalhost: true}});

   //=========================================== Testcase =====================================
	const data = fs.readFileSync(testcase, 'utf8');
	// split the contents by new line
	const lines = data.split(/\r?\n/);
	var network, contract;
	console.log('Number of testcases: ' + lines.length);
	fs.writeFileSync('output.txt',"");
	for (let i = 0; i<lines.length; i++){
	  	    let line = lines[i];
	        let test = line.split('; ');
	        let org = test[0];
	        let func = test[1];
	        let attr = [].concat(test);
	        attr.splice(0, 2);

	        fs.writeFileSync('output.txt',"[ ",{flag:'a+'});
	        args = [].concat(test);
	        for(let i=0; i<args.length; i++){
			    args[i] = "'" + args[i] + "'";
			}
			var list_with_quotes = args.join(", ");
	        fs.writeFileSync('output.txt', list_with_quotes, {flag:'a+'});
	        fs.writeFileSync('output.txt'," ]\n",{flag:'a+'});
	        
	        try {
	        	//Network access
		        switch (org) {
			        case 'org1':
					    network = await gateway1.getNetwork('mychannel');
					    contract = await network.getContract('fabhouse');   
					    break;
					case 'org2':
					    network = await gateway2.getNetwork('mychannel');
					    contract = await network.getContract('fabhouse');   
					    break;  
					default:
						fs.writeFileSync('output.txt','ERROR\n',{flag:'a+'});
						break;
				}
	            
	            //Query Execution
	            switch (func) {
					 case 'CreateHouse':
					    console.log('> CreateHouse invoked'); 
		                await contract.submitTransaction('CreateHouse', attr[0], attr[1], attr[2]);
		                break;
		             case 'ReadHouse': 
		         		console.log('> ReadHouse invoked');
		         	    let res = await contract.evaluateTransaction('ReadHouse', attr[0]);
		         		fs.writeFileSync('output.txt',res.toString(),{flag:'a+'});
		         		fs.writeFileSync('output.txt',"\n",{flag:'a+'}); 
		         		break;
		             case 'GetAllHouses':
		                console.log('> GetAllHouses invoked');
		         		let res2 = await contract.evaluateTransaction('GetAllHouses');	
		         		fs.writeFileSync('output.txt',res2.toString(),{flag:'a+'});
		         		fs.writeFileSync('output.txt',"\n",{flag:'a+'}); 
		         		break;
		             case 'TransferHouse':
		                console.log('> TransferHouse invoked');
		         		await contract.submitTransaction('TransferHouse', attr[0], attr[1]);
		         		break;
		             case 'HouseExists': 
		                console.log('> HouseExists invoked');
		         		let res3 = await contract.evaluateTransaction('HouseExists', attr[0]);
		         		fs.writeFileSync('output.txt',res3.toString(),{flag:'a+'});
		         		fs.writeFileSync('output.txt',"\n",{flag:'a+'}); 
		         		break;
		         	 default:
		         	    fs.writeFileSync('output.txt','ERROR\n',{flag:'a+'});
		         	    break;
	            }
			} catch(error) {
				fs.writeFileSync('output.txt','ERROR\n',{flag:'a+'});
			}  
			fs.writeFileSync('output.txt',"\n",{flag:'a+'}); 
	}
	await gateway1.disconnect();
	await gateway2.disconnect();
}

main();