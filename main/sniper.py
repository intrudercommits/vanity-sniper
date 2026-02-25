import time
import primp
import random
import os
import threading
import itertools
import asyncio

from utils.logger import banner
from utils.logger import log
from utils.webhook import send_webhook
from utils.config import load_config, Config


def load_proxies():
    if not os.path.exists("data/proxies.txt"):
        with open("data/proxies.txt", "w") as f:
            f.write("")
        return []
    with open("data/proxies.txt", "r") as f:
        return [p.strip() for p in f.read().splitlines() if p.strip()]

cfg: Config = load_config()
proxies = load_proxies()

TOKEN = cfg.token
PASSWORD = cfg.password

class Sniper:
    def __init__(
            self, 
            vanity_map
        ):
        self.vanity_map = vanity_map

        if not proxies:
            log("WARNING", "No proxies found in data/proxies.txt! You will likely be rate-limited very quickly.")
            self.proxies = [None]
        else:
            self.proxies = [f"http://{p}" if not p.startswith("http") else p for p in proxies]
            log("INFO", f"Loaded {len(self.proxies)} proxies from data/proxies.txt")

        self.raw_client = primp.Client(impersonate="chrome")
        self.client = primp.Client(impersonate="chrome", proxy=self.get_random_proxy())

        self.raw_client.get("https://ptb.discord.com/")

        while True:
            try:
                self.client.get("https://ptb.discord.com/")
                break
            except Exception:
                log("WARNING", "Proxy failed during warmup, rotating...")
                self.client = primp.Client(impersonate="chrome_130", proxy=self.get_random_proxy())

        self.mfa_lock = threading.Lock()
        self.mfa_ticket = None
        self.mfa_expiry = 0

        self._refresh_mfa()
        threading.Thread(target=self._mfa_keeper, daemon=True).start()

    def get_random_proxy(self):
        return random.choice(self.proxies)

    def _refresh_mfa(self):
        st = time.time()
        token_ = self.mfa()
        end = time.time()

        if not token_:
            log("ERROR", "MFA Rejected or Failed. Make sure your token and password are correct.")
            os._exit(0)

        with self.mfa_lock:
            self.mfa_ticket = token_
            self.mfa_expiry = time.time() + 299

        try:
            display_ticket = self.mfa_ticket.split('.')[2][:20]
        except:
            display_ticket = self.mfa_ticket[:20]

        log("INFO", f"Received MFA={display_ticket}... ({round(end - st, 2)}s)")

    def _mfa_keeper(self):
        while True:
            with self.mfa_lock:
                wait = max(1, self.mfa_expiry - time.time() - 1)
            time.sleep(wait)
            self._refresh_mfa()

    def mfa(self):
        vanity, guild_id = next(iter(self.vanity_map.items()))

        headers = {
            "Authorization": TOKEN,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.1137 Chrome/130.0.6723.191 Electron/33.4.0 Safari/537.36",
            "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJwdGIiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC4xMTM3Iiwib3NfdmVyc2lvbiI6IjEwLjAuMjYxMDAiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJ4NjQiLCJzeXN0ZW1fbG9jYWxlIjoiZW4tVVMiLCJoYXNfY2xpZW50X21vZHMiOmZhbHNlLCJicm93c2VyX3VzZXJfYWdlbnQiOiJNb3ppbGxhLzUuMCAoV2luZG93cyBOVCAxMC4wOyBXaW42NDsgeDY0KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBkaXNjb3JkLzEuMC4xMTM3IENocm9tZS8xMzAuMC42NzIzLjE5MSBFbGVjdHJvbi8zMy40LjAgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjMzLjQuMCIsIm9zX3Nka192ZXJzaW9uIjoiMjYxMDAiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjozODUxMTUsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjYwOTI2LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ=="
        }

        resp = self.raw_client.patch(
            f"https://ptb.discord.com/api/v9/guilds/{guild_id}/vanity-url",
            headers=headers,
            json={"code": vanity}
        )

        log("DEBUG", f"Initial MFA trigger response: {resp.status_code} - {resp.text}")

        if "mfa" not in resp.text:
            log("ERROR", f"Unexpected MFA response: {resp.status_code} - {resp.text}")
            return False

        try:
            ticket = resp.json()["mfa"]["ticket"]
        except Exception as e:
            log("ERROR", f"Failed to parse MFA ticket: {e} - {resp.text}")
            return False

        payload = {
            "ticket": ticket,
            "mfa_type": "password",
            "data": PASSWORD
        }

        mfa_resp = self.raw_client.post(
            "https://ptb.discord.com/api/v9/mfa/finish",
            json=payload,
            headers=headers
        )

        log("DEBUG", f"MFA finish response: {mfa_resp.status_code} - {mfa_resp.text}")

        if mfa_resp.status_code != 200:
            log("ERROR", f"MFA completion failed: {mfa_resp.status_code} - {mfa_resp.text}")
            return False

        try:
            mfa_token = mfa_resp.json().get("token")
            if not mfa_token:
                log("ERROR", f"No MFA token in response: {mfa_resp.text}")
                return False
            return mfa_token
        except Exception as e:
            log("ERROR", f"Failed to parse MFA token: {e} - {mfa_resp.text}")
            return False

    def check_vanity(self, vanity):
        return self.client.get(
            "https://discord.com/api/v9/invites/" + vanity,
            params={
                "inputValue": vanity,
                "with_counts": "true",
                "with_expiration": "true",
                "with_permissions": "true",
            },
        )

    def snipe(self, vanity, guild_id):
        headers = {
            "Authorization": TOKEN,
            "x-discord-mfa-authorization": self.mfa_ticket,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.1137 Chrome/130.0.6723.191 Electron/33.4.0 Safari/537.36",
            "X-Super-Properties": "eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJwdGIiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC4xMTM3Iiwib3NfdmVyc2lvbiI6IjEwLjAuMjYxMDAiLCJvc19hcmNoIjoieDY0IiwiYXBwX2FyY2giOiJ4NjQiLCJzeXN0ZW1fbG9jYWxlIjoiZW4tVVMiLCJoYXNfY2xpZW50X21vZHMiOmZhbHNlLCJicm93c2VyX3VzZXJfYWdlbnQiOiJNb3ppbGxhLzUuMCAoV2luZG93cyBOVCAxMC4wOyBXaW42NDsgeDY0KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBkaXNjb3JkLzEuMC4xMTM3IENocm9tZS8xMzAuMC42NzIzLjE5MSBFbGVjdHJvbi8zMy40LjAgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjMzLjQuMCIsIm9zX3Nka192ZXJzaW9uIjoiMjYxMDAiLCJjbGllbnRfYnVpbGRfbnVtYmVyIjozODUxMTUsIm5hdGl2ZV9idWlsZF9udW1iZXIiOjYwOTI2LCJjbGllbnRfZXZlbnRfc291cmNlIjpudWxsfQ=="
        }

        st = time.time()
        resp = self.raw_client.patch(
            f"https://ptb.discord.com/api/v9/guilds/{guild_id}/vanity-url",
            headers=headers,
            json={"code": vanity}
        )
        end = time.time()

        if resp.status_code == 200:
            latency = (end - st) * 1000
            log("SNIPE", f"SNIPED > {vanity}... ({latency:.2f}ms)")
            webhook_url = cfg.get("webhook_url")
            if webhook_url:
                try:
                    asyncio.run(send_webhook(webhook_url, vanity, guild_id, latency))
                except Exception as e:
                    log("ERROR", f"Failed to send webhook: {e}")
        else:
            log("ERROR", f"Failed to snipe /{vanity}: {resp.status_code} - {resp.text}")

    def lookup(self):
        stop = threading.Event()

        def worker(vanity, guild_id):
            while not stop.is_set():
                st = time.time()
                try:
                    response = self.check_vanity(vanity)

                    if "You are being rate limited" not in response.text:
                        if "Unknown Invite" in response.text or response.status_code == 404:
                            end = time.time()
                            log("DEBUG", f"Sniping vanity=/{vanity} ({round(end - st, 2)}s)")
                            self.snipe(vanity, guild_id)
                            stop.set()
                            return

                    if response.status_code == 429:
                        self.client.proxy = self.get_random_proxy()

                except Exception as e:
                    self.client.proxy = self.get_random_proxy()

        threads = []
        log("INFO", f"Starting lookup threads for {list(self.vanity_map.keys())}...")
        for vanity, guild_id in self.vanity_map.items():
            t = threading.Thread(target=worker, args=(vanity, guild_id), daemon=True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

    def search(self, ltr_amt, guild_id, workers=10):
        stop = threading.Event()
        gen = itertools.product("abcdefghijklmnopqrstuvwxyz", repeat=ltr_amt)
        gen_lock = threading.Lock()
        winner = threading.Event()

        def next_vanity():
            with gen_lock:
                try:
                    return "".join(next(gen))
                except StopIteration:
                    stop.set()
                    return None

        def worker():
            client = primp.Client(impersonate="chrome_130", proxy=self.get_random_proxy())
            client.get("https://ptb.discord.com/")

            while not stop.is_set():
                vanity = next_vanity()
                if vanity is None:
                    return

                try:
                    response = client.get(
                        "https://discord.com/api/v9/invites/" + vanity,
                        params={
                            "inputValue": vanity,
                            "with_counts": "true",
                            "with_expiration": "true",
                            "with_permissions": "true",
                        },
                    )

                    if "You are being rate limited" not in response.text:
                        if "Unknown Invite" in response.text or response.status_code == 404:
                            if winner.is_set():
                                return
                            winner.set()
                            stop.set()
                            log("DEBUG", f"Sniping vanity=/{vanity}")
                            self.snipe(vanity, guild_id)
                            return

                    if response.status_code == 429:
                        client.proxy = self.get_random_proxy()

                except Exception as e:
                    client.proxy = self.get_random_proxy()

        threads = []
        log("INFO", f"Starting {workers} search workers for {ltr_amt}-letter vanities...")
        for _ in range(workers):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()


if __name__ == "__main__":
    banner()
    
    mode = cfg.mode

    if mode == "lookup":
        target_map = cfg["vanities"]
        sniper = Sniper(target_map)
        sniper.lookup()
    else:
        ltr_amount = cfg.get("search_length", 3)
        guild_id = cfg["server_id"]
        target_map = cfg["vanities"]
        sniper = Sniper(target_map)
        sniper.search(ltr_amount, guild_id)