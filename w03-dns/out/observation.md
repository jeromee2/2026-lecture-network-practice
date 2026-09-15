## Task 1
The root server did not return the final address because it is responsible for delegating the query to the appropriate TLD server, not for storing every host record.
When a delegation lacked glue, the resolver started another walk from a root server to find each nameserver's A record; resolving `www.stanford.edu` required 21 such extra lookups and 27 server queries in total.
This is much more work than the single query a laptop normally sends to its recursive resolver, because that resolver performs and caches the intermediate steps on the laptop's behalf.

## Task 2
The delegation response in packet 2 has no answer but points to the next nameservers in its authority section, while packet 6 contains the final A answer `163.152.6.10`.
My rule labels a site third-party when the final two labels change; it wrongly labels `www.wikipedia.org` because `wikimedia.org` is still Wikimedia-operated infrastructure.
Across the original Wi-Fi and phone hotspot, 8 of 11 CDN-hosted sites returned different address sets, which supports DNS steering but does not by itself prove that every selected address was geographically nearer.

## Task 3
The baseline needlessly refreshes records whose TTL exceeds 60 seconds and serves expired records whose TTL is below 60 seconds; both problems come from discarding the real TTL and using one fixed lifetime.
The floor is 275 upstream queries: each name must be fetched on its first request and again after each TTL expiry, while every still-valid answer is already reused by `YourCache`, so no correct cache can make fewer calls on this workload.
The baseline handles `www.microsoft.com` worst, producing 189 stale answers because its 20-second TTL is much shorter than the fixed 60-second lifetime and it is queried most often.
