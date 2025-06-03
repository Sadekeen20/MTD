The core plan is to introduce routing randomization with Ryu and Mininet. 


1️⃣ At Start:
✅ Precomputes all simple paths from source (s1) to destination (s5) using NetworkX (paths list).
✅ No flow rules are installed initially except the default “send to controller” rule (switch_features_handler).

2️⃣ For Each New Packet:
✅ Learns MACs (mymacs).
✅ If destination is unknown, it floods (no flow rule installed).
✅ If destination is known, it:
🔹 Picks the shortest path (via NetworkX, get_path)
🔹 Installs flow rules for that specific path (in install_path).
🔹 Flow rules match on in_port, src_mac, and dst_mac to only affect traffic between these two hosts.

3️⃣ Periodic Path Mutation (rrm_thread):
✅ Every 2 minutes, for specific MAC pair (hardcoded as h1 and h2 in the code), it:
🔹 Randomly selects a new path from paths.
🔹 Reinstalls flow rules along that path for this MAC pair.

