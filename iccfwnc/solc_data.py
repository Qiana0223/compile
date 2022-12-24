import json
from subprocess import PIPE, Popen

def get_solc_json(file, solc_binary="solc", solc_settings_json=None):
    """
the function to execute 'solc ...' command to obtain compiled results
    :param file:
    :param solc_binary:
    :param solc_settings_json:
    :return:
    """
    cmd = [solc_binary, "--optimize", "--standard-json", "--allow-paths", "."]

    settings = json.loads(solc_settings_json) if solc_settings_json else {}
    settings.update(
        {
            "outputSelection": {
                "*": {
                    "": ["ast"],
                    "*": [
                        "metadata",
                        "evm.bytecode",
                        "evm.deployedBytecode",
                        "evm.methodIdentifiers",
                    ],
                }
            }
        }
    )
    input_json = json.dumps(
        {
            "language": "Solidity",
            "sources": {file: {"urls": [file]}},
            "settings": settings,
        }
    )

    try:
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate(bytes(input_json, "utf8"))

    except Exception:
        print(
            "Compiler not found. Make sure that solc is installed and in PATH, or set the SOLC environment variable."
        )

    out = stdout.decode("UTF-8")

    result = json.loads(out)

    for error in result.get("errors", []):
        if error["severity"] == "error":
            print(
                "Solc experienced a fatal error.\n\n%s" % error["formattedMessage"]
            )

    return result
