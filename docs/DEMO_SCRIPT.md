# Demo script

A walkthrough for the demo video, about 6–8 minutes. It follows Meera's journey ([PRODUCT_DESIGN.md §5](PRODUCT_DESIGN.md#5-user-journey)), and its centre is one scenario: **promote Ravi Kumar to L4 with a 12% raise.**

The figures below come from a fresh seed (`python -m app.seed`), seen on 15 Nov 2026. Headcounts and "this quarter" figures depend on the day you record, so read them off the screen rather than this script.

## Before recording

- **Fresh data.** Ravi's promotion is saved during the demo, so run the seed with `--reset` first if you've rehearsed. It clears and reloads the demo data, so never run it against data you want to keep.
- **Wake the API** if it's on Render's free plan: open `/api/v1/health` a minute before you start.
- **Browser:** a 1440 px wide window, zoomed to 100%, with nothing signed in yet.

---

## 1. Sign in (20 s)

Open the app. Every page redirects to sign in.

- Enter a wrong password once: the error doesn't say which field was wrong.
- Sign in with the HR email and password.

> "There's one HR Manager login. Salary data shouldn't sit behind a public URL, but one persona doesn't need user management."

## 2. Orient: Overview (45 s)

- **KPI cards:** active headcount (9,505), total annual target pay (about $615M), median total pay ($52,385) and the share paid within band (85.2%).
- **Needs your attention:** 668 below band, 168 changes taking effect soon, 644 above band and 12 missing a package.
- **Median total pay by country:** in USD at fixed reference rates, from the United States (about $95k) down to India (about $27k).

> "Everything is converted at fixed reference rates for comparison. Each profile shows the local currency."

## 3. Find Ravi (30 s)

- Press **⌘K** and type "Ravi". Pick **Ravi Kumar**.
- Optionally, show the directory first: filter **Country = India** and **Department = Engineering**, and point out that the filters are in the URL and the table is paged on the server.

## 4. Understand: Ravi's profile (60 s)

Ravi is a Software Engineer L3 in India, paid in INR.

- **Package:** base ₹24,00,000, housing allowance ₹30,000 a month and meal allowance ₹2,200 a month (both shown annualised), and a 10% bonus target (a role default).
  - Total target pay is ₹30,26,400, about $36,317.
  - Open **How is this calculated?**
- **One-time sign-on bonus** of ₹1,50,000 is shown separately and left out of the total.
- **Band:** L3 India runs from ₹22,00,000 to ₹32,00,000, with a ₹27,00,000 midpoint. His compa-ratio is 0.89: in band, ₹3,00,000 below the midpoint.
- **History:** hire in 2022, two merit increases and a promotion to L3, each with the percentage change.

## 5. Act: promote Ravi to L4 (90 s), the key moment

Click **Revise compensation**.

1. **Reason:** Promotion. **Effective from:** 1 Jan 2027.
2. Tick **Promote to Software Engineer L4**. The L4 defaults apply: the bonus target goes from 10% to 15%.
3. Click the **+12%** quick pick. The new base is ₹26,88,000.
4. Read the **live preview**. Nothing is saved yet:
   - Target variable pay is ₹4,03,200, and total target pay goes from ₹30,26,400 to ₹34,77,600.
   - The band is now **L4 India: ₹28,00,000 to ₹38,00,000**, and his compa-ratio is **0.81**.
   - The amber warning says he's **still below the band minimum, ₹1,12,000 short**.

> "This is the point of the preview. A 12% promotion raise sounds generous, but it still leaves Ravi under the L4 minimum. Meera finds out before she saves, not in next quarter's audit."

5. Optionally, click **Band minimum** to show the fix, then go back to +12% so the exception appears later.
6. Click **Review change**. The confirmation sentence reads: *"Promotion to Software Engineer L4, effective 1 Jan 2027. Base ₹24,00,000 → ₹26,88,000 (+12.0%), bonus target 15%."*
7. **Confirm & save.** The success message says it takes effect on 1 Jan 2027 and shows as pending until then.

## 6. Confirm: the change is recorded (30 s)

- **Back to Ravi's profile.** His current package hasn't changed, and the promotion appears as **pending** from 1 Jan 2027.
- **Overview → Recent pay changes:** Ravi's promotion is at the top, "Pending · 1 Jan 2027, +12.0%".

> "History is effective-dated. Nothing is overwritten: the current package stays in the record, and the new one takes over on its date."

## 7. Review: Exceptions (45 s)

Open **Exceptions** from the sidebar (the badge counts what needs attention).

- **Below band** lists the base, the band minimum and the gap, largest gap first, with **Review** opening the profile.
- **Above band** is framed as worth a look, not a problem.
- **Pending changes** now includes Ravi's promotion.
- **Missing package** shows the people left out of averages until a package is added.
- Click **Export list** to show the CSV.

> "Below band is amber, never red. It's a prompt to review, not an error."

## 8. Answer: Insights (75 s)

> "How do we pay engineers across countries, and what does India look like?"

- **Company-wide, grouped by country:** salary ranges (min → max with the median), fixed vs variable pay, and position against bands.
- **Filter Country = India.** Amounts switch to rupees:
  - 2,633 active people, a median of about ₹22.6 lakh, and ₹657.8 Cr in total.
  - The pay histogram uses ₹10 L brackets.
  - Toggle **USD** to compare, then switch back.
- **Group by Department** within India. Engineering has the highest median (about ₹28 lakh), and Sales has the largest variable share (about 19%) because of commission.
- **Add Department = Engineering.** Grouping switches to level, so you see pay rise from L1 to L5.
- Click **See these employees in the directory**. The same filters carry over.

## 9. Share and leave (20 s)

- In the directory, with the filters still applied, click **Export CSV**: it contains exactly the filtered list.
- **Sign out.** You're back at the sign-in page, and the API refuses requests without a session.

---

## Talking points, if there's time

- **Money is integers.** Amounts are stored as integer minor units with a currency, never as floats, and rounding is half-to-even.
- **The rules are tested where they live.** Every rule (edge cases E1–E25 in [COMPENSATION_MODEL.md](COMPENSATION_MODEL.md)) is in a pure domain layer with full test coverage. The UI mirrors the rules for fast feedback, but the server decides.
- **It's fast at 10,000 employees.** Every list and insight endpoint is under 300 ms p95, on SQLite and on Postgres ([PERFORMANCE.md](PERFORMANCE.md)).
- **It was built test-first with AI,** and [AI_USAGE.md](AI_USAGE.md) records where its output was corrected.
