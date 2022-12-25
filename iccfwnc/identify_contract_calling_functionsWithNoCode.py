
import logging
import re
import json
import sys
from parser import ParserError

import os
from subprocess import PIPE, Popen
import argparse
from typing import Dict, Set

from iccfwnc import solc_data

log = logging.getLogger(__name__)

def get_contract_ast_data(data):
    """
    Takes a solc AST and gets the src mappings for all the contracts defined in the top level of the ast
    :param ast: AST of the contract
    :return: The source maps
    """
    contract_ast={}
    for source in data["sources"].values():
        ast=source["ast"]
        if ast["nodeType"] == "SourceUnit":
            for child in ast["nodes"]:
                if child.get("contractKind"):
                    de=[]
                    if 'contractDependencies' in child.keys():
                        de=child['contractDependencies']

                    contract_ast[child["name"]]={'id':child['id'],
                                                 'dependency':de,
                                                 'src':child["src"],
                                                 'fullyImplemented':child['fullyImplemented']
                                                 }

        elif ast["nodeType"] == "YulBlock":
            for child in ast["statements"]:
                # source_maps.add(child["src"])
                print(f'contract srcmap error')

    return contract_ast

def get_contract_method_identifiers(data):
    contract_mi={}
    for contract_data in data["contracts"].values():
        for contract_name,contract_evm_data in contract_data.items():
            contract_mi[contract_name]=contract_evm_data['evm']['methodIdentifiers']
    return contract_mi

def get_source_code(file_path:str, srcmap:str):
        items=srcmap.split(":")
        start=int(items[0])
        length=int(items[1])

        result=''
        with open (file_path,'r') as f:
            f.seek(start,0)
            result=f.read(length)
        f.close()
        return result

def check_substring(contract1_name:str,contract2_name:str,str1_list:list,str2_list:list):

    results=[]
    for str2 in str2_list:
        for idx, line in enumerate(str1_list):
            if len(line)==0:continue
            # if str2 in line:

            if re.search(f'\s*\.\s*{str2}\s*\(',line):
                results.append(f'\t{str2}:: {idx}:: {line.strip()}')
    if len(results)>0:
        print(f'==== {contract1_name} ==== {contract2_name} ====')
        for item in results:
            print(item)

def search_strings_in_source_code(method_name:str,source_lines:list,search_str1:list,search_str2:list,search_str3:list,search_str4:list):
    """

    :param method_name:
    :param source_lines:
    :param search_str1: search strings obtained from state variables
    :param search_str2: search strings obtained from function state variables
    :param search_str3: search strings obtained from the names of unimplemented contracts
    :param search_str4: search strings obtained from the names of othr contracts

    :return:
    """
    involved_contracts=[]

    # from the state variables
    results=[]
    for values in search_str1:
        assert len(values)==3
        # assume the statements calling functions are in a line
        for idx,line in enumerate(source_lines):
            if re.search(f'\s*{values[0]}\s*.\s*{values[1]}\s*\(',line):
                results.append(f'\t{values[2]}:: {values[0]}.{values[1]}:: {line.strip()}')
                if values[2] not in involved_contracts:
                    involved_contracts.append(values[2])

    # from the function parameters
    results2 = []
    for values in search_str2:
        assert len(values) == 3
        # assume the statements calling functions are in a line
        for idx, line in enumerate(source_lines):
            if re.search(f'\s*{values[0]}\s*.\s*{values[1]}\s*\(', line):
                results2.append(f'\t{values[2]}:: {values[0]}.{values[1]}:: {line.strip()}')
                if values[2] not in involved_contracts:
                    involved_contracts.append(values[2])


    # directly check if the function contains the names of the contracts that have no code
    results3 = []
    for value in search_str3:
        # assume the statements calling functions are in a line
        for idx, line in enumerate(source_lines):
            if re.search(f'\s*{value}\s*', line):
                results3.append(f'\t{value}:: {line.strip()}')
                if value not in involved_contracts:
                    involved_contracts.append(value)

    results4 = []
    for value in search_str4:
        # assume the statements calling functions are in a line
        for idx, line in enumerate(source_lines):
            if re.search(f'\s*{value}\s*', line):
                results4.append(f'\t{value}:: {line.strip()}')
                if value not in involved_contracts:
                    involved_contracts.append(value)


    #output searching results
    if len(results)>0 or len(results2)>0 or len(results3)>0:
        print(f'==== {method_name} ====')
        if len(results)>0:
            print(f'\t-- from state variable --')
            for item in results:
                print(item)
        if len(results2)>0:
            print(f'\t-- from function parameters --')
            for item in results2:
                print(item)
        if len(results3)>0:
            print(f'\t-- from the names of the contracts not implemented --')
            for item in results3:
                print(item)
    return involved_contracts,results,results2,results3,results4

