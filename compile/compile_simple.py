
import logging
import os
import argparse
from compile import solc_data

log = logging.getLogger(__name__)

def compiling(solidity_file_contract:str,output_folder:str) :
    if ":" in solidity_file_contract:
        file, contract_name = solidity_file_contract.split(":")
    else:
        file=solidity_file_contract

    file = os.path.expanduser(file)

    # try:

    data = solc_data.call_solc_command(file, output_folder)


def main():
    parser=argparse.ArgumentParser(description='find contracts using functions that have no code available in Solidity files')
    parser.add_argument('file_contract',type=str,help=" format:solidity file path:contract name")
    parser.add_argument('output_folder', type=str, help=" the place to hold the binary files")

    parser.add_argument('--solc-binary',type=str,default='solc')
    parser.add_argument('--solc-setting-json', type=str, default=None)
    parser.add_argument(
        "-v", type=int, help="log level (0-5)", metavar="LOG_LEVEL", default=3
    )


    args=parser.parse_args()
    if args.file_contract is None or args.output_folder is None:
        return
    compiling(args.file_contract, args.output_folder)




