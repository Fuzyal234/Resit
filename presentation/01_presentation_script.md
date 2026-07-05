# 15-Minute Presentation Script — OTP Messenger Security Assessment

**Module:** Cyber Security Engineering (UFCE87-15-3) · **Assessment:** Recorded Video (Resit)
**Speakers:** A = _[Student 1 name]_ · B = _[Student 2 name]_
**Target run time:** 14:30 (hard cut-off 15:00 — nothing past 15:00 is marked)

### How to read this script
- `[A]` / `[B]` — who speaks.
- `[PLAIN ENGLISH]` — say this for the non-technical viewer (the brief requires both audiences). Slow down slightly here.
- `[TECHNICAL]` — the depth that shows the marker you understand it.
- `[DEMO → step N]` — switch to your screen recording and run step *N* from `03_demo_runbook.md`.
- `[Slide N]` — the slide that should be on screen (`02_slide_storyboard.md`).
- Narration is word-for-word, but read it as notes — natural delivery beats reciting. To shorten, cut the parenthetical asides first.

---

## SEGMENT 1 — Introduction + Live Demo · [A] · 1:45 · (0:00–1:45)
`[Slide 1 → 2]`

**[A] [PLAIN ENGLISH]**
"Hi — I'm _[Name A]_ and this is _[Name B]_. This is our security assessment of the
**OTP Messenger**, a browser-based encryption tool built for a client we'll call
Company X. In plain terms: you type a secret message, the app scrambles it using a
random 'one-time pad' key so that only someone holding that exact key can unscramble
it. Our job wasn't to build it — it was to **assess** it: find everything wrong with
it, fix what we could, justify what we couldn't, and prove the app still works."

**[A]** `[DEMO → step F1]`
"Here's the finished, hardened version running. I'll encrypt a message — *'MEETING AT
0900'* — and the app returns the ciphertext and a one-time key. I copy the key, paste
it into decrypt, and we get the original message back. Two things to notice: it's over
**HTTPS**, and the key is shown once and **never stored**."

**[A]**
"To show how we got here, we kept **two copies** side by side: the **original baseline**
as delivered, and our **hardened** version. Everything today compares the two. I'll
cover the vulnerabilities and the fixes; _[Name B]_ covers the compliance standards, the
testing, and the final verdict."

> ⏱ Checkpoint: you should be at **~1:45** leaving this segment.

---

## SEGMENT 2 — Identified Vulnerabilities · [A] · 3:00 · (1:45–4:45)
`[Slide 4 → 5 → 6 → 7]`

**[A] [PLAIN ENGLISH]**
"First: how did we look, and what did we find? We didn't rely on one tool — real
assessment is layered."

**[A] [TECHNICAL] — methodology & tools** `[Slide 5]`
"Three layers. One, **manual static code review** of the Python, the Dockerfiles, the
Nginx config and the Compose files. Two, **automated tooling** — Trivy for container
image CVEs, Nmap for service enumeration, and a **fuzzing** pass with oversized and
malformed input. Three, **dynamic testing** against the running app. We also reviewed
specifically for **malicious code** — backdoors, hardcoded credentials phoning home,
suspicious network calls — and found **none**; what we found are vulnerabilities and
misconfigurations, not planted malware."

**[A]** `[Slide 6]`
"Across the baseline: **17 findings — 5 critical (CAT I), 9 high (CAT II), 3 low (CAT
III)**. Let me show the three that best explain the risk."

**[A]** `[DEMO → step O1]` `[Slide 7]`
"**One — debug mode.** The baseline runs Flask's development server with debugging on.
Look at the container log: *'Debugger is active'*. That interactive debugger lets an
attacker run arbitrary Python on the server — effectively **remote code execution**.
That's a ten-out-of-ten finding."

**[A]** `[DEMO → step O2]`
"**Two — no encryption in transit.** The baseline is HTTP-only. Watch: I send a message
and the response hands back the secret key **in cleartext**, straight from the Flask
port with no Nginx in front of it."
**[PLAIN ENGLISH]** "HTTP is a postcard — anyone on the network path can read it. For a
tool whose whole job is to protect a secret key, mailing that key on a postcard defeats
the entire point."

**[A]** `[DEMO → step O3, log]`
"And it gets worse — the app writes the **plaintext message into its own logs**. There's
our secret sitting in the log file. That's like writing the safe combination in the
visitor book."

