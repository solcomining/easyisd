import os
import re
import requests
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode

class GalaxyHarvester:

    def download_xml(self, galaxy_id, output_path):
        url = f"https://galaxyharvester.net/exports/current{galaxy_id}.xml"
        date_format = "%a, %d %b %Y %H:%M:%S %z"

        def parse_xml(path):
            tree = ET.parse(path)
            xml_root = tree.getroot()
            galaxy_name = xml_root.find(".//galaxy").text

            # GH export creation time always 0800 UTC
            as_of_date = xml_root.attrib["as_of_date"]
            gh_export_dt = datetime.strptime(as_of_date, date_format)
            gh_export_local_dt = gh_export_dt.astimezone()
            as_of_label = f"{galaxy_name} as of {gh_export_local_dt.strftime(date_format)} (local time)"

            return xml_root, as_of_label, galaxy_name, gh_export_dt

        # GH export cutover time 0800 UTC
        now_dt = datetime.now(timezone.utc)
        gh_cutover_dt = datetime(
            year=now_dt.year,
            month=now_dt.month,
            day=now_dt.day,
            hour=8, minute=0, second=4,
            tzinfo=timezone.utc
        )

        # determine latest valid GH export date
        if now_dt < gh_cutover_dt:
            latest_valid_date = (now_dt - timedelta(days=1)).date()
        else:
            latest_valid_date = now_dt.date()

        # use local file if it matches the latest valid GH export date
        if os.path.exists(output_path):
            try:
                xml_root, as_of_label, galaxy_name, gh_export_dt = parse_xml(output_path)

                if gh_export_dt.date() == latest_valid_date:
                    return xml_root, as_of_label, galaxy_name

            except Exception as e:
                print(f"Error: Could not parse existing Galaxy Harvester data export\n{e}")

        # or download fresh copy
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

        except Exception as e:
            print(f"Error: Could not download Galaxy Harvester data export\n{e}")
            return

        # and parse
        try:
            xml_root, as_of_label, galaxy_name, gh_export_dt = parse_xml(output_path)
            return xml_root, as_of_label, galaxy_name
        except Exception as e:
            print(f"Error: Could not parse downloaded Galaxy Harvester data export\n{e}")
            return

    def parse_xml_resources(self, xml_root):
        resources = []

        for res in xml_root.findall("resource"):
            name = res.findtext("name")
            galaxy = res.find("galaxy").text
            enter_date = res.findtext("enter_date")
            resource_type = res.findtext("resource_type")
            resource_type_id = res.find('resource_type').attrib['id']
            group_id = res.findtext("group_id")

            stats = {stat.tag: stat.text for stat in res.find("stats")}
            planets = [p.text for p in res.find("planets").findall("planet")]

            resources.append({
                "name": name.capitalize(),
                "galaxy": galaxy,
                "enter_date": enter_date,
                "resource_type": resource_type,
                "resource_type_id": resource_type_id,
                "group_id": group_id,
                "stats": stats,
                "planets": planets
            })

        return resources

    def gh_login(self, gh_user, gh_pass):
        # see https://github.com/pwillworth/galaxyharvester/wiki/authUser
        if not gh_user:
            gh_user = input("Enter your username: ")
            if not gh_user:
                print("Error: Username is required.")
                return

        if not gh_pass:
            gh_pass = input("Enter your password: ")
            if not gh_pass:
                print("Error: Password is required.")
                return

        url = "https://galaxyharvester.net/authUser.py"
        params = {
            "loginu": gh_user,
            "passu": gh_pass
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            content_str = response.text.strip()
        except Exception as e:
            print(f"Error: {e}")
            return

        if content_str.startswith("success-"):
            token = content_str[len("success-"):]
            print(f"Login succeeded for {gh_user}")
            return token

        print(f"Error: Login failed for {gh_user}")
        return

    def filter_spawn_names(self, xml_root, parsed_spawns):
        parsed_names = set(spawn.get('name', '').strip().lower() for spawn in parsed_spawns)
        xml_names = set(resource.find('name').text.strip().lower() for resource in xml_root.findall('.//resource'))
        only_in_parsed = parsed_names - xml_names

        # all names in mails, and potentially new names in mails
        return sorted(parsed_names), sorted(only_in_parsed)

    def filter_expired_names(self, parsed_spawns, xml_root, parsed_names):
        # we don't have total information and we want to avoid mistakes
        # we figure out the info we DO have, and make decisions based on that
        # i.e don't mark Naboo Fiber as expired if we didn't survey Naboo using a chemical tool
        # all of this could be avoided by querying GH before each submit, but that doubles time taken

        # these all correspond to the group_id tag in the XML data export
        CHEMICAL_GROUPS = ["fiberplast", "fuel_petrochem_liquid", "petrochem_inert"]
        GAS_GROUPS      = ["gas_inert", "gas_reactive"]
        SOLAR_GROUPS    = ["energy_renewable_unlimited_solar"]
        WATER_GROUPS    = ["water"]
        WIND_GROUPS     = ["energy_renewable_unlimited_wind"]

        FLORA_GROUPS = [
            "corn_domesticated", "corn_wild", "fruit_berries", "fruit_flowers", "fruit_fruits",
            "oats_domesticated", "oats_wild", "rice_domesticated", "rice_wild",
            "softwood", "softwood_evergreen", "vegetable_beans", "vegetable_fungi",
            "vegetable_greens", "vegetable_tubers", "wheat_domesticated", "wheat_wild", "wood_deciduous"
        ]
        
        MINERAL_GROUPS = [
            "aluminum", "copper", "iron", "steel", "fuel_petrochem_solid", "radioactive",
            "gemstone_armophous", "gemstone_crystalline",
            "ore_carbonate", "ore_extrusive", "ore_intrusive", "ore_siliclastic"
        ]
        
        JTL_TYPES = [
            "aluminum_perovskitic", "copper_borocarbitic", "fiberplast_gravitonic",
            "gas_reactive_organometallic","ore_siliclastic_fermionic", "radioactive_polymetric",
            "steel_bicorbantium", "steel_arveshian"
        ]

        # determine which groups were surveyed by the droids
        tools_used = {spawn["tool"] for spawn in parsed_spawns}
        total_groups = []
        if "chemical" in tools_used:
            total_groups += CHEMICAL_GROUPS
        if "flora" in tools_used:
            total_groups += FLORA_GROUPS
        if "gas" in tools_used:
            total_groups += GAS_GROUPS
        if "mineral" in tools_used:
            total_groups += MINERAL_GROUPS
        if "solar" in tools_used:
            total_groups += SOLAR_GROUPS
        if "water" in tools_used:
            total_groups += WATER_GROUPS
        if "wind" in tools_used:
            total_groups += WIND_GROUPS

        # determine which planets were surveyed by the droids
        tool_planets = {}
        for spawn in parsed_spawns:
            tool = spawn["tool"]
            planet = spawn["planet"].strip().lower()

            if tool not in tool_planets:
                tool_planets[tool] = set()

            tool_planets[tool].add(planet)

        # determine which types were surveyed in gh format like copper_polysteel
        parsed_types = {spawn['resource_type_id'] for spawn in parsed_spawns}

        # if the emails are newer than the xml data export, expired names are those found only in the data export.
        expired_names = []
        for resource in xml_root.findall('resource'):
            name           = resource.findtext('name', '').strip().lower()
            restype        = resource.find('resource_type')     # Polysteel Copper
            restype_id     = restype.get('id')                  # copper_polysteel
            group_id       = resource.findtext('group_id', '')  # copper
            planets_xml    = resource.findall('.//planet')
            planets_remote = [planet.text.strip().lower().replace(" ", "") for planet in planets_xml] # yavin 4 to yavin4

            # skip if we dont have any survey info for this res group
            if group_id not in total_groups:
                continue

            # determine which tool would have surveyed this resource
            xml_tool = "unknown"
            if group_id in CHEMICAL_GROUPS:
                xml_tool = "chemical"
            elif group_id  in FLORA_GROUPS:
                xml_tool = "flora"
            elif group_id  in GAS_GROUPS:
                xml_tool = "gas"
            elif group_id  in MINERAL_GROUPS:
                xml_tool = "mineral"
            elif group_id  in SOLAR_GROUPS:
                xml_tool = "solar"
            elif group_id  in WATER_GROUPS:
                xml_tool = "water"
            elif group_id  in WIND_GROUPS:
                xml_tool = "wind"

            # skip if we don't have survey info for the planet this res was found on
            if not set(planets_remote) & set(tool_planets.get(xml_tool, set())):
                continue

            # skip if we don't have a new spawn of these same types
            if group_id in FLORA_GROUPS and restype_id not in parsed_types:
                continue

            if restype_id in JTL_TYPES and restype_id not in parsed_types:
                continue

            if group_id == "energy_renewable_unlimited_solar" and restype_id not in parsed_types:
                continue

            if group_id == "energy_renewable_unlimited_wind" and restype_id not in parsed_types:
                continue

            if group_id == "fiberplast" and restype_id not in parsed_types:
                continue

            if group_id == "water" and restype_id not in parsed_types:
                continue

            # now we can more safely say that this res spawn has expired
            # we only need the name to submit to GH as expired
            if name not in parsed_names:
                expired_names.append(name)

        return sorted(expired_names)

    def make_new_urls(self, new_spawns, galaxy_id):
        new_spawns = sorted(new_spawns, key=lambda s: s.get("name", "").lower())
        new_urls = []

        # remove empty parameters to ease load on GH, maybe?
        remove_empty = lambda url: (
            re.sub(r'([?&])[^=]+=(?=&|$)', '', url)      # remove empty key=
            .replace('?&', '?')                          # normalize ?&
            .replace('&&', '&')                          # normalize &&
            .rstrip('?&')                                # remove trailing ? or &
        )

        for spawn in new_spawns:
            resname = spawn.get("name")
            stats = spawn.get("stats", {})
            planet = spawn.get("planet")
            gh_restype = spawn.get("resource_type_id")

            ER, CR, CD, DR = stats.get("ER", ""), stats.get("CR", ""), stats.get("CD", ""), stats.get("DR", "")
            FL, HR, MA = stats.get("FL", ""), stats.get("HR", ""), stats.get("MA", "")
            PE, OQ, SR, UT = stats.get("PE", ""), stats.get("OQ", ""), stats.get("SR", ""), stats.get("UT", "")

            url = (
                f"https://galaxyharvester.net/postResource.py?galaxy={galaxy_id}"
                f"&planet={planet}&resName={resname}&resType={gh_restype}"
                f"&ER={ER}&CR={CR}&CD={CD}&DR={DR}&FL={FL}&HR={HR}&MA={MA}&PE={PE}&OQ={OQ}&SR={SR}&UT={UT}"
            )

            # apply regex cleanup
            url = remove_empty(url)
            new_urls.append(url)

        return new_urls

    def submit_new(self, urls, token):
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        payload = {"gh_sid": token}
        encoded_payload = urlencode(payload)

        new_count = 0
        oq_total = 0
        request_count = 0
        start_time = time.perf_counter()

        for url in urls:
            try:
                response = requests.post(url, data=encoded_payload, headers=headers)
                decoded_content = response.text
                request_count += 1

                try:
                    root = ET.fromstring(decoded_content)
                    rt = root.find("resultText")
                    raw_text = rt.text if rt is not None else "No resultText found"
                except ET.ParseError:
                    raw_text = "Invalid XML"

                result_text = raw_text.strip().capitalize()
                result_text = " ".join(result_text.split()) # remove double spaces

                now = datetime.now().strftime('%H:%M:%S')
                print(f"{now} {result_text}")

                if "1st entry" in decoded_content:
                    new_count += 1
                    try:
                        oq_value = url.split("OQ=")[1].split("&")[0]
                        oq_total += int(oq_value)
                    except Exception:
                        pass

            except Exception as e:
                print(f"Error: {e}")

        elapsed = time.perf_counter() - start_time
        rps = request_count / elapsed if elapsed > 0 else 0
        oq_average = oq_total / new_count if new_count > 0 else 0

        print(f"\nGalaxy Harvester has been updated. {new_count} new resources were found, "
              f"with an OQ average of {oq_average:.0f}.")
        print(f"http requests: {request_count}, time: {elapsed:.0f}s, rate: {rps:.2f} req/s")

        return new_count, oq_average

    def submit_expired(self, names, token, galaxy_id):
        url = "https://galaxyharvester.net/markUnavailable.py"
        expired_count = 0
        request_count = 0
        start_time = time.perf_counter()

        for name in names:
            payload = {
                "gh_sid": token,
                "galaxy": galaxy_id,
                "planets": "all",
                "spawn": name
            }

            try:
                encoded_payload = urlencode(payload)
                response = requests.post(
                    url,
                    data=encoded_payload,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                decoded = response.text.strip()
                result_text = " ".join(decoded.split()) # remove double spaces

                now = datetime.now().strftime('%H:%M:%S')
                print(f"{now} {name.capitalize()} {result_text.lower()}")

                if "unavailable" in result_text:
                    expired_count += 1

                request_count += 1

            except Exception as e:
                print(f"Error: {e}")

        elapsed = time.perf_counter() - start_time
        rps = request_count / elapsed if elapsed > 0 else 0

        print(f"\nGalaxy Harvester has been updated. {expired_count} resources were marked as unavailable.")
        print(f"http requests: {request_count}, time: {elapsed:.0f}s, rate: {rps:.2f} req/s")

        return expired_count

    def send_to_discord_webhooks(self, new_count, oq_average):
        username = "ISD-Reporter"

        webhook_urls = [
            "https://discord.com/api/webhooks/11111111/abcdefgh",
            "https://discord.com/api/webhooks/22222222/abcdefgh",
            "https://discord.com/api/webhooks/33333333/abcdefgh",
            "https://discord.com/api/webhooks/44444444/abcdefgh",
        ]

        message = (
            f"[Galaxy Harvester](https://galaxyharvester.net/) has been updated.\n"
            f"||{new_count} new resources were found, with an OQ average of {oq_average:.0f}.||"
        )

        payload = {"username": username, "content": message}

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"     # 403 error if no user-agent
        }

        for url in webhook_urls:
            now = datetime.now().strftime('%H:%M:%S')
            try:
                response = requests.post(url, json=payload, headers=headers)
                print(f"{now} {url[0:53]}... {response.status_code}")

            except Exception as e:
                print(f"Error sending to {url}\n{e}")

    def get_spawn_details(self, name, galaxy_id):
        # this can be used to query if a resource is known by GH
        # and to query the stat gates

        url = "https://galaxyharvester.net/getResource.py"
        params = {
            "name": name,
            "galaxy": galaxy_id
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"HTTP error: {e}")
            return None

        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as e:
            print(f"XML parse error: {e}")
            return None

        result = root.find("result")
        if result is None:
            print("No <result> element found")
            return None

        # convert all XML children into a dict
        data = {child.tag: child.text for child in result}

        # normalize numeric fields
        numeric_fields = [
            "spawnID", "CR", "CRmin", "CRmax", "CD", "CDmin", "CDmax",
            "DR", "DRmin", "DRmax", "FL", "FLmin", "FLmax", "HR", "HRmin", "HRmax",
            "MA", "MAmin", "MAmax", "PE", "PEmin", "PEmax", "OQ", "OQmin", "OQmax",
            "SR", "SRmin", "SRmax", "UT", "UTmin", "UTmax", "ER", "ERmin", "ERmax",
            "maxWaypointConc"
        ]

        for key in numeric_fields:
            if key in data and data[key] not in (None, ""):
                try:
                    data[key] = int(data[key])
                except ValueError:
                    pass  # leave as string if not numeric

        planets = []
        for planet in result.findall("planet"):
            planets.append({
                "id": planet.get("id"),
                "entered": planet.get("entered"),
                "enteredBy": planet.get("enteredBy")
            })

        data["planetEntries"] = planets

        return data




