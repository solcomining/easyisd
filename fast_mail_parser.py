# This is quite fast at 0.76s for 10,000 sample mails
# Most time is spent opening files, further improvements are not cross-platform

import os
import re
import shutil
import time
import mmap

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

@dataclass(slots=True)
class TransactionEntry:
    type: str               # sale, purchase, offer
    path: str
    email_id: str
    timestamp: int
    item: str
    price: int
    location: str
    buyer: Optional[str] = None
    seller: Optional[str] = None
    player: Optional[str] = None  # offerer
    vendor: Optional[str] = None

    @property
    def datetime(self) -> str:
        dt = time.localtime(self.timestamp)
        return f"{dt.tm_year % 100:02d}-{dt.tm_mon:02d}-{dt.tm_mday:02d} " \
               f"{dt.tm_hour:02d}:{dt.tm_min:02d}:{dt.tm_sec:02d}"

@dataclass(slots=True)
class InboxEntry:
    path: str
    email_id: str
    sender: str
    timestamp: int
    subject_line: str
    body: list[str]

    @property
    def datetime(self) -> str:
        dt = time.localtime(self.timestamp)
        return f"{dt.tm_year % 100:02d}-{dt.tm_mon:02d}-{dt.tm_mday:02d} " \
               f"{dt.tm_hour:02d}:{dt.tm_min:02d}:{dt.tm_sec:02d}"

