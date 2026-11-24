# Findings: Digital Payment Trends in India — UPI and Beyond

Every number below is computed from `data/processed/*.csv`, which
`python -m src.preprocessing` builds from the two raw files in `data/raw/`.
Periods are stated with each figure; "Sep 2026" means the RBI's September 2026
release.

---

## The one-line story

UPI now carries **87 of every 100 retail payment transactions in India but only
30 rupees of every 100 of their value**: it has won the transaction, not yet the
treasury. The next phase of growth has to come from bigger baskets, not just
more taps.

---

## Key insights

### 1. UPI dominates transaction count but not money moved

In Sep 2026, UPI processed **24,068 million transactions worth ₹29.37 lakh
crore**, against total retail payments of **27,544 million transactions worth
₹96.91 lakh crore** — a **87.4% share of volume and 30.3% of value**.

The Herfindahl index of retail volume across 11 instruments is **7,661**, far
above the 2,500 level usually read as "highly concentrated". The top three
instruments (UPI, NEFT, wallets) hold **93.2%** of all retail transactions.

### 2. The volume/value gap is a ticket-size gap, and it is enormous

Average ticket size in Sep 2026:

| Instrument | Avg ticket |
|---|---|
| UPI | ₹1,220 |
| Wallets | ₹309 |
| Credit card | ₹3,343 |
| IMPS | ₹19,937 |
| NEFT | ₹54,231 |
| CTS (cheques) | ₹1,45,461 |
| RTGS | ₹72.3 lakh |

NEFT moves **3.1% of retail transactions but 48.2% of retail value**. Cheques
move **0.15% of transactions and 6.4% of value**. UPI is a retail-payment rail;
the money still travels on NEFT and RTGS.

### 3. Growth is adoption, not bigger baskets

Across the ten months in the NPCI series (Jun 2025 → Mar 2026), UPI volume rose
**18,395 → 22,641 million (+23.1%)** and value rose **+22.8%**, an annualised
**+31.9%** in volume. The average ticket size moved from **₹1,307 to ₹1,304** —
flat, with a standard deviation of just **₹23** over the ten months.

Volume and value are **0.967 correlated**, while ticket size is only **0.24
correlated with volume**: the system is adding transactions, not adding value
per transaction.

### 4. UPI is absorbing IMPS, and taking share from cards

Year on year, Sep 2025 → Sep 2026, by volume:

| Instrument | Volume | Value | Ticket |
|---|---|---|---|
| UPI | **+22.6%** | +18.0% | −3.8% |
| Credit card | +23.2% | **−5.9%** | −23.6% |
| Wallets | +7.3% | +32.7% | +23.6% |
| NEFT | +2.6% | +9.6% | +6.8% |
| Debit card | −7.5% | −7.4% | +0.2% |
| CTS | −8.6% | +8.3% | +18.5% |
| **IMPS** | **−10.2%** | +18.3% | +31.7% |
| APBS | −21.7% | −22.9% | −1.6% |
| NACH (Cr) | −27.0% | +24.5% | +70.6% |

IMPS loses 10% of its transactions while its value rises 18% — the small-ticket
IMPS user has moved to UPI and what remains is larger transfers. Credit cards
show the mirror image: **23% more swipes but 6% less value**, so the average
card ticket fell **23.6%**, consistent with small-ticket credit being routed
through UPI-linked credit.

### 5. Acceptance is being built on QR, not on terminals

Sep 2025 → Sep 2026:

| Acceptance point | Change |
|---|---|
| UPI QR codes | **+24.9%** (70.9 → 88.6 crore codes) |
| PPI / wallet stock | +46.1% |
| Credit cards in force | +10.4% |
| Debit cards in force | +1.5% |
| Micro ATMs | **−8.7%** |
| Bharat QR | −12.0% |
| PoS terminals | **−14.0%** (1.21 → 1.04 crore) |

India is adding **17.7 crore UPI QR codes while removing 17 lakh PoS
terminals** — ten times as many QR stickers as terminals lost. The marginal merchant is being onboarded with a sticker, not a
machine — cheaper to deploy, but it also means less card and EMI infrastructure
at the point of sale.

### 6. Fraud value has doubled while the fraud *rate* has improved

Domestic payment frauds, Sep 2022 → Sep 2026:

- Fraud value per month: **₹249 crore → ₹493 crore (+97.8%)**
- One fraud per **58,177 transactions → one per 78,408** (a 35% improvement)
- Fraud-to-sales ratio (FTS): **0.127 → 0.147 basis points**
- 12-month average fraud value: **₹414 crore per month**

