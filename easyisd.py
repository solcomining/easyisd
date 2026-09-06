# Easy ISD Reporter v1.0
# Solco Mining Corporation Aug 2026

import argparse
import os
import sys

from console_helpers  import ConsoleHelpers
from fast_folder_scan import FastFolderScan
from fast_mail_parser import FastMailParser
from galaxy_harvester import GalaxyHarvester

CH  = ConsoleHelpers()
FFS = FastFolderScan()
FMP = FastMailParser()
GH  = GalaxyHarvester()

# --- Menu ---
def select_swg(paths, cache_file="locations.txt"):
    while True:
        CH.cprint("\nSWG locations")
        print(f"[0] Delete {cache_file} and exit")
        for i, path in enumerate(paths, start=1):
            print(f"[{i}] {path}")

        choice = input("\nChoose a location: ")
        if not choice.isdigit():
            continue

        choice = int(choice)
        if choice == 0:
            try:
                os.remove(cache_file)
                print(f"\nDeleted {os.path.abspath(cache_file)}")
            except Exception as e:
                print(f"Error: {e}")
            goodbye()

        if 1 <= choice <= len(paths):
            return paths[choice - 1]

def select_character(base_path):
    profiles_root = os.path.join(base_path, "profiles")
    character_folders = []

    for root, dirs, files in os.walk(profiles_root):
        for d in dirs:
            if d.startswith("mail_"):
                character_folders.append(os.path.join(root, d))

    if not character_folders:
        print("Error: Could not find any saved mail folders. Did you run /mailsave ingame?")
        goodbye()

    while True:
        CH.cprint("\nSaved mail locations")
        print("[0] Exit")
        for i, folder in enumerate(character_folders, start=1):
            print(f"[{i}] {folder}")

        choice = input("\nChoose a location: ")
        if not choice.isdigit():
            continue

        choice = int(choice)
        if choice == 0:
            goodbye()

        if 1 <= choice <= len(character_folders):
            return character_folders[choice - 1]

def wait_for_it(galaxy_name):
    while True:
        CH.cprint("\nGalaxy Harvester submit (2 of 2)")
        print(f"[0] Exit\n[1] Submit spawns to Galaxy Harvester from {galaxy_name}")
        if input("\nChoose an action: ") == "1":
            break
        goodbye()

def goodbye():
    raise SystemExit("\nGoodbye")

