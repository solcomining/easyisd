# Easy ISD Reporter
The easiest way to update Galaxy Harvester using info from Interplanetary Survey Droid emails.

### Features
- Simple numbered-list menu
- Safety conscious design to avoid submitting incorrect or out-of-date info
- Fast folder scanning to auto-find all SWG installations
- Formatted tables showing new and expired spawns
- Highlighting of stats that are at least 95% of the max possible value

### Prerequisites
1) Python from https://www.python.org/downloads/
2) The Galaxy Harvester `galaxy_id` value. In https://galaxyharvester.net/resource.py/321/resourcename the `galaxy_id` value is 321

### Installation
1) Download the latest release from https://github.com/solcomining/easyisd/releases
2) Extract the contents of the zip file into a new folder

### Usage
1) Send a batch of survey droids ingame, wait for the email replies, then use `/mailsave`
2) Run Easy ISD from a command prompt using `python easyisd.py galaxy_id`
3) Make choices from simple numbered lists

### Options
A list of options is shown when the user runs `python easyisd.py -h`

Option  | Description
------------- | -------------
-m  | Path to saved mail folder
-u  | Galaxy Harvester username
-p  | Galaxy Harvester password
-n  | Submit only new spawns
-e  | Submit only expired spawns
-b  | Submit both new and expired spawns

>**Minimum required** 

`python easyisd.py 321` 


>**Specifying login details** 

`python easyisd.py 321 -u myuser -p mypass` 



>**Specifying mail folder and login details** 

`python easyisd.py 321 -m c:\whatever -u myuser -p mypass`



>**Non-interactive mode** 

`python easyisd.py 321 -m c:\whatever -u myuser -p mypass -b`

#
If the SWG installation cannot be found or the search takes too long, you might need to edit `TARGET_FILE` or `EXCLUDED_DRIVES` or `EXCLUDED_FOLDERS ` or `MAX_FOLDER_DEPTH`

name  | value
------------- | -------------
TARGET_FILE | SWGEmu.exe
EXCLUDED_DRIVES | X,Y,Z
EXCLUDED_FOLDERS | C:\\ProgramData, C:\\Users, C:\\Windows, C:\\$Recycle.Bin
MAX_FOLDER_DEPTH | 3

#
If a warning message is shown about not being able to find resource mapping or resource gate data, you might need to edit `restypes.txt` or `resgates.txt` due to differences between game servers.

#
### Example usage
<img width="737" height="862" alt="easyisd4" src="https://github.com/user-attachments/assets/5d6cbfb8-dc8e-4575-a837-923da60ac39a" />

### Help message
<img width="742" height="442" alt="easyisd5" src="https://github.com/user-attachments/assets/2950534d-d7d7-45bb-99a5-6f9fc8c6d763" />
# 












