###### ROLL NO: 18CS30018 ####

import asyncio
import json
import time
from indy import pool, wallet, did, ledger, anoncreds, blob_storage
from indy.error import ErrorCode, IndyError
from indy.pairwise import get_pairwise
from os.path import dirname


async def create_wallet(identity):
    print("\"{}\" -> Create wallet".format(identity['name']))
    try:
        await wallet.create_wallet(identity['wallet_config'],
                                   identity['wallet_credentials'])
    except IndyError as ex:
        if ex.error_code == ErrorCode.PoolLedgerConfigAlreadyExistsError:
            pass
    identity['wallet'] = await wallet.open_wallet(identity['wallet_config'], identity['wallet_credentials'])


async def get_schema(pool_handle, _did, schema_id):
    get_schema_request = await ledger.build_get_schema_request(_did, schema_id)
    get_schema_response = await ensure_previous_request_applied(
        pool_handle, get_schema_request, lambda response: response['result']['data'] is not None)
    return await ledger.parse_get_schema_response(get_schema_response)


async def ensure_previous_request_applied(pool_handle, checker_request, checker):
    for _ in range(3):
        response = json.loads(await ledger.submit_request(pool_handle, checker_request))
        try:
            if checker(response):
                return json.dumps(response)
        except TypeError:
            pass
        time.sleep(5)


async def get_cred_def(pool_handle, _did, cred_def_id):
    get_cred_def_request = await ledger.build_get_cred_def_request(_did, cred_def_id)
    get_cred_def_response = \
        await ensure_previous_request_applied(pool_handle, get_cred_def_request,
                                              lambda response: response['result']['data'] is not None)
    return await ledger.parse_get_cred_def_response(get_cred_def_response)


async def getting_verinym(from_, to):
    await create_wallet(to)

    (to['did'], to['key']) = await did.create_and_store_my_did(to['wallet'], "{}")

    from_['info'] = {
        'did': to['did'],
        'verkey': to['key'],
        'role': to['role'] or None
    }

    await send_nym(from_['pool'], from_['wallet'], from_['did'], from_['info']['did'], from_['info']['verkey'], from_['info']['role'])


async def send_nym(pool_handle, wallet_handle, _did, new_did, new_key, role):
    nym_request = await ledger.build_nym_request(_did, new_did, new_key, None, role)
    print(nym_request)
    await ledger.sign_and_submit_request(pool_handle, wallet_handle, _did, nym_request)


async def prover_get_entities_from_ledger(pool_handle, _did, identifiers, actor, timestamp_from=None,
                                          timestamp_to=None):
    schemas = {}
    cred_defs = {}
    rev_states = {}
    for item in identifiers.values():
        print("\"{}\" -> Get Schema from Ledger".format(actor))
        (received_schema_id, received_schema) = await get_schema(pool_handle, _did, item['schema_id'])
        schemas[received_schema_id] = json.loads(received_schema)

        print("\"{}\" -> Get Claim Definition from Ledger".format(actor))
        (received_cred_def_id, received_cred_def) = await get_cred_def(pool_handle, _did, item['cred_def_id'])
        cred_defs[received_cred_def_id] = json.loads(received_cred_def)

        if 'rev_reg_id' in item and item['rev_reg_id'] is not None:
            # Create Revocations States
            print("\"{}\" -> Get Revocation Registry Definition from Ledger".format(actor))
            get_revoc_reg_def_request = await ledger.build_get_revoc_reg_def_request(_did, item['rev_reg_id'])

            get_revoc_reg_def_response = \
                await ensure_previous_request_applied(pool_handle, get_revoc_reg_def_request,
                                                      lambda response: response['result']['data'] is not None)
            (rev_reg_id, revoc_reg_def_json) = await ledger.parse_get_revoc_reg_def_response(get_revoc_reg_def_response)

            print("\"{}\" -> Get Revocation Registry Delta from Ledger".format(actor))
            if not timestamp_to: timestamp_to = int(time.time())
            get_revoc_reg_delta_request = \
                await ledger.build_get_revoc_reg_delta_request(_did, item['rev_reg_id'], timestamp_from, timestamp_to)
            get_revoc_reg_delta_response = \
                await ensure_previous_request_applied(pool_handle, get_revoc_reg_delta_request,
                                                      lambda response: response['result']['data'] is not None)
            (rev_reg_id, revoc_reg_delta_json, t) = \
                await ledger.parse_get_revoc_reg_delta_response(get_revoc_reg_delta_response)

            tails_reader_config = json.dumps(
                {'base_dir': dirname(json.loads(revoc_reg_def_json)['value']['tailsLocation']),
                 'uri_pattern': ''})
            blob_storage_reader_cfg_handle = await blob_storage.open_reader('default', tails_reader_config)

            print('%s - Create Revocation State', actor)
            rev_state_json = \
                await anoncreds.create_revocation_state(blob_storage_reader_cfg_handle, revoc_reg_def_json,
                                                        revoc_reg_delta_json, t, item['cred_rev_id'])
            rev_states[rev_reg_id] = {t: json.loads(rev_state_json)}

    return json.dumps(schemas), json.dumps(cred_defs), json.dumps(rev_states)


