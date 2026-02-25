from __future__ import annotations

import datetime
from colorama import Fore, Style, init

init(autoreset=True)

_COLOURS = {
    "INFO":    Fore.CYAN,
    "SUCCESS": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR":   Fore.RED,
    "SNIPE":   Fore.MAGENTA,
    "CACHE":   Fore.BLUE,
    "DEBUG":   Fore.WHITE,
}


def log(level: str, message: str) -> None:
    now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]  
    colour = _COLOURS.get(level.upper(), Fore.WHITE)
    tag = f"{colour}[{level.upper():<7}]{Style.RESET_ALL}"
    print(f"{Fore.WHITE}[{now}]{Style.RESET_ALL} {tag} {message}")


def banner() -> None:
    print(
        f"\n{Fore.MAGENTA}"
        "  ██╗   ██╗ █████╗ ███╗   ██╗██╗████████╗██╗   ██╗\n"
        "  ██║   ██║██╔══██╗████╗  ██║██║╚══██╔══╝╚██╗ ██╔╝\n"
        "  ██║   ██║███████║██╔██╗ ██║██║   ██║    ╚████╔╝ \n"
        "  ╚██╗ ██╔╝██╔══██║██║╚██╗██║██║   ██║     ╚██╔╝  \n"
        "   ╚████╔╝ ██║  ██║██║ ╚████║██║   ██║      ██║   \n"
        "    ╚═══╝  ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝   ╚═╝      ╚═╝   \n"
        f"       {Fore.CYAN}SNIPER  ·  discord.py-self ·  by intruder{Style.RESET_ALL}\n"
    )
