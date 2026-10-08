# 20 — CoT Listener Design Checklist

The facts from 00–19 turned into decisions for a passive CoT listener or monitor. Each item names the file that backs it. The "This project" notes describe `tak-cot-listener` as of the commit this was written against (Oct 2026). Re-check them against the current code.

## Transport

- [ ] **Pick the feed deliberately (18 §3).**
  - TAK Server: use `wss://host:8443/takproto/1` (protobuf from the first frame, no negotiation) or `tls://host:8089` (XML first, optionally negotiated, 17 §3).
  - FreeTAKServer: a raw XML stream.
  - Mesh: UDP multicast `239.2.3.1:6969`.
- [ ] **WebSocket frames carry the stream header.** Each binary message is `0xBF varint TakMessage` (18 §1). Strip the header before `ParseFromString`, or use `takproto.parse_proto()`. Note that it returns `-1` on failure (19).
- [ ] **Never send text frames on `/takproto/1`.** The server closes with 1003 (18 §1).
- [ ] **Keep the receive loop fast.** The server drops messages for a WebSocket that's more than 64 KB or 5 s behind (18 §1).
- [ ] **On raw 8089 `tls`, accept XML and protobuf.** Split XML on `</event>`. If you want protobuf, wait for `t-x-takp-v`, then send `t-x-takp-q` and switch framing only after `t-x-takp-r status=true` (17 §3).
- [ ] **On UDP, accept both XML and `BF 01 BF` datagrams** on the same socket (17 §3, mesh). To hear mesh SA, *join* `239.2.3.1` (02, 00). Just binding port 6969 is not enough.
- [ ] **Federation ports (9000/9001/9102) use a different framing** (4-byte length, `FederatedEvent`). Don't connect a client decoder to them (17 §6).

## Identity and authorisation

- [ ] **Give the listener its own client cert**, not a copy of an operator's WinTAK/ATAK cert (05, 10). Make it read-only on every group it should see: `UserManager.jar certmod -og <group> …` (07).
- [ ] **Reconnect after changing the listener's groups.** The WebSocket subscription's group vector is fixed at connect time unless the client sends something (18 §1).
- [ ] **`/Marti/api/clientEndPoints` only shows clients in groups the cert can read** (18 §2). If "everyone" matters, the read-only membership above is required.
- [ ] **A normal (non-admin) cert is enough** for `/takproto/1`, `/clientEndPoints`, `/subscriptions/all`, `/cot/**`, `/groups/**` and `/version` (18 §2).
- [ ] **Verify the server.** Trust the **intermediate** CA truststore (the client's `caCert.p12`, converted to PEM). The server's CN is usually `takserver`, so either keep the hostname check off and verify the chain, or reissue the server cert with SANs (05, 06, 12).
- [ ] **Show TLS failures as distinct states** (12):
  - "peer not verified" means the wrong CA.
  - A handshake reset that loops means a revoked cert (`RevokedException` on the server).
  - Everyone dropping at once means the intermediate CA and server cert expired.

## Decoding

- [ ] **Merge typed fields with `xmlDetail`.** TAK Server only fills `detail.takv`, `contact`, `group`, `track`, `status` and `precisionLocation` when the XML element had **exactly** the expected attributes. Otherwise the whole element is in `xmlDetail` (17 §5). If an element is in both places, the `xmlDetail` copy wins.
  - *This project:* `cot.py` decides "is a device" from `ev.detail.takv.platform`. A client whose `<takv>` lacks `os` or `device` would then be misclassified on the protobuf path. Parse `xmlDetail` as a fallback for `takv`, `contact` and `__group`.
- [ ] **Times:** protobuf uses ms since epoch, XML uses ISO 8601 with any number of fractional digits (15 §2).
- [ ] **Unknown values:** `hae`/`ce`/`le` ≥ 999999 means unknown, and `0,0` means no fix (15 §3).
- [ ] **Accept a `;suffix` on `type`** and ignore unknown `<detail>` children (15 §7).

## Semantics

- [ ] **UID rules.** The newest event for a UID replaces the older ones (15 §2).
- [ ] **Liveness.**
  - Use `stale` from each client's SA as the main signal.
  - `t-x-c-t` / `t-x-c-t-r` ping/pong traffic only shows that a connection is alive. Drop it (16 §4).
  - For server-side truth use `/clientEndPoints?showCurrentlyConnectedClients=true` or `/subscriptions/all` (18).
- [ ] **Deletes.** Only treat `t-x-d-d` **with a `<link uid>`** as a delete. PyTAK's hello/pong are `t-x-d-d` without a link (16, 19).
- [ ] **Classification** follows 16 §5. A device is an `a-*` atom **with** `<takv>`; everything else on the map is an object.
- [ ] **Control traffic stays out of the UI:** `t-x-takp-*`, `t-x-c-t*`, and optionally `t-x-m-*` (16 §4).

## Recovering state after a restart

- [ ] **The stream only carries changes.** Seed the current picture from the archive with `/Marti/api/cot/sa?start&end` in windows of at most 24 h, or from a client's local store (18 §3).
- [ ] **Archive behaviour.** The archive only holds data if the input has `archive="true"` (the `CoreConfig.xsd` default) and Data Retention hasn't purged it (03, 11, 18 §2). A 404 from `/cot/xml/{uid}` means "not archived, or not visible to your groups". It doesn't mean the server never relayed the object.
  - *This project:* the README concludes "TAK Server keeps no queryable copy of loose markers". Before relying on that, check the 8089 input's `archive` flag and the retention policy, and try `/cot/sa`.

## Operations

- [ ] **Reconnect with exponential backoff and jitter** (PyTAK: 5 s initial, ×2, 120 s max, reset after 300 s healthy; 19).
- [ ] **Health check** with `GET /Marti/api/version` (any user, cheap; 18).
- [ ] **No secrets in code.** Don't hard-code the cert path or password. Change the `atakatak` default (10).
- [ ] **Directed traffic.** Events with `<marti><dest …>` aren't delivered to the listener unless it's a named destination, so the listener never sees directed chat or data meant for others. That's expected (15 §6, 19).
