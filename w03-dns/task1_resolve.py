#!/usr/bin/env python3
"""Week 3 · Task 1 — Build your own iterative resolver.

Textbook §2.4.2 - §2.4.3.

`dig +trace` walks root -> TLD -> authoritative for you. In this task you do
that walk yourself: start at a root server, read the delegation it returns,
ask the next server, and keep going until somebody answers authoritatively.

You may shell out to `dig` for the transport, or use a DNS library
(`dnspython` is in the container). Either is fine - what matters is that
*you* follow the delegations rather than letting a tool do it.

    python3 task1_resolve.py www.korea.ac.kr
    python3 task1_resolve.py --verify        # check yourself against dig

Pass condition
--------------
`--verify` resolves five names with your resolver and with `dig`, and the
addresses must agree. A name behind a CDN may legitimately return a different
address each time; the harness compares the *set of authoritative nameservers*
you ended at for those, not the address.
"""
import argparse, subprocess, sys


ROOT_SERVERS = [
    "198.41.0.4",       
    "199.9.14.201",     
    "192.33.4.12",      
]




VERIFY_NAMES = [
    ("www.korea.ac.kr", "stable"),
    ("dns.google", "stable"),
    ("en.wikipedia.org", "stable"),
    ("www.stanford.edu", "stable"),
    ("www.microsoft.com", "cdn"),
]


class Resolver:
    """Your iterative resolver.

    The whole point is that you never ask a server to recurse for you.
    You ask one server, it says "not mine, ask over there", and you go there.

    Suggested shape - but it is yours to design:

        resolve(name) -> (address, path)
            address : the A record you ended up with, as a string
            path    : the servers you asked, in order, so you can show your work

    Things you will hit, in roughly this order:

    1.  A delegation gives you NS *names*, sometimes with glue A records and
        sometimes without. No glue means you have to resolve that nameserver's
        name first - which is another walk. Decide what you do there.
    2.  A server may not answer. Try the next one rather than giving up.
    3.  CNAMEs. The answer you get back may be a different name than the one
        you asked for, and you have to start again with that name.
    4.  Loops. Cap your depth.

    If you shell out to dig, the flag you want is `+norecurse`, so that the
    server you ask replies with a delegation instead of doing the work:

        dig @198.41.0.4 www.korea.ac.kr +norecurse
    """

    MAX_DEPTH = 24

    def resolve(self, name):
        self.path = []
        self.asked = set()
        address = self._walk(self._absolute(name), ROOT_SERVERS, 0, set())
        return address, self.path

    @staticmethod
    def _absolute(name):
        return name.rstrip(".").lower() + "."

    @staticmethod
    def _unique(values):
        return list(dict.fromkeys(values))

    def _query(self, server, name):
        """Ask exactly one server; +norecurse keeps the walk ours."""
        result = subprocess.run(
            ["dig", f"@{server}", name, "A", "+norecurse", "+time=2", "+tries=1"],
            capture_output=True, text=True, timeout=4,
        )
        if result.returncode:
            return {"answer": [], "authority": [], "additional": []}

        records = {"answer": [], "authority": [], "additional": []}
        section = None
        headings = {
            ";; ANSWER SECTION:": "answer",
            ";; AUTHORITY SECTION:": "authority",
            ";; ADDITIONAL SECTION:": "additional",
        }
        for line in result.stdout.splitlines():
            line = line.strip()
            if line in headings:
                section = headings[line]
                continue
            if not section or not line or line.startswith(";"):
                continue
            fields = line.split()
            if len(fields) >= 5:
                records[section].append(
                    (self._absolute(fields[0]), fields[3].upper(), fields[4]))
        return records

    def _walk(self, name, servers, depth, cname_chain):
        if depth >= self.MAX_DEPTH:
            raise RuntimeError("DNS walk exceeded its depth limit")
        if name in cname_chain:
            raise RuntimeError(f"CNAME loop at {name}")

        current_servers = servers
        while current_servers:
            referral = None
            for server in current_servers:
                question = (server, name)
                if question in self.asked:
                    continue
                self.asked.add(question)
                self.path.append(server)
                try:
                    response = self._query(server, name)
                except (subprocess.SubprocessError, OSError):
                    continue

                addresses = [value for _, kind, value in response["answer"]
                             if kind == "A"]
                if addresses:
                    return addresses[0]

                cnames = [self._absolute(value) for _, kind, value in response["answer"]
                          if kind == "CNAME"]
                if cnames:
                    return self._walk(cnames[-1], ROOT_SERVERS, depth + 1,
                                      cname_chain | {name})

                nameservers = [self._absolute(value)
                               for _, kind, value in response["authority"]
                               if kind == "NS"]
                if nameservers:
                    glue = {}
                    for owner, kind, value in response["additional"]:
                        if kind == "A":
                            glue.setdefault(owner, []).append(value)
                    referral = (nameservers, glue)
                    break

            if not referral:
                break

            nameservers, glue = referral
            next_servers = [ip for ns in nameservers for ip in glue.get(ns, [])]
            for ns in nameservers:
                if ns in glue:
                    continue
                try:
                    next_servers.append(self._walk(ns, ROOT_SERVERS, depth + 1,
                                                   set()))
                except RuntimeError:
                    continue
            current_servers = self._unique(next_servers)
            depth += 1

            if depth >= self.MAX_DEPTH:
                raise RuntimeError("DNS walk exceeded its depth limit")

        raise RuntimeError(f"no usable DNS answer for {name}")



def dig_answer(name):
    """What the system resolver says, for comparison."""
    out = subprocess.run(["dig", "+short", name, "A"],
                         capture_output=True, text=True).stdout
    return [l for l in out.split() if l and l[0].isdigit()]


def verify():
    r, failures = Resolver(), 0
    for name, kind in VERIFY_NAMES:
        try:
            addr, path = r.resolve(name)
        except NotImplementedError:
            print("Nothing implemented yet - write Resolver.resolve first.")
            return 1
        except Exception as e:
            print(f"  FAIL  {name:<22} your resolver raised {e!r}")
            failures += 1
            continue
        expected = dig_answer(name)
        if addr in expected:
            note = ""
        elif kind == "cdn":
            note = "  <- differs, but this name is CDN-hosted. Explain it."
        else:
            note = "  <- should have matched"
            failures += 1
        print(f"  {'FAIL' if note.endswith('matched') else 'ok  '}  {name:<22} "
              f"you={addr:<16} dig={','.join(expected) or '-'}   "
              f"hops={len(path)}{note}")
    print(f"\n  {len(VERIFY_NAMES) - failures}/{len(VERIFY_NAMES)} ok")
    return 1 if failures else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name", nargs="?", default="www.korea.ac.kr")
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()

    if a.verify:
        sys.exit(verify())

    addr, path = Resolver().resolve(a.name)
    for i, server in enumerate(path, 1):
        print(f"  {i}. asked {server}")
    print(f"\n  {a.name} -> {addr}")


if __name__ == "__main__":
    main()