def detect_if_calling_functionsWithNoCode(file_path:str, contract_name:str, contract_method_identifiers:dict, contract_ast_data:dict,target_sv_info:dict,target_ftn_info:dict):
    target_data=contract_ast_data[contract_name]
    # source_code=get_source_code(file_path,target_data['src'])
    # source_code_lines=source_code.split('\n')

    # get contracts or interfaces that are not implemented
    contracts_not_implemented= {}
    for name,data in contract_ast_data.items():
        if str(name).__eq__(contract_name):continue
        if data['id'] in target_data['dependency']:continue
        if data['fullyImplemented']: continue
        contracts_not_implemented[name]=data['id']

    # get search strings
    search_strings_from_state_variables=[]
    for sv_name,value in target_sv_info.items():
        if value['type_id'] is not None:
            for contract_name, id in contracts_not_implemented.items():
                if value['type_id']==id:
                    for method_name in contract_method_identifiers[contract_name].keys():
                        pure_name= str(method_name).split('(')[0] if '(' in method_name else method_name
                        search_strings_from_state_variables.append([sv_name,pure_name,contract_name])

    all_contracts_involved=[]
    # get search strings by going through each functions of the target contract
    for ftn_name, data in target_ftn_info.items():
        search_strings_from_parameters=[]
        if 'parameters' in data.keys():
            parameters=data['parameters']
            for param_name,value in parameters.items():
                if value['type_id'] is not None:
                    for contract_name, id in contracts_not_implemented.items():
                        if value['type_id'] == id:
                            for method_name in contract_method_identifiers[contract_name].keys():
                                pure_name = str(method_name).split('(')[0] if '(' in method_name else method_name
                                # param_name and pure_method will actually used, contract_name is not used but kept for easy understanding
                                search_strings_from_parameters.append([param_name, pure_name,contract_name])

        # get the source code of the method
        source_code=get_source_code(file_path,data['src'])
        source_lines=source_code.split('\n')

        # search in the source code of the ethod
        call_from_sv = {}
        call_from_parameter = {}
        call_from_within_body = {}
        invoke_any_contracts = {}
        contracts_involved,re1,re2,re3,re4=search_strings_in_source_code(ftn_name,source_lines, search_strings_from_state_variables,search_strings_from_parameters,list(contracts_not_implemented.keys()),list(contract_ast_data.keys()))
        for item in contracts_involved:
            if item not in all_contracts_involved:
                all_contracts_involved.append(item)
        call_from_sv[ftn_name]=re1,
        call_from_parameter=re2
        call_from_within_body=re3
        invoke_any_contracts=re4 # contracts other than the target contract

    return all_contracts_involved,call_from_sv,call_from_parameter,call_from_within_body,invoke_any_contracts