class FastMailParser: # TY to Dasch for the big assist
    def __init__(self):
        self.parsed_auction     = []
        self.parsed_inbox       = []
        self.parsed_isdmails    = []

        # load resource metadata
        self.restypes = self.load_restypes("restypes.txt")

    def parse_folder(self, folder_path): 
        for entry in os.scandir(folder_path):
            if entry.is_file() and entry.name.endswith(".mail"):
                result = self.parse_file(entry.path)
                if not result:
                    continue

                if result["type"] == "auction":
                    self.parsed_auction.append(result["data"])
                elif result["type"] == "inbox":
                    self.parsed_inbox.append(result["data"])
                elif result["type"] == "isd":
                    self.parsed_isdmails.extend(result["data"])

        # sorting by timestamp now is fastest
        #self.parsed_auction.sort(key=lambda x: x.timestamp, reverse=True)
        #self.parsed_inbox.sort(key=lambda x: x.timestamp, reverse=True)

        #return self.parsed_auction, self.parsed_inbox, self.parsed_isdmails
        return self.parsed_isdmails

    def parse_file(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    content = mm.read().decode("utf-8")
        except Exception:
            return None

        lines = content.splitlines()

        if len(lines) < 3:
            return None

        if ".auctioner" in lines[1]:
            parsed = self.parse_auction_mail(lines, path)
            return {"type": "auction", "data": parsed} if parsed else None
        elif ".interplanetary survey droid" in lines[1]:
            parsed = self.parse_survey_mail(content, path)
            return {"type": "isd", "data": parsed} if parsed else None
        elif len(lines) > 4:
            parsed = self.parse_inbox_mail(lines, path)
            return {"type": "inbox", "data": parsed} if parsed else None

        return None

    def parse_auction_mail(self, lines, path):
        subject_line = lines[2]

        if "Item Offered to Vendor" in subject_line:
            return self.parse_incoming_offer(lines, path)
        elif "Vendor Item Purchased" in subject_line:
            return self.parse_purchase(lines, path)
        elif "Vendor Sale Complete" in subject_line:
            return self.parse_outgoing_sale(lines, path)
        return None

    def parse_incoming_offer(self, lines, path):
        try:
            id_line = lines[0].strip()
            ts_line = lines[3]
            offer_line = lines[4]
            location_line = lines[5]

            ts = int(ts_line.partition(":")[2].strip())

            offer_split = offer_line.split(" has offered ", 1)
            player = offer_split[0]
            remainder = offer_split[1]

            item_end = remainder.find(" to your vendor")
            item = remainder[:item_end]

            vendor_start = offer_line.find("Vendor: ") + 8
            vendor_end = offer_line.find(",", vendor_start)
            vendor = offer_line[vendor_start:vendor_end]

            price_start = offer_line.find(" for ") + 5
            price_end = offer_line.find(" credits", price_start)
            price = int(offer_line[price_start:price_end])

            loc_start = location_line.find(" at ") + 4
            loc_mid = location_line.find(", on ", loc_start)
            location = f"{location_line[loc_start:loc_mid]}, {location_line[loc_mid + 5:].rstrip('.')}"

            return TransactionEntry(
                type="offer",
                path=path,
                email_id=id_line,
                timestamp=ts,
                item=item,
                price=price,
                location=location,
                player=player,
                vendor=vendor
            )
        except Exception:
            return None

    def parse_purchase(self, lines, path):
        try:
            id_line = lines[0].strip()
            ts_line = lines[3]
            purchase_line = lines[4]
            location_line = lines[5]

            ts = int(ts_line.partition(":")[2].strip())

            auction_start = purchase_line.find('auction of "') + len('auction of "')
            auction_end = purchase_line.find('" from', auction_start)
            item = purchase_line[auction_start:auction_end]

            seller_start = purchase_line.find('from "', auction_end) + len('from "')
            seller_end = purchase_line.find('" for', seller_start)
            seller = purchase_line[seller_start:seller_end]

            price_start = purchase_line.find(" for ", seller_end) + 5
            price_end = purchase_line.find(" credits", price_start)
            price = int(purchase_line[price_start:price_end])

            loc_start = location_line.find(" at ") + 4
            loc_mid = location_line.find(", on ", loc_start)
            location = f"{location_line[loc_start:loc_mid]}, {location_line[loc_mid + 5:].rstrip('.')}"

            return TransactionEntry(
                type="purchase",
                path=path,
                email_id=id_line,
                timestamp=ts,
                item=item,
                price=price,
                location=location,
                seller=seller
            )
        except Exception:
            return None

    def parse_outgoing_sale(self, lines, path):
        try:
            id_line = lines[0].strip()
            ts_line = lines[3]
            sale_line = lines[4]
            location_line = lines[5]

            ts = int(ts_line.partition(":")[2].strip())

            sale_body = sale_line[8:]
            vendor_end = sale_body.find(" has sold ")
            vendor = sale_body[:vendor_end]

            item_start = vendor_end + len(" has sold ")
            item_end = sale_body.find(" to ", item_start)
            item = sale_body[item_start:item_end]

            buyer_start = item_end + len(" to ")
            buyer_end = sale_body.find(" for ", buyer_start)
            buyer = sale_body[buyer_start:buyer_end]

            price_start = buyer_end + len(" for ")
            price_end = sale_body.find(" credits", price_start)
            price = int(sale_body[price_start:price_end])

            loc_start = location_line.find(" at ") + 4
            loc_mid = location_line.find(", on ", loc_start)
            location = f"{location_line[loc_start:loc_mid]}, {location_line[loc_mid + 5:].rstrip('.')}"

            return TransactionEntry(
                type="sale",
                path=path,
                email_id=id_line,
                timestamp=ts,
                item=item,
                price=price,
                location=location,
                buyer=buyer,
                vendor=vendor
            )
        except Exception:
            return None

    def parse_inbox_mail(self, lines, path):
        try:
            email_id     = lines[0].strip()
            sender       = lines[1].split('.')[-1]
            subject_line = lines[2]
            ts           = lines[3].partition(":")[2].strip()
            body         = lines[4:]

            return InboxEntry(
                path=path,
                email_id=email_id,
                sender=sender,
                timestamp=int(ts),
                subject_line=subject_line,
                body=body
            )
        except Exception:
            return None

    def parse_survey_mail(self, content, path):
        lines = content.splitlines()

        # mail timestamp always UTC
        mail_ts = lines[3].partition(":")[2].strip()
        mail_dt = datetime.fromtimestamp(int(mail_ts), timezone.utc)

        # GH export always created at 0800 UTC
        # this is equivalent to parsing the XML for the as_of_date
        now_dt = datetime.now(timezone.utc)
        gh_cutover_dt = datetime(
            year=now_dt.year,
            month=now_dt.month,
            day=now_dt.day,
            hour=8, minute=0, second=0,
            tzinfo=timezone.utc
        )

        # determine latest valid GH export date
        if now_dt < gh_cutover_dt:
            latest_valid_date = (now_dt - timedelta(days=1)).date()
        else:
            latest_valid_date = now_dt.date()

        # move and disregard mails older than the latest valid GH export date
        if mail_dt.date() < latest_valid_date:
            self.move_to_oldmails(path)
            return []

        # determine the tool used from the subject line
        tool_types = ["chemical", "flora", "gas", "mineral", "solar", "water", "wind"]
        tool = next((t for t in tool_types if t in lines[2].lower()), "unknown")

        # and parse the mail for spawns
        parsed_isdmails = []
        mail_spawns = self.parse_survey_spawns(content)

        for spawn in mail_spawns:
            stats = spawn.get('stats', {})
            parsed_isdmails.append({
                'timestamp': mail_ts,
                'tool': tool,
                'planet': spawn.get('planet').rstrip(),
                'name': spawn.get('name'),
                'resource_type': spawn.get('type'),
                'resource_type_id': self.restypes.get(spawn.get('type')),
                'stats': {
                    'ER': stats.get('ER', ''),
                    'CR': stats.get('CR', ''),
                    'CD': stats.get('CD', ''),
                    'DR': stats.get('DR', ''),
                    'FL': stats.get('FL', ''),
                    'HR': stats.get('HR', ''),
                    'MA': stats.get('MA', ''),
                    'PE': stats.get('PE', ''),
                    'OQ': stats.get('OQ', ''),
                    'SR': stats.get('SR', ''),
                    'UT': stats.get('UT', '')
                },
            })

        return parsed_isdmails

    def load_restypes(self, filepath):
        # Endorian Fruit to fruit_fruits_endor
        # Resource types from mails don't always match Galaxy Harvester XML
        # e.g Kuat vs Kuati, Corellia vs Corellian, Dathomir vs Dathomirian
        # That's why there are some duplicates in restypes.txt

        lookup = {}
        try:
            with open(filepath, encoding='utf-8') as f:
                for line in f:
                    if ',' in line:
                        swg_type, gh_type = line.split(',', 1)
                        lookup[swg_type] = gh_type.strip()
        except Exception as e:
            print(f"Error: Could not load resource types from {filepath}\n{e}")

        return lookup

    def move_to_oldmails(self, path):
        path = os.path.abspath(path)
        parent = os.path.dirname(path)
        filename = os.path.basename(path)

        try:
            oldmails_folder = os.path.join(parent, "oldmails")
            os.makedirs(oldmails_folder, exist_ok=True)
        except:
            print(f"Error: Could not create oldmails subfolder. Check write permissions for the {parent} folder.")
            raise SystemExit("Goodbye")

        try:
            dest_path = os.path.join(oldmails_folder, filename)
            shutil.move(path, dest_path)
        except:
            print(f"Error: Could not move old mail to {oldmails_folder}.")
            raise SystemExit("Goodbye")

        return

    @staticmethod
    def parse_survey_spawns(email_data):
        if isinstance(email_data, str):
            planet = re.findall(r'Planet\:\s+[^\s]+\s([^\n]+)', email_data)[0]
            parts = re.split(r'Resources located\.\.\.[^\n]+[\n]+', email_data)
            data = parts[1].strip()
            lines = re.split(r'[\n]+', data)
            resources, group, resource_type = [[], None, None]
            for line in lines:
                if line.startswith("\t\t\t"):
                    resources, group, resource_type = FastMailParser.survey_reduce_set_resource_stats(line, [resources, group, resource_type])
                elif line.startswith("\t\t"):
                    resources, group, resource_type = FastMailParser.survey_reduce_init_resource(line, [resources, group, resource_type])
                elif line.startswith("\t"):
                    resources, group, resource_type = FastMailParser.survey_reduce_type(line, [resources, group, resource_type])
                else:
                    resources, group, resource_type = FastMailParser.survey_reduce_group(line, [resources, group, resource_type])
            resources = list(map(lambda resource: {**resource, 'planet': planet}, resources))
            return resources
        else:
            raise ValueError("email_data must be a string")

    @staticmethod
    def survey_reduce_group(line, acc):
        resources, _, _ = acc
        return resources, line, None

    @staticmethod
    def survey_reduce_type(line, acc):
        resources, group, _ = acc
        return resources, group, FastMailParser.remove_tabs(line)

    @staticmethod
    def survey_reduce_init_resource(line, acc):
        resources, group, resource_type = acc
        resource_name = re.sub(r'(.*\s([^\\]+).*)', r'\2', line)
        resource = {'name': resource_name, 'group': group, 'type': resource_type, 'stats': {}}
        return [resource] + resources, group, resource_type

    @staticmethod
    def survey_reduce_set_resource_stats(line, acc):
        resources, group, resource_type = acc
        resource, others = resources[0], resources[1:]
        stat, value = re.split(r':\s*', FastMailParser.remove_tabs(line))
        updated_stats = {**resource['stats'], stat: value}
        updated_resource = {**resource, 'stats': updated_stats}
        return [[updated_resource] + others, group, resource_type]

    @staticmethod
    def remove_tabs(str):
        str = str.replace("\t", "")
        str = str.replace("\r", "") # using mmap to read files adds /r to line endings
        return str

