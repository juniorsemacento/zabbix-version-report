import os
import logging
import argparse
import urllib3
from pyzabbix import ZabbixAPI, ZabbixAPIException

# Configuration
ZABBIX_API_KEY = "your_api_key_here"  # Replace with your actual API key
DEFAULT_ITEM_KEY = "agent.version"
DEFAULT_FILE_NAME = "ReportZabbixVersion.csv"  # CSV file will be created in the current directory

# Suppress InsecureRequestWarning messages after the first
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Initialize Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main(zabbix_url, hostgroup_ids=None):
    try:
        # Define full API endpoint
        zapi = ZabbixAPI(f"{zabbix_url}/api_jsonrpc.php")
        zapi.session.verify = False  # Disable SSL verification if necessary
        
        # Use Bearer token in Authorization header
        zapi.session.headers.update({"Authorization": f"Bearer {ZABBIX_API_KEY}"})
        logging.info("Connected to Zabbix API")

        # Fetch all necessary host data in a single call
        host_filter = {"status": 0}  # Only enabled hosts
        hosts = zapi.host.get(
            output=["host", "hostid"],
            selectInterfaces=["ip"],
            groupids=hostgroup_ids if hostgroup_ids else None,
            filter=host_filter
        )
        
        if not hosts:
            logging.warning("No enabled hosts found.")
            return

        # Open file to save the report
        with open(DEFAULT_FILE_NAME, "w") as file:
            file.write("Host, IP, Zabbix Agent Version\n")

            # Process each host
            for host in hosts:
                host_name = host["host"]
                ip = host["interfaces"][0]["ip"] if host["interfaces"] else "N/A"

                # Retrieve item directly
                item = zapi.item.get(
                    output=["itemid"],
                    hostids=host["hostid"],
                    filter={"key_": DEFAULT_ITEM_KEY}
                )

                if item:
                    item_id = item[0]["itemid"]
                    history = zapi.history.get(
                        output=["value"],
                        history=1,
                        sortfield="clock",
                        sortorder="DESC",
                        limit=1,
                        itemids=[item_id]
                    )
                    
                    if history:
                        last_value = history[0]["value"]
                        file.write(f"{host_name}, {ip}, {last_value}\n")
                    else:
                        logging.warning(f"No history data for item '{DEFAULT_ITEM_KEY}' on host '{host_name}'")
                        file.write(f"{host_name}, {ip}, No data available\n")
                else:
                    logging.warning(f"No item found with key '{DEFAULT_ITEM_KEY}' on host '{host_name}'")
                    file.write(f"{host_name}, {ip}, Item key '{DEFAULT_ITEM_KEY}' not found\n")

        logging.info(f"Report saved to: {os.path.abspath(DEFAULT_FILE_NAME)}")
    
    except ZabbixAPIException as e:
        logging.error(f"Zabbix API error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Zabbix Agent Version Checker")
    parser.add_argument("zabbix_url", help="Zabbix server URL")
    parser.add_argument("--hostgroup_ids", nargs="+", type=int, help="Optional host group IDs (space-separated list)")

    args = parser.parse_args()
    
    main(args.zabbix_url, args.hostgroup_ids)
