# Easy ISD Reporter
The easiest way to update Galaxy Harvester using saved Interplanetary Survey Droid emails.

Compatible with all SWGEmu based Star Wars Galaxies servers.

### Features
- Fast folder scanning to quickly find all SWG installations.
- Simple numbered list user interface.
- Safety conscious design to avoid submitting incorrect or out-of-date info.
- Formatted tables with highlighting of stats that are at least 90% of the max possible value.

### Prerequisites
1) Python from https://www.python.org/downloads/
2) The Galaxy Harvester `galaxy_id` value for your server.

      In [https://galaxyharvester.net/resource.py/118/leonaore](https://galaxyharvester.net/resource.py/118/leonaore) the `galaxy_id` value is 118 (Finalizer).
 
### Installation
1) Download the latest zip file release from https://github.com/solcomining/easyisd/releases
2) Extract the contents of the zip file into a new folder, e.g. `C:\Games\Easyisd`

### Usage ingame
1) Send some survey droids, wait for the email replies, then use `/mailsave`. This will save all mails.
2) For ease of use it is recommended to use `/emptymail` after `/mailsave`, and to not send droids from a merchant or main character.

### Usage out-of-game (after /mailsave)
1) Open a command prompt window.
2) Change directory to where you previously extracted the zip file, by using e.g.  `cd C:\Games\Easyisd`
3) Run Easy ISD, by using `python easyisd.py galaxy_id`
4) Make choices from the numbered lists. An option to exit is always available.

### Options
A list of options is shown by using `python easyisd.py -h`

Option  | Description
------------- | -------------
-u  | Galaxy Harvester username
-p  | Galaxy Harvester password
-m  | Path to saved mail folder
-n  | Submit only new spawns
-e  | Submit only expired spawns
-b  | Submit both new and expired spawns

>**Minimum required:** 

`python easyisd.py 321` 


>**Specifying login details:** 

`python easyisd.py 321 -u myuser -p mypass` 



>**Specifying mail folder and login details:** 

`python easyisd.py 321 -m c:\whatever -u myuser -p mypass`



>**Non-interactive mode:** 

`python easyisd.py 321 -m c:\whatever -u myuser -p mypass -b`

#
If the SWG installation cannot be found you might need to edit `EXCLUDED_DRIVES` or `EXCLUDED_FOLDERS ` or `MAX_FOLDER_DEPTH` in `fast_folder_scan.py`

name  | value
------------- | -------------
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