async def verifier_get_entities_from_ledger(pool_handle, _did, identifiers, actor, timestamp=None):
    schemas = {}
    cred_defs = {}
    rev_reg_defs = {}
    rev_regs = {}
    for item in identifiers:
        print("\"{}\" -> Get Schema from Ledger".format(actor))
        (received_schema_id, received_schema) = await get_schema(pool_handle, _did, item['schema_id'])
        schemas[received_schema_id] = json.loads(received_schema)

        print("\"{}\" -> Get Claim Definition from Ledger".format(actor))
        (received_cred_def_id, received_cred_def) = await get_cred_def(pool_handle, _did, item['cred_def_id'])
        cred_defs[received_cred_def_id] = json.loads(received_cred_def)

        if 'rev_reg_id' in item and item['rev_reg_id'] is not None:
            # Get Revocation Definitions and Revocation Registries
            print("\"{}\" -> Get Revocation Definition from Ledger".format(actor))
            get_revoc_reg_def_request = await ledger.build_get_revoc_reg_def_request(_did, item['rev_reg_id'])

            get_revoc_reg_def_response = \
                await ensure_previous_request_applied(pool_handle, get_revoc_reg_def_request,
                                                      lambda response: response['result']['data'] is not None)
            (rev_reg_id, revoc_reg_def_json) = await ledger.parse_get_revoc_reg_def_response(get_revoc_reg_def_response)

            print("\"{}\" -> Get Revocation Registry from Ledger".format(actor))
            if not timestamp: timestamp = item['timestamp']
            get_revoc_reg_request = \
                await ledger.build_get_revoc_reg_request(_did, item['rev_reg_id'], timestamp)
            get_revoc_reg_response = \
                await ensure_previous_request_applied(pool_handle, get_revoc_reg_request,
                                                      lambda response: response['result']['data'] is not None)
            (rev_reg_id, rev_reg_json, timestamp2) = await ledger.parse_get_revoc_reg_response(get_revoc_reg_response)

            rev_regs[rev_reg_id] = {timestamp2: json.loads(rev_reg_json)}
            rev_reg_defs[rev_reg_id] = json.loads(revoc_reg_def_json)

    return json.dumps(schemas), json.dumps(cred_defs), json.dumps(rev_reg_defs), json.dumps(rev_regs)