**[A]** `[Slide 7 — code snippet]`
"**Three — a bug in the crypto itself**, which no scanner caught; we found it by reading
the code. The original XORs the message against the key using Python's `zip`, which stops
at the **shorter** of the two. If the key is ever shorter than the message, the extra
bytes come out **unencrypted** — silently. That's a logic flaw, not a config toggle."

**[A] — impact & decision**
"The rest of the seventeen follow the same theme: a **hardcoded secret key** committed to
the repo, raw exception messages leaked to users, **no CSRF protection**, no input limits,
no rate limiting, no security headers, root containers, and images with over a thousand
known CVEs. **Impact-wise** this baseline is a full compromise waiting to happen — so our
**decision was to mitigate every CAT I and CAT II finding**; none were accepted, because
all are directly exploitable and fixable in code. The only accepted risks are three
low-severity ones — _[Name B]_ takes those next."

> ⏱ Checkpoint: **~4:45**.

---

## SEGMENT 3 — Required Compliance Standards · [B] · 3:15 · (4:45–8:00)
`[Slide 8 → 9 → 10 → 11]`

**[B] [PLAIN ENGLISH]**
"Thanks _[Name A]_. Finding bugs is only half the job. The other half is measuring the
app against recognised **security standards** — because Company X has to *prove* to an
auditor it meets a baseline, not just say 'trust us.'"

**[B] [TECHNICAL] — which standards and why** `[Slide 9]`
"We chose standards by matching them to what the app actually is. It's a **web
application** → the **Application Security and Development STIG**, the ASD STIG, V5R3. It
**terminates TLS** → **NIST Special Publication 800-52 Revision 2** for transport. It runs
in **containers behind Nginx** → the **Container Platform SRG** and the **Web Server SRG**.
We located these by searching the **DoD STIG library** on the app's functionality —
keywords like 'application', 'web server', 'container', 'TLS'."

**[B] — initial checks & shortcomings** `[Slide 10]`
"Then we checked each relevant control against the baseline. The shortcomings were severe.
Against the **ASD STIG**: debug mode breaks **APSC-DV-002530**; the hardcoded key breaks
**APSC-DV-003280**; no HTTPS breaks **APSC-DV-002000**; plaintext in the logs breaks
**APSC-DV-003200**. Against **NIST 800-52** there was literally **no TLS to assess**.
Against the **Container Platform SRG**: running as root breaks **V-205072**, no dropped
capabilities breaks **V-205070**, and the end-of-life images break **V-205076**. The
verdict on the baseline: **not authorised to deploy** against any of them."

**[B] — accepted shortcomings + rationale** `[Slide 11]`
"After hardening, **three** findings remain — all **CAT III (low)** — and we **accepted**
them, each with a justification and a remediation timeline. **One:** the TLS certificate is
**self-signed**, because we have no DoD PKI in a dev environment — but it still meets NIST's
requirements: RSA-4096 key, SHA-256 signature. **Two: FIPS 140-2** — our key generation uses
the operating system's random generator, which is FIPS-validated *only* when the host runs in
FIPS mode; that's a **deployment dependency, not a code defect**. **Three:** OTP **key
distribution** — the app computes the pad, but physically getting the key to the recipient is
an out-of-band **procedural control**, documented in policy. Every accepted risk is
environmental, and every one has a fix path before production."

> ⏱ Checkpoint: **~8:00**.

---

## SEGMENT 4 — Changes Made · [A] · 2:30 · (8:00–10:30)
`[Slide 12 → 13]`

**[A] [PLAIN ENGLISH]**
"So what did we actually change? One rule throughout: **fix the security problem without
breaking what the app is meant to do.**"

**[A] [TECHNICAL] — application layer** `[Slide 13]`
"At the **application layer**: we replaced the dev server with **Gunicorn** and forced debug
**off**; swapped the hardcoded key for **`secrets.token_hex(32)`** from the OS random source;
added **Flask-WTF CSRF** tokens on every form; added **length validation** plus a 32-kilobyte
body limit; rewrote logging to record **metadata only** — timestamp, source IP, method, path,
outcome — never the message or key; and replaced verbose errors with generic pages. We also
fixed that truncating-XOR bug with an explicit **length-equality check**."