Read carefully: the system got safer per transaction, but because the number of
transactions exploded, the absolute money lost still doubled. The rate is small;
the base is not. (FTS is quoted exactly as the RBI publishes it — the published
ratio and the published rupee figures do not reconcile to a single denominator,
so treat FTS as a relative indicator and use ₹ crore for the level.)

### 7. Seasonality cannot be claimed from this data

The monthly series covers only **10 months (Jun 2025 – Mar 2026)**, so each
calendar month appears once. March 2026 is the peak (**22,641 Mn**, index 110
against the series mean) and June 2025 the trough (**18,395 Mn**, index 90), but
with a single observation per month that is a trend, not a seasonal pattern.
Establishing festive-quarter effects needs at least 24–36 months of history.

---

## The data story

**Problem.** India's payment statistics show explosive growth in UPI, but
"more UPI transactions" is quoted as if it means more money moving, more
inclusion, and a healthier payment system. It does not automatically mean any
of those things.

**Analysis.** Putting the NPCI monthly series next to the RBI's
instrument-level release shows where UPI sits: 87.4% of retail volume against
30.3% of retail value, an average ticket of ₹1,220 that has not moved in ten
months, and a peer group where IMPS is shrinking in count while cheques and
NEFT still carry the large-value traffic. Meanwhile the acceptance mix is
tilting to QR (−14% PoS), and fraud value has doubled even as the fraud rate
improved.

**Insight.** UPI has solved *reach* and not yet *depth*. Its growth is
transaction-count growth at a fixed ticket size, which caps how much value it
can capture and keeps the large-value rails — and their fraud exposure —
outside its orbit.

**Recommendation.** Grow the ticket, not just the count (see below), and treat
fraud as a volume problem, not only a rate problem.

---

## Recommendations

1. **For merchants and acquirers: plan for QR-first, not terminal-first.**
   PoS terminals fell 14% in a year while UPI QR codes grew 25%. New merchant
   onboarding, reconciliation and settlement flows should assume a QR sticker
   and a smartphone, with PoS reserved for high-ticket and EMI categories.

2. **For banks and UPI product teams: the next growth lever is ticket size.**
   With the average ticket pinned at ~₹1,300 for ten months, volume growth is
   the only engine running. Push UPI into categories with naturally larger
   baskets — credit lines and EMI at checkout, insurance and utility bill
   payments, tuition and rent, B2B collections — where the ₹1,220 ticket has
   room to move.

3. **For risk teams: monitor absolute fraud value, not just the rate.**
   The rate improved (1 in 58,177 → 1 in 78,408) while monthly fraud value rose
   98%. Set alerts on ₹ crore lost per month alongside FTS in basis points, and
   invest in mule-account detection and first-time-recipient friction, which
   scale with transaction count rather than with ticket size.

4. **For the card networks and issuers: defend the small-ticket swipe.**
   Credit-card volume grew 23% but value fell 6%, and the average ticket
   dropped 24%. Small-ticket credit is migrating to UPI-linked credit; issuers
   should compete on rewards and credit-at-checkout for small merchants instead
   of terminal economics.

5. **For policymakers: keep the large-value rails funded.**
   NEFT carries 48% of retail value and RTGS moves ₹72 lakh per transaction on
   average. UPI's success is not a reason to under-invest in NEFT/RTGS capacity,
   settlement resilience or cheque-clearing migration, because that is where the
   money — and the systemic risk — still sits.

---

## Data quality notes (worth stating in the report)

- **The two sources agree.** For Sep 2025, NPCI reports 19,633.43 Mn UPI
  transactions and RBI reports 196,334.33 lakh, which is the same number
  (1 lakh = 0.1 million). The pipeline checks this automatically and prints the
  comparison on every run.
- **Units.** NPCI reports volume in millions and value in ₹ crore; RBI reports
  volume in lakh and value in ₹ crore. The pipeline converts lakh → million and
  keeps value in crore throughout.
- **Provisional data.** The RBI release states that its data is provisional;
  the latest month can be revised.
- **Different windows.** The monthly UPI series is Jun 2025 – Mar 2026; the RBI
  snapshot covers FY 2025-26 to date, Sep 2025, Aug 2026 and Sep 2026. The
  "year on year" comparisons use Sep 2025 vs Sep 2026, the only same-month pair
  available.
- **Derived, not reported.** Average ticket size, per-day averages and
  month-on-month growth are computed here; the sources do not publish ticket
  size.