def get_target_contract_function_ast_data(data,method_identifiers:dict,file_path:str,contract_name:str):

    def get_type_id_name(node:dict):
        type_id = None
        type_name = ''
        typeDescriptions = {}
        if 'typeDescriptions' in node.keys():
            typeDescriptions = node['typeDescriptions']
        elif 'typeName' in node.keys():
            if 'typeDescriptions' in node['typeName'].keys():
                typeDescriptions = node['typeName']['typeDescriptions']

        if len(typeDescriptions) > 0:
            type_id = typeDescriptions['typeIdentifier']
            if '$' in type_id:
                type_id = str(type_id).split('$')[-1]
                if type_id.isnumeric():
                    type_id=int(type_id)
                else:type_id=None
            else: type_id=None
            type_name = str(typeDescriptions['typeString']).split(' ')[-1]

        return type_id,type_name

    selector_to_function={} # for noeds of (0x2caf5a42ec2d6747ec696714bf913b174d94fdf0.sol	0.5.17	LexLocker), they have function selector
    pure_name_to_full_name = {}  # for nodes of Crowdsale, they does not have function selector

    for con_name,mi in method_identifiers.items():
        if con_name==contract_name:
            for ftn,selector in mi.items():
                selector_to_function[selector]=ftn
                if '(' in str(ftn):
                    pure_name=str(ftn).split('(')[0]
                else:
                    pure_name=ftn
                pure_name_to_full_name[pure_name]=ftn

    state_variables_info={}
    function_info={}
    # get the srcmap for each public/external function
    nodes_sourceUnit = data['sources'][file_path]['ast']['nodes']
    for nodes_contractDefinition in nodes_sourceUnit:
        if nodes_contractDefinition['nodeType'] == 'ContractDefinition':
            con_name = nodes_contractDefinition['name']
            if con_name==contract_name:
                for node in nodes_contractDefinition['nodes']:
                    if node['nodeType'] in ['FunctionDefinition','VariableDeclaration' ] and node['visibility'] in ['public', 'external']:
                        ftn_name = node['name']
                        if len(str(ftn_name))>0:
                            if 'stateVariable' in node.keys():
                                constant=node['constant'] if 'constant' in node.keys() else None
                                type_id,type_name=get_type_id_name(node)
                                state_variables_info[ftn_name]={
                                    'id':node['id'],
                                    'src':node['src'],
                                    'constant':constant,
                                    'type_id':type_id,
                                    'type_name':type_name,
                                    'visibility':node['visibility'],

                                }
                                continue
                            # get the full name
                            if 'functionSelector' in node.keys():
                                selector=node['functionSelector']
                                if selector in selector_to_function.keys():
                                    ftn_name=selector_to_function[selector]
                            elif ftn_name in pure_name_to_full_name.keys():
                                ftn_name=pure_name_to_full_name[ftn_name]

                            params = {}
                            parameters=node['parameters']
                            if 'parameters' in parameters.keys():
                                parameters=parameters['parameters']
                                for param in parameters:
                                    type_id, type_name = get_type_id_name(param)
                                    params[param['name']]={
                                        'id':param['id'],
                                        'src':param['src'],
                                        'constant':param['constant'],
                                        'type_id':type_id,
                                        'type_name':type_name,
                                    }



                            function_info[ftn_name]={
                                'id':node['id'],
                                'src':node['src'],
                                'parameters':params,
                                'visibility':node['visibility'],
                                'stateMutability':node['stateMutability']
                            }

                        else:
                            if 'kind' in node.keys():
                                ftn_name=node['kind']
                            elif 'isConstructor' in node.keys():
                                if node['isConstructor']:
                                    ftn_name='constructor'
                                else:ftn_name='fallback'
                            if ftn_name=='fallback':
                                function_info[ftn_name] = {
                                    'id': node['id'],
                                    'src': node['src'],
                                    'visibility': node['visibility'],
                                    'stateMutability': node['stateMutability']
                                }

    contract_len=0
    for solidity_file,contracts in data['contracts'].items():
        for contract in contracts.keys():
            if str(contract).__eq__(contract_name):
                contract_len=len(contracts[contract]['evm']['deployedBytecode']['object'])
                break



    return  state_variables_info,function_info,contract_len


