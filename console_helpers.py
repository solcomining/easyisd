import json
import re

class ConsoleHelpers:
    def __init__(self):
        # load resource metadata
        self.resource_gates = json.load(open("resgates.txt"))

        # spawn table columns
        self.STAT_KEYS = ["CD", "DR", "FL", "HR", "MA", "PE", "OQ", "SR", "UT"]
        self.NAME_W    = 12
        self.TYPE_W    = 30
        self.STAT_W    = 4
        self.PLANET_W  = 31

    # colour print default yellow bold
    def cprint(self, text, color="yellow", style="bold", end="\n"):
        ANSI_COLORS = {
            "black":"30","red":"31","green":"32","yellow":"33",
            "blue":"34","magenta":"35","cyan":"36","white":"37"
        }

        ANSI_STYLES = {
            "bold":"1","dim":"2","italic":"3","underline":"4",
            "blink":"5","reverse":"7"
        }
        codes = []

        if color in ANSI_COLORS:
            codes.append(ANSI_COLORS[color])

        if style:
            if isinstance(style, (list, tuple)):
                for s in style:
                    if s in ANSI_STYLES:
                        codes.append(ANSI_STYLES[s])
            else:
                for s in str(style).split(","):
                    s = s.strip()
                    if s in ANSI_STYLES:
                        codes.append(ANSI_STYLES[s])

        prefix = f"\033[{';'.join(codes)}m" if codes else ""
        suffix = "\033[0m" if codes else ""

        print(f"{prefix}{text}{suffix}", end=end)

    # ANSI aware alignment
    def visible_length(self, str):
        ANSI_RE = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
        return len(ANSI_RE.sub("", str))

    def pad_ansi(self, str, width, align="left"):
        vis = self.visible_length(str)
        if vis >= width:
            return str

        pad = width - vis

        if align == "right":
            return " " * pad + str
        elif align == "center":
            left = pad // 2
            right = pad - left
            return " " * left + str + " " * right
        else:
            return str + " " * pad

    def short_planet(self, str):
        return str[:3] if len(str) > 3 else str

    def short_rtype(self, str):
        return str[:self.TYPE_W] if len(str) > self.TYPE_W else str

    def format_rtype(self, str):
        return self.pad_ansi(self.short_rtype(str), self.TYPE_W)

    # formatted spawns table with highlighting
    def print_spawn_table(self, table_name, spawns):
        # group spawns by name (multiplanet spawns on one line)
        grouped = {}
        for spawn in spawns:
            name = spawn["name"]
            restype = spawn["resource_type"]
            restype_id = spawn["resource_type_id"].strip()
            planet = spawn.get("planet", "All")
            stats = spawn.get("stats", {})

            key = (name, restype)

            if key not in grouped:
                grouped[key] = {
                "planets": set(),
                "stats": stats,
                "restype_id":restype_id,
                }

            grouped[key]["planets"].add(planet)

        # build header
        header = (
            self.pad_ansi(table_name, self.NAME_W) + " " +
            self.pad_ansi("", self.TYPE_W) + " " +
            " ".join(self.pad_ansi(k, self.STAT_W, align="center") for k in self.STAT_KEYS) + " " +
            self.pad_ansi("Planets", self.PLANET_W)
        )
        self.cprint(f"\n{header}", style=["bold", "reverse"])

        # build row
        for (name, restype), data in grouped.items():
            planets = " ".join(self.short_planet(p) for p in sorted(data["planets"]))
            stats = data["stats"]
            restype_id = data["restype_id"]

            gate_ranges = self.resource_gates.get(restype_id, {})
            if not gate_ranges:
                print(f"Warning: {restype_id} not found in resgates.txt")
                continue

            # stat highlighting
            row_stats = []
            for key in self.STAT_KEYS:
                val = stats.get(key, "")
                val = val if val != "" else "- "

                stat_key_lower = key.lower()
                if stat_key_lower in gate_ranges:
                    min_val, max_val = gate_ranges[stat_key_lower]
                    ninefive = max_val - 0.05 * (max_val - min_val)    # 95%
                    ninezero = max_val - 0.10 * (max_val - min_val)    # 90%
                    
                    try:
                        if int(val) > ninefive:
                            val = f"\033[0;33m{val}\033[0m"     # goldyellow
                        if int(val) > ninezero:
                            val = f"\033[0;32m{val}\033[0m"     # green
                    except ValueError:
                        pass

                row_stats.append(self.pad_ansi(val, self.STAT_W, align="right"))

            row = (
                self.pad_ansi(name, self.NAME_W) + " " +
                self.format_rtype(restype) + " " +
                " ".join(row_stats) + " " +
                self.pad_ansi(planets, self.PLANET_W)
            )

            # and print
            print(row)