# --- Parse and submit ---
def parse_args():
    argparser = argparse.ArgumentParser(
        usage="easyisd.py galaxy_id [options] or easyisd.py -h for help",
        description="Easy ISD Reporter - Submit new and/or expired spawns to Galaxy Harvester.",
        epilog=(
            "examples:\n"
            "  easyisd.py 321\n"
            "  easyisd.py 321 -u myuser -p mypass\n"
            "  easyisd.py 321 -u myuser -p mypass -m c:\\whatever\n"
            "  easyisd.py 321 -u myuser -p mypass -m c:\\whatever -b\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    argparser.add_argument("galaxy_id", type=int, help="Galaxy Harvester server ID (always required)")
    argparser.add_argument("-u", type=str, metavar="", default=None, help="Galaxy Harvester username")
    argparser.add_argument("-p", type=str, metavar="", default=None, help="Galaxy Harvester password")
    argparser.add_argument("-m", type=str, metavar="", default=None, help="Path to saved mail folder")

    exclusive = argparser.add_mutually_exclusive_group()
    exclusive.add_argument("-n", action="store_true", help="Submit only new spawns")
    exclusive.add_argument("-e", action="store_true", help="Submit only expired spawns")
    exclusive.add_argument("-b", action="store_true", help="Submit both new and expired spawns")

    args = argparser.parse_args()

    # collapse the three booleans into one submit_what
    if args.n:
        submit_what = "new"
    elif args.e:
        submit_what = "expired"
    elif args.b:
        submit_what = "both"
    else:
        submit_what = None  # interactive mode

    return args.galaxy_id, args.m, args.u, args.p, submit_what

def parse_saved_mail(xml_root, mailpath):
    parsed_isdmails = FMP.parse_folder(mailpath)

    if not parsed_isdmails:
        print(f"\nError: No valid mails found in {mailpath}")
        goodbye()

    parsed_xml = GH.parse_xml_resources(xml_root)
    parsed_names, only_in_parsed = GH.filter_spawn_names(xml_root, parsed_isdmails)
    expired_names = GH.filter_expired_names(parsed_isdmails, xml_root, parsed_names)

    new_spawns = sorted(
        [d for d in parsed_isdmails if d['name'].lower() in only_in_parsed],
        key=lambda d: d['resource_type'].lower()
    )
    exp_spawns = [d for d in parsed_xml if d['name'].lower() in expired_names]

    return new_spawns, exp_spawns, expired_names

def galaxy_login(gh_user, gh_pass):
    CH.cprint("\nGalaxy Harvester login")
    
    token = GH.gh_login(gh_user, gh_pass)
    if not token:
        goodbye()
    
    return token

def submit_spawns(expired_names, new_urls, galaxy_id, token, submit_what):
    CH.cprint("\nGalaxy Harvester responses...")
    new_count, oq_average = 0,0

    if submit_what == "both":
        new_count, oq_average = GH.submit_new(new_urls, token)
        print()
        GH.submit_expired(expired_names, token, galaxy_id)
    elif submit_what == "new":
        new_count, oq_average = GH.submit_new(new_urls, token)
    elif submit_what == "expired":
        GH.submit_expired(expired_names, token, galaxy_id)

    return new_count, oq_average

# --- Main ---
def main():
    galaxy_id, mail_folder, gh_user, gh_pass, submit_what = parse_args()

    # enable ANSI color and style in cmd prompt window
    if sys.platform == "win32":
        os.system("")

    CH.cprint("┌───────────────────────┐")
    CH.cprint("│   Easy ISD Reporter   │")
    CH.cprint("└───────────────────────┘")

    # user select game and mail location
    if not mail_folder:
        paths = FFS.find_swg_paths()
        swgpath = select_swg(paths)
        mail_folder = select_character(swgpath)

    # validate mail location if supplied from cmdline
    if not os.path.exists(mail_folder):
        print(f"Error: Mail folder '{mail_folder}' does not exist.")
        goodbye()

    # get gh data export
    CH.cprint("\nGalaxy Harvester data")
    print(f"Getting daily data export for galaxy id {galaxy_id}")
    output_file = f"current{galaxy_id}.xml"
    xml_root, as_of_label, galaxy_name = None, None, None
    try:
        xml_root, as_of_label, galaxy_name = GH.download_xml(galaxy_id, output_file)
        print(f"Found {as_of_label}")
    except:
        goodbye()

    # mail processing
    new_spawns, exp_spawns, exp_names = parse_saved_mail(xml_root, mail_folder)
    new_urls = GH.make_new_urls(new_spawns, galaxy_id)
    unique_new_names = {e["name"] for e in new_spawns}

    # user select galaxy
    if not (submit_what):
        CH.cprint("\nCaution", color="red", style="bold")
        print("[0] Exit")
        print(f"[1] {galaxy_name}")

        if input("\nConfirm the server: ") != "1":
            goodbye()

    # user select submit
    if not (submit_what):
        CH.cprint("\nGalaxy Harvester submit (1 of 2)")
        print(f"[0] Exit")
        print(f"[1] Submit new and expired")
        print(f"[2] Submit only new ({len(unique_new_names)})")
        print(f"[3] Submit only expired ({len(exp_spawns)})")

        choice = input("\nChoose an action: ")
        if choice == "1":
            submit_what = "both"
            CH.print_spawn_table("NEW", new_spawns)
            CH.print_spawn_table("EXPIRED", exp_spawns)
            wait_for_it(galaxy_name)
        elif choice == "2":
            submit_what = "new"
            CH.print_spawn_table("NEW", new_spawns)
            wait_for_it(galaxy_name)
        elif choice == "3":
            submit_what = "expired"
            CH.print_spawn_table("EXPIRED", exp_spawns)
            wait_for_it(galaxy_name)
        else:
            goodbye()

    # do the login and submit
    token = galaxy_login(gh_user, gh_pass)
    new_count, oq_average = submit_spawns(exp_names, new_urls, galaxy_id, token, submit_what)

    # send discord messages
    notify_discord = True
    if notify_discord and new_count > 0:
        CH.cprint("\nDiscord notification")
        GH.send_to_discord_webhooks(new_count, oq_average)

    goodbye()

if __name__ == "__main__":
    main()
