# Avoids using slow NTFS method calls, further improvements are not cross-platform
# Time taken greatly depends on MAX_FOLDER_DEPTH

import os
import sys
import string
from concurrent.futures import ThreadPoolExecutor, as_completed

EXCLUDED_DRIVES = "X,Y,Z"
EXCLUDED_FOLDERS = {
    "windows": [
        "C:\\ProgramData", "C:\\Users", "C:\\Windows",
        "C:\\$Recycle.Bin", "C:\\AMD", "C:\\Intel", "C:\\NVIDIA",
    ],
    "linux": [
        "/proc", "/sys", "/dev", "/run", "/var/log", "/var/cache",
    ],
}
MAX_FOLDER_DEPTH = {
    "windows": 3,
    "linux": 4,
}
IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")

class FastFolderScan:
    def __init__(self, target_file="SWGEmu.exe", cache_file="locations.txt"):
        self.target_file = target_file
        self.cache_file = cache_file

        # defaults per OS
        os_key = "windows" if IS_WINDOWS else "linux"
        self.excluded_drives  = EXCLUDED_DRIVES or []
        self.excluded_folders = EXCLUDED_FOLDERS[os_key]
        self.max_folder_depth = MAX_FOLDER_DEPTH[os_key]

        # build exclusions trie
        self.excluded_trie = PrefixTrie()
        for folder in self.excluded_folders:
            self.excluded_trie.insert(os.path.abspath(folder))

    def find_roots(self):
        if IS_WINDOWS:
            excluded_drive_letters = {d.upper() for d in self.excluded_drives}
            return [
                f"{letter}:\\"
                for letter in string.ascii_uppercase
                if os.path.exists(f"{letter}:\\") and letter not in excluded_drive_letters
            ]
        else:
            return ["/"]

    def fast_scan(self, start_path, max_depth):
        stack = [(start_path, 0)]
        found_paths = []

        while stack:
            current_path, depth = stack.pop()

            if depth > max_depth:
                continue

            cur_abs = os.path.abspath(current_path)

            # trie based exclusion, cross-platform
            if self.excluded_trie.is_excluded(cur_abs):
                continue

            try:
                for entry in os.scandir(current_path):
                    name = entry.name

                    if entry.is_dir(follow_symlinks=False):
                        stack.append((entry.path, depth + 1))
                    else:
                        if name == self.target_file:
                            found_paths.append(current_path)

            except (PermissionError, FileNotFoundError, OSError):
                continue

        return found_paths

    def threaded_scan(self):
        roots = self.find_roots()
        results = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(self.fast_scan, root, self.max_folder_depth)
                for root in roots
            ]
            for future in as_completed(futures):
                results.extend(future.result())

        return results

    def find_swg_paths(self):
        paths = self.load_from_cache()
        if paths:
            print(f"Loaded SWG locations from {self.cache_file}")
            return paths

        print("Searching for all SWG installs...")
        paths = self.threaded_scan()

        if not paths:
            print(f"Could not find {self.target_file}\nTry increasing the value of MAX_FOLDER_DEPTH in fast_folder_scan.py")
            raise SystemExit("\nGoodbye")

        paths.sort()
        self.save_to_cache(paths)
        print(f"Saved results to {self.cache_file}")
        return paths

    def save_to_cache(self, paths):
        try:
            with open(self.cache_file, "w") as f:
                for path in paths:
                    f.write(path + "\n")
        except Exception as e:
            print(f"Error: {e}")

    def load_from_cache(self):
        try:
            with open(self.cache_file, "r") as f:
                return [line.strip() for line in f if os.path.exists(line.strip())]
        except FileNotFoundError:
            return []

# a trie where node position is used for faster exclusions
class PrefixTrie:
    def __init__(self):
        self.root = {}

    def split_path(self, path):
        # normalize separators
        return path.replace("\\", "/").lower().split("/")

    def insert(self, path):
        parts = self.split_path(path)
        node = self.root
        for part in parts:
            node = node.setdefault(part, {})
        node["#"] = True

    def is_excluded(self, path):
        parts = self.split_path(path)
        node = self.root

        for part in parts:
            if part in node:
                node = node[part]
                if "#" in node:
                    return True
            else:
                return False

        return "#" in node
