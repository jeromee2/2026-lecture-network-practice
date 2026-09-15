# DNS steering measurement

## Packet capture

- Transaction ID `23812`: packet 1 is the query to the root server; packet 2 is its matching response.
- Packet 2 is a delegation (`0/6/11`: no answer, six authority records, eleven additional records).
- Packet 6 is the final answer from `163.152.11.6`: `www.korea.ac.kr A 163.152.6.10`.
- The largest DNS response captured was packet 2, at 352 bytes; its root delegation records made it large.

## Third-party rule

Rule verdict: call a site third-party when its final CNAME name has a different final two labels from the original site. This is only a heuristic, not proof of ownership.

| Site | Chain length | Final zone | Third party? | Rule verdict | Address sets observed |
| --- | ---: | --- | --- | --- | --- |
| www.microsoft.com | 2 | akamaiedge.net | yes | yes | 104.94.218.45 / 23.49.206.40 / 23.63.226.92 |
| www.netflix.com | 1 | netflix.com | no | no | 207.45.72.1, 207.45.73.1 |
| www.adobe.com | 2 | akamai.net | yes | yes | 2.22.234.137, 2.22.234.155 / 23.35.218.227, 23.35.218.232 / 23.67.53.155, 23.67.53.169, 23.67.53.185 / 23.76.153.115, 23.76.153.121 |
| www.cnn.com | 1 | fastly.net | yes | yes | 146.75.51.5 / 151.101.131.5, 151.101.195.5, 151.101.3.5, 151.101.67.5 |
| www.apple.com | 3 | akamaiedge.net | yes | yes | 104.94.216.37 / 184.31.228.249 / 23.217.69.53 / 23.49.205.28 / 23.63.77.47 |
| www.korea.ac.kr | 0 | ac.kr | no | no | 163.152.6.10 |
| www.stanford.edu | 1 | netlifyglobalcdn.com | yes | yes | 15.197.167.90, 3.33.186.135 |
| www.bbc.co.uk | 2 | fastly.net | yes | yes | 146.75.48.81 / 151.101.0.81, 151.101.128.81, 151.101.192.81, 151.101.64.81 |
| www.spotify.com | 1 | fastly.net | yes | yes | 146.75.51.42 / 151.101.131.42, 151.101.195.42, 151.101.3.42, 151.101.67.42 |
| www.github.com | 1 | github.com | no | no | 20.200.245.247 / 20.27.177.113 |
| www.wikipedia.org | 1 | wikimedia.org | no | yes | 103.102.166.224 |
| www.nytimes.com | 3 | fastly.net | yes | yes | 146.75.49.164 / 151.101.1.164, 151.101.129.164, 151.101.193.164, 151.101.65.164 |

## Steering result

Networks measured: original-wifi, phone-hotspot.

8 of 11 CDN-hosted sites answered differently to a different resolver or recorded network.

## Rule limitation and correction

The rule gets **www.wikipedia.org** wrong: its target ends in `wikimedia.org`, so the rule says `yes`, but it is Wikimedia-operated infrastructure rather than a third-party CDN. A site with no CNAME is also classified as `no` by this rule, but that does not prove there is no CDN: anycast can hide a CDN behind ordinary A records.