**[A] — transport layer**
"At the **transport layer**: Nginx now terminates **TLS 1.2 and 1.3** with **NIST-approved
cipher suites only**, redirects all HTTP to HTTPS, and adds **HSTS** plus a full security-header
suite — Content-Security-Policy, X-Frame-Options, and the rest."

**[A] — container layer**
"At the **container layer**: multi-stage builds on **current** base images, a **non-root** user,
**all Linux capabilities dropped**, a **read-only** filesystem, resource limits, health checks,
and the Flask port is **no longer exposed to the host** — the only way in is through Nginx."

**[A] — enhancements (beyond fixing findings)**
"And beyond fixing findings, we **enhanced** the app: a live character counter, copy-to-clipboard,
explicit key-handling warnings, and a **health endpoint** for orchestration — usability and
operability on top of the security work."

> ⏱ Checkpoint: **~10:30**.

---

## SEGMENT 5 — Testing & Verification · [B] · 2:45 · (10:30–13:15)
`[Slide 14 → 15 → 16]`

**[B] [PLAIN ENGLISH]**
"A fix you haven't tested is just a hope. So for **every** change we did three things: confirm
the app still works, confirm the vulnerability is actually gone, and confirm we didn't break
anything new. And this was a **loop**, not a one-shot."

**[B] — functionality** `[DEMO → step F1 (round-trip)]` `[Slide 15]`
"**Functionality first.** On the hardened app I encrypt, then decrypt with the key, and get the
exact message back — so the hardening didn't break the core feature."

**[B] — vulnerability re-tests** `[DEMO → steps F2–F6]`
"Then I re-tested each finding. **Debug mode** — gone; it's Gunicorn now, no debugger.
**TLS** — 1.2 and 1.3 succeed, **TLS 1.1 is rejected**, and plain HTTP gets a 301 redirect to
HTTPS. **Flask exposure** — connecting to port 5000 directly is now **refused**. **CSRF** — a
scripted POST without a token is **blocked with a 400**. **Oversized input** — a 100-kilobyte
body is **rejected with a 413** before it ever reaches the app. Each maps to a finding that's
now **closed**."

**[B] — the iterative loop (the key example)** `[Slide 16]` `[DEMO → step F7 or show report §3]`
"Here's where the loop really mattered. Our **first** Trivy scan of the *hardened* images was
**not clean** — it flagged **Gunicorn 21.2.0** for HTTP request smuggling, **CVE-2024-1135**,
plus about twenty CVEs in the Nginx image's system libraries. So we made another change —
upgraded Gunicorn to **22.0.0** and added an `apk upgrade` to the Nginx build — then **rebuilt
and re-scanned**. The Gunicorn CVE disappeared and the Nginx image dropped to **zero**. That
**change → re-test → re-scan** cycle is the whole process, and we ran it until the numbers
stopped moving."

**[B] — validation**
"The final image scan came in at **14** high-and-critical findings, down from **1,403** — and
every one of those 14 is a **base-OS package with no fix available** and no route from the web
app. We validated that, logged them as **residual risk**, and accepted them."

> ⏱ Checkpoint: **~13:15**.

---

## SEGMENT 6 — Comparison, Accepted Risks & Conclusion · [B] · 1:15 · (13:15–14:30)
`[Slide 17 → 18]`

**[B] [PLAIN ENGLISH + numbers]** `[Slide 17]`
"Pulling it together. **Critical findings: 5 → 0. High: 9 → 0. Image vulnerabilities:
1,403 → 14 — a 99% cut. STIG status: not authorised → conditionally authorised.** And the app
still does exactly what it did on day one — encrypt and decrypt — just **safely**."

**[B] — honest close** `[Slide 18]`
"We accepted three low-severity risks, all environmental — self-signed cert, FIPS host, and
key-distribution policy — each with a documented fix before production. We won't claim it's
'perfectly secure' — nothing is — but it now **meets its baseline**, the **residual risks are
understood and justified**, and the **functionality is intact**."

**[B]**
"That's our assessment of the OTP Messenger. Thank you — we're happy to take any questions."

> ⏱ Final: **~14:30** — 30 seconds under the cut-off. If you're running long, trim the
> parenthetical asides in Segments 2 and 4 first.

---

### If you'd rather use bullet notes
Every paragraph above compresses to one on-screen bullet. Keep the `[PLAIN ENGLISH]` line as a
spoken sentence (that's the two-audience mark) and let the `[TECHNICAL]` detail live in the
demo and on the slides.