async def run():

    print("=======================================")
    print("===              Part A              ==")
    print("---------------------------------------")
    ################################################

    print("Connecting to indy pool.....")
    pool_ = {
        'name': 'pool1'
    }
    print("Open Pool Ledger: {}".format(pool_['name']))
    pool_['genesis_txn_path'] = "pool1.txn"
    pool_['config'] = json.dumps({"genesis_txn": str(pool_['genesis_txn_path'])})

    print(pool_)

    await pool.set_protocol_version(2)

    try:
        await pool.create_pool_ledger_config(pool_['name'], pool_['config'])
    except IndyError as ex:
        if ex.error_code == ErrorCode.PoolLedgerConfigAlreadyExistsError:
            pass
    pool_['handle'] = await pool.open_pool_ledger(pool_['name'], None)

    print("\nCreating a steward....")
    steward = {
        'name': "Sovrin Steward",
        'wallet_config': json.dumps({'id': 'sovrin_steward_wallet'}),
        'wallet_credentials': json.dumps({'key': 'steward_wallet_key'}),
        'pool': pool_['handle'],
        'seed': '000000000000000000000000Steward1'
    }
    print(steward)

    await create_wallet(steward)

    steward["did_info"] = json.dumps({'seed':steward['seed']})

    # did:demoindynetwork:Th7MpTaRZVRYnPiabds81Y
    steward['did'], steward['key'] = await did.create_and_store_my_did(steward['wallet'], steward['did_info'])

    print("\n-----------------------------------------")
    print("==  Registering Verinym for Government  ==")
    print("------------------------------------------")


    government = {
        'name': 'Government',
        'wallet_config': json.dumps({'id': 'government_wallet'}),
        'wallet_credentials': json.dumps({'key': 'government_wallet_key'}),
        'pool': pool_['handle'],
        'role': 'TRUST_ANCHOR'
    }

    await getting_verinym(steward, government)

    print("\n--------------------------------------------")
    print("==  Registering Verinym for IIT Kharagpur  ==")
    print("---------------------------------------------")

    iitkgp = {
        'name': 'IIT Kharagpur',
        'wallet_config': json.dumps({'id': 'iitkgp_wallet'}),
        'wallet_credentials': json.dumps({'key': 'iitkgp_wallet_key'}),
        'pool': pool_['handle'],
        'role': 'TRUST_ANCHOR'
    }

    await getting_verinym(steward, iitkgp)

    print("\n----------------------------------------")
    print("==   Registering Verinym for CitiBank   ==")
    print("------------------------------------------")

    citibank = {
        'name': 'CitiBank',
        'wallet_config': json.dumps({'id': 'citibank_wallet'}),
        'wallet_credentials': json.dumps({'key': 'citibank_wallet_key'}),
        'pool': pool_['handle'],
        'role': 'TRUST_ANCHOR'
    }

    await getting_verinym(steward, citibank)

    print("\n\n=======================================")
    print("==               Part B              ==")
    print("---------------------------------------")
    ################################################

    print("\n============================================")
    print("===            Credential Schemas         ==")
    print("============================================")
    print("\n------------------------------------------------------------")
    print("\"Government\" creating transcript schema for PropertyDetails ")
    print("--------------------------------------------------------------")
    print("\"Government\" -> Create \"PropertyDetails\" Schema")
    transcript1 = {
		'name': 'PropertyDetails',
		'version': '1.2',
		'attributes': ['owner_first_name', 'owner_last_name','address_of_property', 'owner_since_year', 'property_value_estimate']
	}
    (government['transcript_schema_id_1'], government['transcript_schema_1']) = \
        await anoncreds.issuer_create_schema(government['did'], transcript1['name'], transcript1['version'],
                                             json.dumps(transcript1['attributes']))
    
    transcript_schema_id_1 = government['transcript_schema_id_1']

    print("Schema_id: ", government['transcript_schema_id_1'], "\nSchema: ", government['transcript_schema_1'])

    print("\"Government\" -> Send \"PropertyDetails\"  Schema to Ledger")
    schema_request = await ledger.build_schema_request(government['did'], government['transcript_schema_1'])
    await ledger.sign_and_submit_request(government['pool'], government['wallet'], government['did'], schema_request)

    print("-------------------------------------------------------------")
    print("\"Government\" creating transcript schema for BonafideStudent")
    print("-------------------------------------------------------------")

    print("\"Government\" -> Create \"BonafideStudent\" Schema")
    transcript2 = {
		'name': 'BonafideStudent',
		'version': '1.2',
		'attributes': ['student_first_name', 'student_last_name','course_name', 'student_since_year', 'department']
	}
    (government['transcript_schema_id_2'], government['transcript_schema_2']) = \
        await anoncreds.issuer_create_schema(government['did'], transcript2['name'], transcript2['version'],
                                             json.dumps(transcript2['attributes']))
    
    transcript_schema_id_2 = government['transcript_schema_id_2']

    print("Schema_id: ", government['transcript_schema_id_2'], "\nSchema: ", government['transcript_schema_2'])

    print("\"Government\" -> Send \"BonafideStudent\" Schema to Ledger")
    schema_request = await ledger.build_schema_request(government['did'], government['transcript_schema_2'])
    await ledger.sign_and_submit_request(government['pool'], government['wallet'], government['did'], schema_request)

    print("-------------------------------------------------------------- ")

    print("\n============================================")
    print("===          Credential Definitions       ==")
    print("============================================")

    print("\n-------------------------------------------------------------")
    print("\"Government\" creating PropertyDetails Credential Definition ")
    print("--------------------------------------------------------------")

    print("\"Government\" -> Get \"PropertyDetails\" Schema from Ledger")

    get_schema_request_1 = await ledger.build_get_schema_request(government['did'], transcript_schema_id_1)
    get_schema_response_1 = await ensure_previous_request_applied(
        government['pool'], get_schema_request_1, lambda response: response['result']['data'] is not None)
    (government['transcript_schema_id'], government['transcript_schema']) = await ledger.parse_get_schema_response(get_schema_response_1)

   
    print("\"Government\" -> Create and store in Wallet \"PropertyDetails\" Credential Definition")
    transcript_cred_def_1 = {
        'tag': 'TAG1',
        'type': 'CL',
        'config': {"support_revocation": False}
    }
    (government['transcript_cred_def_id'], government['transcript_cred_def']) = \
        await anoncreds.issuer_create_and_store_credential_def(government['wallet'], government['did'],
                                                               government['transcript_schema'], transcript_cred_def_1['tag'],
                                                               transcript_cred_def_1['type'],
                                                               json.dumps(transcript_cred_def_1['config']))
    print(government['transcript_cred_def'])

    print("\"Government\" -> Send  \"PropertyDetails\" Credential Definition to Ledger")

    cred_def_request_1 = await ledger.build_cred_def_request(government['did'], government['transcript_cred_def'])
    await ledger.sign_and_submit_request(government['pool'], government['wallet'], government['did'], cred_def_request_1)

    print("------------------------------------------------------------------")
    print("\"IIT Kharagpur\" creating BonafideStudent Credential Definition ")
    print("------------------------------------------------------------------")

    print("\"IIT Kharagpur\" -> Get \"BonafideStudent\" Schema from Ledger")

    get_schema_request_2 = await ledger.build_get_schema_request(iitkgp['did'], transcript_schema_id_2)
    get_schema_response_2 = await ensure_previous_request_applied(
        iitkgp['pool'], get_schema_request_2, lambda response: response['result']['data'] is not None)
    (iitkgp['transcript_schema_id'], iitkgp['transcript_schema']) = await ledger.parse_get_schema_response(get_schema_response_2)

    print("\"IIT Kharagpur\" -> Create and store in Wallet \"BonafideStudent\" Credential Definition")
    transcript_cred_def_2 = {
        'tag': 'TAG1',
        'type': 'CL',
        'config': {"support_revocation": False}
    }
    (iitkgp['transcript_cred_def_id'], iitkgp['transcript_cred_def']) = \
        await anoncreds.issuer_create_and_store_credential_def(iitkgp['wallet'], iitkgp['did'],
                                                               iitkgp['transcript_schema'], transcript_cred_def_2['tag'],
                                                               transcript_cred_def_2['type'],
                                                               json.dumps(transcript_cred_def_2['config']))

    print(iitkgp['transcript_cred_def'])

    print("\"IIT Kharagpur\" -> Send  \"BonafideStudent\" Credential Definition to Ledger")

    cred_def_request_2 = await ledger.build_cred_def_request(iitkgp['did'], iitkgp['transcript_cred_def'])

    await ledger.sign_and_submit_request(iitkgp['pool'], iitkgp['wallet'], iitkgp['did'], cred_def_request_2)

    print("------------------------------------------------------------------")

    print("\n\n=======================================")
    print("==               Part C              ==")
    print("---------------------------------------")
    
    ##################################################################################################

    print("\n---------------------------------------")
    print("           Setting up \"Sunil\"          ")
    print("----------------------------------------")

    sunil = {
        'name': 'Sunil',
        'wallet_config': json.dumps({'id': 'sunil_wallet'}),
        'wallet_credentials': json.dumps({'key': 'sunil_wallet_key'}),
        'pool': pool_['handle'],
    }
    await create_wallet(sunil)
    (sunil['did'], sunil['key']) = await did.create_and_store_my_did(sunil['wallet'], "{}")
    print("\"Sunil\" -> Create and store \"Sunil\" Master Secret in Wallet")
    sunil['master_secret_id'] = await anoncreds.prover_create_master_secret(sunil['wallet'], None)

    print("\n===================================================")
    print("===  PropertyDetails Transcript With Government   ==")
    print("====================================================")

    print("\n---------------------------------------------------")
    print(' Government creates PropertyDetails credential offer ')
    print("-----------------------------------------------------")
    print("\"Government\" -> Create \"PropertyDetails\" Credential Offer for Sunil")
    government['transcript_cred_offer'] = \
        await anoncreds.issuer_create_credential_offer(government['wallet'], government['transcript_cred_def_id'])

    print("\"Government\" -> Send \"PropertyDetails\" Credential Offer to Sunil")
    
    # Over Network 
    sunil['property_cred_offer'] = government['transcript_cred_offer']

    print("-----------------------------------------------------")
    print(' Sunil prepares a PropertyDetails credential request ')
    print("-----------------------------------------------------")

    transcript_cred_offer_object = json.loads(sunil['property_cred_offer'])

    sunil['property_schema_id'] = transcript_cred_offer_object['schema_id']
    sunil['property_cred_def_id'] = transcript_cred_offer_object['cred_def_id']

    print("\"Sunil\" -> Get \"Government PropertyDetails\" Credential Definition from Ledger")
    (sunil['gov_transcript_cred_def_id'], sunil['gov_transcript_cred_def']) = \
        await get_cred_def(sunil['pool'], sunil['did'], sunil['property_cred_def_id'])

    print("\"Sunil\" -> Create \"PropertyDetails\" Credential Request for Government")
    (sunil['property_cred_request'], sunil['property_cred_request_metadata']) = \
        await anoncreds.prover_create_credential_req(sunil['wallet'], sunil['did'],
                                                     sunil['property_cred_offer'],
                                                     sunil['gov_transcript_cred_def'],
                                                     sunil['master_secret_id'])

    print("\"Sunil\" -> Send \"PropertyDetails\" Credential Request to Government")

    # Over Network
    government['transcript_cred_request'] = sunil['property_cred_request']

    print("----------------------------------------")
    print(' Government issues credential to Sunil ')
    print("---------------------------------------")
    print("\"Government\" -> Create \"PropertyDetails\" Credential for Sunil")
    government['sunil_transcript_cred_values'] = json.dumps({
        "owner_first_name": {"raw": "Sunil", "encoded": "1139481716457488690172217916278103335"},
        "owner_last_name": {"raw": "Dey", "encoded": "5321642780241790123587902456789123452"},
        "address_of_property": {"raw": "M G Road, Chennai", "encoded": "12434523576212321"},
        "owner_since_year": {"raw": "2005", "encoded": "2005"},
        "property_value_estimate": {"raw": "1000000", "encoded": "1000000"},
    })
    government['transcript_cred'], _, _ = \
        await anoncreds.issuer_create_credential(government['wallet'], government['transcript_cred_offer'],
                                                 government['transcript_cred_request'],
                                                 government['sunil_transcript_cred_values'], None, None)

    print(government['transcript_cred'])
    print("\"Government\" -> Send \"PropertyDetails\" Credential to Sunil")
   
    # Over the network
    sunil['property_cred'] = government['transcript_cred']

    print("\"Sunil\" -> Store \"PropertyDetails\" Credential from Government")
    _, sunil['property_cred_def'] = await get_cred_def(sunil['pool'], sunil['did'],
                                                         sunil['property_cred_def_id'])

    await anoncreds.prover_store_credential(sunil['wallet'], None, sunil['property_cred_request_metadata'],
                                            sunil['property_cred'], sunil['property_cred_def'], None)

    print("----------------------------------------------------------------")

    print("\n==================================================")
    print("=== BonafideStudent Transcript with IIT Kharagpur ==")
    print("====================================================") 
    
    print("\n-------------------------------------------------------")
    print(' IIT Kharagpur creates BonafideStudent credential offer ')
    print("--------------------------------------------------------")

    print("\"IIT Kharagpur\" -> Create \"BonafideStudent\" Credential Offer for Sunil")
    iitkgp['transcript_cred_offer'] = \
        await anoncreds.issuer_create_credential_offer(iitkgp['wallet'], iitkgp['transcript_cred_def_id'])

    print("\"IIT Kharagpur\" -> Send \"BonafideStudent\" Credential Offer to Sunil")
    
    # Over Network 
    sunil['bonafide_cred_offer'] = iitkgp['transcript_cred_offer']

    print("--------------------------------------------------------")
    print('  Sunil prepares a BonafideStudent credential request   ')
    print("--------------------------------------------------------")

    transcript_cred_offer_object = json.loads(sunil['bonafide_cred_offer'])

    sunil['bonafide_schema_id'] = transcript_cred_offer_object['schema_id']
    sunil['bonafide_cred_def_id'] = transcript_cred_offer_object['cred_def_id']

    print("\"Sunil\" -> Get \"IIT Kharagpur BonafideStudent\" Credential Definition from Ledger")
    (sunil['iitkgp_transcript_cred_def_id'], sunil['iitkgp_transcript_cred_def']) = \
        await get_cred_def(sunil['pool'], sunil['did'], sunil['bonafide_cred_def_id'])

    print("\"Sunil\" -> Create \"BonafideStudent\" Credential Request for IIT Kharagpur")
    (sunil['bonafide_cred_request'], sunil['bonafide_cred_request_metadata']) = \
        await anoncreds.prover_create_credential_req(sunil['wallet'], sunil['did'],
                                                     sunil['bonafide_cred_offer'],
                                                     sunil['iitkgp_transcript_cred_def'],
                                                     sunil['master_secret_id'])

    print("\"Sunil\" -> Send \"BonafideStudent\" Credential Request to IIT Kharagpur")

    # Over Network
    iitkgp['transcript_cred_request'] = sunil['bonafide_cred_request']

    print("----------------------------------------------")
    print('   IIT Kharagpur issues credential to Sunil   ')
    print("----------------------------------------------")
    print("\"IIT Kharagpur\" -> Create \"BonafideStudent\" Credential for Sunil")
    iitkgp['sunil_transcript_cred_values'] = json.dumps({
        "student_first_name": {"raw": "Sunil", "encoded": "1139481716457488690172217916278103335"},
        "student_last_name": {"raw": "Dey", "encoded": "5321642780241790123587902456789123452"},
        "course_name": {"raw": "Mtech", "encoded": "12434523576212321"},
        "student_since_year": {"raw": "2021", "encoded": "2021"},
        "department": {"raw": "Computer Science and Engineering", "encoded": "3124141231422543541"},
    })
    iitkgp['transcript_cred'], _, _ = \
        await anoncreds.issuer_create_credential(iitkgp['wallet'], iitkgp['transcript_cred_offer'],
                                                 iitkgp['transcript_cred_request'],
                                                 iitkgp['sunil_transcript_cred_values'], None, None)

    print(iitkgp['transcript_cred'])
    print("\"IIT Kharagpur\" -> Send \"BonafideStudent\" Credential to Sunil")
    
    # Over the network
    sunil['bonafide_cred'] = iitkgp['transcript_cred']

    print("\"Sunil\" -> Store \"BonafideStudent\" Credential from IIT Kharagpur")
    _, sunil['bonafide_cred_def'] = await get_cred_def(sunil['pool'], sunil['did'],
                                                         sunil['bonafide_cred_def_id'])

    await anoncreds.prover_store_credential(sunil['wallet'], None, sunil['bonafide_cred_request_metadata'],
                                            sunil['bonafide_cred'], sunil['bonafide_cred_def'], None)

    print("----------------------------------------------------------------")
    

    print("\n\n=======================================")
    print("==               Part D              ==")
    print("---------------------------------------")
   
    print("\n------------------------------------------------------------------------------")
    print('Creating Loan application request (presentaion request) --- validator - CitiBank')
    print("--------------------------------------------------------------------------------")
    print("\"citibank\" -> Create \"Job-Application\" Proof Request")
    nonce = await anoncreds.generate_nonce()
    citibank['loan_application_proof_request'] = json.dumps({
        'nonce': nonce,
        'name': 'Loan-Application',
        'version': '0.1',
        'requested_attributes': {
            'attr1_referent': {
                'name': 'first_name'
            },
            'attr2_referent': {
                'name': 'last_name'
            },
            'attr3_referent': {
                'name': 'course_name',
                'restrictions': [{'cred_def_id': iitkgp['transcript_cred_def_id']}]
            },
            'attr4_referent': {
                'name': 'address_of_property',
                'restrictions': [{'cred_def_id': government['transcript_cred_def_id']}]
            },
            'attr5_referent': {
                'name': 'owner_since_year',
                'restrictions': [{'cred_def_id': government['transcript_cred_def_id']}]
            }
        },
        'requested_predicates': {
            'predicate1_referent': {
                'name': 'student_since_year',
                'p_type': '>=',
                'p_value': 2021,
                'restrictions': [{'cred_def_id': iitkgp['transcript_cred_def_id']}]
            },
            'predicate2_referent': {
                'name': 'property_value_estimate',
                'p_type': '>=',
                'p_value': 400000,
                'restrictions': [{'cred_def_id': government['transcript_cred_def_id']}]
            }
        }
    })

    print("\"CitiBank\" -> Send \"Loan-Application\" Proof Request to Sunil")

    # Over Network
    sunil['loan_application_proof_request'] = citibank['loan_application_proof_request']

    print(sunil['loan_application_proof_request'])
    print("----------------------------------------------------------------")

    print("\"Sunil\" -> Get credentials for \"Loan-Application\" Proof Request")

    search_for_loan_application_proof_request = json.loads(\
        await anoncreds.prover_get_credentials_for_proof_req(sunil['wallet'], sunil['loan_application_proof_request']))
    
    print(search_for_loan_application_proof_request)
    print("-----------------------------------------------------------------")
    
    cred_for_attr3 = search_for_loan_application_proof_request['attrs']['attr3_referent'][0]['cred_info']
    cred_for_attr4 = search_for_loan_application_proof_request['attrs']['attr4_referent'][0]['cred_info']
    cred_for_attr5 = search_for_loan_application_proof_request['attrs']['attr5_referent'][0]['cred_info']
    cred_for_predicate1 = search_for_loan_application_proof_request['predicates']['predicate1_referent'][0]['cred_info']
    cred_for_predicate2 = search_for_loan_application_proof_request['predicates']['predicate2_referent'][0]['cred_info']

    sunil['creds_for_loan_application_proof'] = {cred_for_attr3['referent']: cred_for_attr3,
                                                 cred_for_attr4['referent']: cred_for_attr4,
                                                 cred_for_attr5['referent']: cred_for_attr5,
                                                 cred_for_predicate1['referent']: cred_for_predicate1,
                                                 cred_for_predicate2['referent']: cred_for_predicate2}


    sunil['schemas_for_loan_application'], sunil['cred_defs_for_loan_application'], \
    sunil['revoc_states_for_loan_application'] = \
        await prover_get_entities_from_ledger(sunil['pool'], sunil['did'],
                                              sunil['creds_for_loan_application_proof'], sunil['name'])

    print("\"Sunil\" -> Create \"Loan-Application\" Proof")
    sunil['loan_application_requested_creds'] = json.dumps({
        'self_attested_attributes': {
            'attr1_referent': 'Sunil',
            'attr2_referent': 'Dey',
        },
        'requested_attributes': {
            'attr3_referent': {'cred_id': cred_for_attr3['referent'], 'revealed': True},
            'attr4_referent': {'cred_id': cred_for_attr4['referent'], 'revealed': True},
            'attr5_referent': {'cred_id': cred_for_attr5['referent'], 'revealed': True},
        },
        'requested_predicates': {
             'predicate1_referent': {'cred_id': cred_for_predicate1['referent']},
             'predicate2_referent': {'cred_id': cred_for_predicate2['referent']},
        }
    })

    sunil['loan_application_proof'] = \
        await anoncreds.prover_create_proof(sunil['wallet'], sunil['loan_application_proof_request'],
                                            sunil['loan_application_requested_creds'], sunil['master_secret_id'],
                                            sunil['schemas_for_loan_application'],
                                            sunil['cred_defs_for_loan_application'],
                                            sunil['revoc_states_for_loan_application'])

    print("\"Sunil\" -> Send \"Loan-Application\" Proof to Citibank")

    # Over Network
    citibank['loan_application_proof'] = sunil['loan_application_proof'] 

    print("--------------------------------------------------------------")
    print('       CitiBank Validating the verifiable presentation        ')
    print("--------------------------------------------------------------")
    loan_application_proof_object = json.loads(citibank['loan_application_proof'])

    citibank['schemas_for_loan_application'], citibank['cred_defs_for_loan_application'], \
    citibank['revoc_ref_defs_for_loan_application'], citibank['revoc_regs_for_loan_application'] = \
        await verifier_get_entities_from_ledger(citibank['pool'], citibank['did'],
                                                loan_application_proof_object['identifiers'], citibank['name'])

    print("\"CitiBank\" -> Verify \"Loan-Application\" Proof from Sunil")
    assert 'Mtech' == loan_application_proof_object['requested_proof']['revealed_attrs']['attr3_referent']['raw']
    assert 'M G Road, Chennai' == loan_application_proof_object['requested_proof']['revealed_attrs']['attr4_referent']['raw']
    assert '2005' == loan_application_proof_object['requested_proof']['revealed_attrs']['attr5_referent']['raw']
    assert 'Sunil' == loan_application_proof_object['requested_proof']['self_attested_attrs']['attr1_referent']
    assert 'Dey' == loan_application_proof_object['requested_proof']['self_attested_attrs']['attr2_referent']

    assert await anoncreds.verifier_verify_proof(citibank['loan_application_proof_request'], citibank['loan_application_proof'],
                                                 citibank['schemas_for_loan_application'],
                                                 citibank['cred_defs_for_loan_application'],
                                                 citibank['revoc_ref_defs_for_loan_application'],
                                                 citibank['revoc_regs_for_loan_application'])
    print("\"CitiBank\" -> \"Loan-Application\" by Sunil is Verified")
    print("----------------------------------------------------------------")


loop = asyncio.get_event_loop()
loop.run_until_complete(run())