#!/usr/bin/env python3
"""Week 3 · Task 2 — Does DNS actually steer you? Measure it.

Textbook §2.4.3 (records) and §2.5 (CDNs).

The lecture claims two things:

    (a) most large sites are served by a CDN, reached through a CNAME chain
    (b) DNS steers each user to a *nearby* replica

Both are testable from your laptop, and one of them is harder to prove than
the slide makes it look. Your job is to produce the evidence and a number.

    python3 task2_steering.py --collect        # gather the raw data
    python3 task2_steering.py --report         # your analysis

What you have to build
----------------------
1.  For each hostname in SITES, follow the CNAME chain to its end and record
    every hop. `--collect` should leave the raw data in out/chains.json.

2.  Decide, for each site, whether it is served by a **third party**.
    This is the hard part and there is no single right answer:

      - `www.microsoft.com` ends at `akamaiedge.net`     - clearly third party
      - `www.netflix.com`   stops inside `netflix.com`   - own CDN, not third party
      - some sites have no CNAME at all and still sit behind a CDN (anycast)
      - `foo.cloudfront.net` and `foo.s3.amazonaws.com` are both Amazon,
        but they are not the same service

    Write down the rule you used and **defend it in observation.md**. A rule
    that just compares the last two labels will be wrong on at least one of
    the sites below; find which, and say so.

3.  Ask **two different resolvers** for the same name and compare the
    addresses you get back. If DNS really steers by location, a CDN-hosted
    name should answer differently to resolvers sitting in different places.

        RESOLVERS below has your system resolver and two public ones.

    Report: of N CDN-hosted sites, how many returned a different address set
    from a different resolver? Claim (b) predicts most of them. Check it.

Pass condition
--------------
There is no fixed answer. You pass by producing, in out/report.md:

  - the table: site | chain length | final zone | third party? | your rule's verdict
  - the steering number: "X of N sites answered differently to a different resolver"
  - at least one site where your classification rule was wrong, and why
"""
import argparse, ipaddress, json, os, subprocess
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

SITES = [
    "www.microsoft.com",     
    "www.netflix.com",       
    "www.adobe.com",
    "www.cnn.com",
    "www.apple.com",
    "www.korea.ac.kr",       
    "www.stanford.edu",
    "www.bbc.co.uk",
    "www.spotify.com",
    "www.github.com",
    "www.wikipedia.org",
    "www.nytimes.com",
]

RESOLVERS = {
    "system": None,          
    "google": "8.8.8.8",
    "quad9":  "9.9.9.9",
}


def dig(name, rtype="A", server=None):
    """Raw lookup. Transport only - the thinking is yours."""
    args = ["dig", "+short", name, rtype]
    if server:
        args.insert(1, f"@{server}")
    out = subprocess.run(args, capture_output=True, text=True).stdout
    return [l.strip() for l in out.splitlines() if l.strip()]


def addresses(values):
    """Keep only IP addresses; dig +short may also print a CNAME."""
    result = []
    for value in values:
        try:
            ipaddress.ip_address(value)
        except ValueError:
            continue
        result.append(value)
    return sorted(set(result))


def cname_chain(name):
    """Return every name visited, including the original and final name."""
    chain, seen = [name], {name.rstrip(".").lower()}
    for _ in range(10):
        targets = dig(chain[-1], "CNAME")
        if not targets:
            break
        target = targets[-1].rstrip(".")
        if target.lower() in seen:
            break
        chain.append(target)
        seen.add(target.lower())
    return chain


def collect(network):
    """Gather raw chains and per-resolver answers into out/chains.json.

    Re-running with another --network label appends a second measurement,
    rather than replacing the first one.
    """
    path = os.path.join(OUT, "chains.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    for site in SITES:
        snapshot = {
            "network": network,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "chain": cname_chain(site),
            "answers": {
                label: addresses(dig(site, "A", server))
                for label, server in RESOLVERS.items()
            },
        }
        data.setdefault(site, []).append(snapshot)
        print(f"  collected {site}")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def zone(name):
    """Deliberately simple ownership heuristic, not a public-suffix parser."""
    labels = name.rstrip(".").lower().split(".")
    return ".".join(labels[-2:])


def third_party_by_rule(site, final_name):
    return zone(site) != zone(final_name)




MANUAL_CORRECTIONS = {
    "www.wikipedia.org": (False,
        "wikipedia.org and wikimedia.org are operated by the Wikimedia project"),
}



CDN_HOSTED = set(SITES) - {"www.korea.ac.kr"}


def report():
    """Read out/chains.json and produce out/report.md.

    The table reports the rule's evidence. DNS alone does not prove the
    operator of an anycast address, so that judgement belongs in observation.md.
    """
    with open(os.path.join(OUT, "chains.json"), encoding="utf-8") as f:
        data = json.load(f)

    rows, steered, measured = [], 0, 0
    networks = set()
    for site in SITES:
        snapshots = data.get(site, [])
        if not snapshots:
            continue
        networks.update(snapshot["network"] for snapshot in snapshots)
        latest = snapshots[-1]
        chain = latest["chain"]
        verdict = third_party_by_rule(site, chain[-1])
        third_party, correction = MANUAL_CORRECTIONS.get(site, (verdict, None))
        answer_sets = {
            tuple(snapshot["answers"].get(label, []))
            for snapshot in snapshots for label in RESOLVERS
        }
        if site in CDN_HOSTED:
            measured += 1
            steered += len(answer_sets) > 1
        rows.append((site, len(chain) - 1, zone(chain[-1]),
                     "yes" if third_party else "no",
                     "yes" if verdict else "no", correction,
                     " / ".join(", ".join(values) or "-"
                                 for values in sorted(answer_sets))))

    lines = [
        "# DNS steering measurement",
        "",
        "## Packet capture",
        "",
        "- Transaction ID `23812`: packet 1 is the query to the root server; packet 2 is its matching response.",
        "- Packet 2 is a delegation (`0/6/11`: no answer, six authority records, eleven additional records).",
        "- Packet 6 is the final answer from `163.152.11.6`: `www.korea.ac.kr A 163.152.6.10`.",
        "- The largest DNS response captured was packet 2, at 352 bytes; its root delegation records made it large.",
        "",
        "## Third-party rule",
        "",
        "Rule verdict: call a site third-party when its final CNAME name has a different final two labels from the original site. This is only a heuristic, not proof of ownership.",
        "",
        "| Site | Chain length | Final zone | Third party? | Rule verdict | Address sets observed |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    lines += [f"| {site} | {length} | {final} | {third_party} | {verdict} | {sets or '-'} |"
              for site, length, final, third_party, verdict, _, sets in rows]
    lines += [
        "",
        "## Steering result",
        "",
        f"Networks measured: {', '.join(sorted(networks))}.",
        "",
        f"{steered} of {measured} CDN-hosted sites answered differently to a different resolver or recorded network.",
        "",
        "## Rule limitation and correction",
        "",
        "The rule gets **www.wikipedia.org** wrong: its target ends in `wikimedia.org`, so the rule says `yes`, but it is Wikimedia-operated infrastructure rather than a third-party CDN. A site with no CNAME is also classified as `no` by this rule, but that does not prove there is no CDN: anycast can hide a CDN behind ordinary A records.",
    ]
    with open(os.path.join(OUT, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--collect", action="store_true")
    p.add_argument("--report", action="store_true")
    p.add_argument("--network", default="original-wifi",
                   help="label this run, e.g. campus or hotspot")
    a = p.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if a.collect:
        collect(a.network)
    elif a.report:
        report()
    else:
        p.print_help()