def check_if_call_functionsWithNoCode( solidity_file_contract:str,solc_binary:str,solc_settings_json) :
    output = {}
    if ":" in solidity_file_contract:
        file, contract_name = solidity_file_contract.split(":")
        output['solidity_file']=str(file).split("/")[-1]
        output['contract_name']=contract_name
    else:
        print(f'No target function is specified!')
        return
    print(f'**** {str(file).split("/")[-1]}:{contract_name} ****')
    file = os.path.expanduser(file)

    # try:
    data = solc_data.get_solc_json(
        file, solc_settings_json=solc_settings_json, solc_binary=solc_binary
    )

    # get the method identifiers for all contracts in the Solidity file
    contract_mi=get_contract_method_identifiers(data)
    output['method_identifiers']=contract_mi

    # get the contract data from ast
    contract_ast_data=get_contract_ast_data(data)
    output['ast_data']=contract_ast_data

    target_sv_info,target_ftn_info,bytecode_size=get_target_contract_function_ast_data(data,contract_mi,file,contract_name)
    output['runtime_bytecode_size']=bytecode_size
    involved_contracts,call_from_sv,call_from_parameter,call_from_within_body,invoke_any_contracts\
        =detect_if_calling_functionsWithNoCode(file, contract_name, contract_mi, contract_ast_data,target_sv_info,target_ftn_info)

    output['target_sv_info']=target_sv_info
    output['target_ftn_info']=target_ftn_info
    output['call_from_sv']=call_from_sv
    output['call_from_parameters']=call_from_parameter
    output['call_from_within_body']=call_from_within_body
    output['invoke_any_contracts']=invoke_any_contracts


    target_ast_data=contract_ast_data[contract_name]

    implemented=True
    if not target_ast_data['fullyImplemented']:
        implemented=False
    output['fullyImplemented']=implemented


    # get base contracts
    base_contract_ids=target_ast_data['dependency']
    base_contracts=[]
    for d in  base_contract_ids:
        for con_name,values in contract_ast_data.items():
            if values['id']==d:
                base_contracts.append(con_name)
    output['base_contracts']=base_contracts
    output['invoke_contracts']=involved_contracts
    print(f'fully implemented:base contracts :the size of deployed bytecode: involved contract names')
    print(f'++++ {implemented}:{bytecode_size}:{base_contracts}:{involved_contracts} ++++')

    last_idx=file.rindex('.')
    with open(str(file)[0:last_idx]+".json",'w') as fw:
        json.dump(output,fw)

        fw.close()

    # for name,value in target_ftn_info.items():
    #     source_code=get_source_code(file,value['src'])
    #     print(f'==== source code of {name} ====')
    #     print(source_code)
    # for name,value in target_sv_info.items():
    #     source_code=get_source_code(file,value['src'])
    #     print(f'==== source code of {name} ====')
    #     print(source_code)

    # except ParserError as e:
    #     print(f'Error message: {str(e)}')
    # except KeyError as e:
    #
    #     print(f'Error message: {str(e)}')
    # except Exception as e:
    #     error_msg = str(e)
    #     print(f'Error message: {error_msg}')


def main():

    parser=argparse.ArgumentParser(description='find contracts using functions that have no code available in Solidity files')
    parser.add_argument('file_contract',type=str,help=" format:solidity file path:contract name")
    parser.add_argument('--solc-binary',type=str,default='solc')
    parser.add_argument('--solc-setting-json', type=str, default=None)
    parser.add_argument(
        "-v", type=int, help="log level (0-5)", metavar="LOG_LEVEL", default=3
    )


    args=parser.parse_args()
    if args.file_contract is None:
        return
    check_if_call_functionsWithNoCode(args.file_contract,args.solc_binary,args.solc_setting_json)




