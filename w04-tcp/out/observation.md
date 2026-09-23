## Task 1

- I chose stop-and-wait because a lost ACK can be retried safely when each packet carries a byte offset and the receiver ACKs the next expected byte; duplicate data is ignored and out-of-order data is buffered.
- Seed 246 used 323 sends for a 250-packet minimum (1.29×) and delivered 291 copies, including 8 duplicates. Loss caused retransmission; both seeds 246 and 999 arrived identical.

## Task 2

- Path B: I used the official Kurose/Ross 9th-edition trace because macOS requires an admin password for live capture. Frames 1–3 are SYN/SYN-ACK/ACK; ISNs are client 4236649187 and server 1068969752; both SYNs offer MSS 1460 and SACK, with window scales 6 (client) and 7 (server). ISNs are chosen per connection rather than starting at zero, which helps avoid stale segments being accepted and makes blind guessing harder.
- In frame 143 the server advertises raw window 1358, scaled to 1358×128 = 173,824 bytes; at frame 145, 75,296 bytes are in flight, so receive-window flow control was not full. The trace shows a browser POST of `alice.txt` from 192.168.86.68 to gaia.cs.umass.edu; it cannot establish the sender's real identity.
- Current Wi-Fi: median 164.60 Mbps (141.09–181.97, 25% spread), 9.3 ms median handshake; phone tethering: 83.94 Mbps (60.50–94.48, 40% spread), 29.7 ms. Handshake and TTFB varied between runs, plausibly with radio/path/CDN load; the higher RTT also slows TCP slow start because its window grows per RTT, though the throughput gap cannot be attributed to RTT alone.

## Task 3

- Slow start to threshold 16, then additive increase of 1/window per ACK and 0.75 multiplicative decrease on loss; window samples had median 25.3 and mean 25.6 packets (about 20 in the pipe plus 5 queued), ending at 27.7.
- Result: 972.8 goodput, 0.5% loss, and 4.9 average queue. The baseline gets 986.8 goodput by dropping 37.4% and keeping 8.8 packets queued, pushing loss and delay onto other flows.
- Compared with a 0.5 loss decrease trial (862.3 goodput, queue 3.2), the gentler 0.75 decrease raised goodput to 972.8 but increased queue to 4.9 and loss from 0.4% to 0.5%.

Trace attribution: J.F. Kurose and K.W. Ross, *Computer Networking: A Top-Down Approach*, 9th ed., official Wireshark trace `tcp-wireshark-trace1-1.pcapng`, https://gaia.cs.umass.edu/kurose_ross/.
