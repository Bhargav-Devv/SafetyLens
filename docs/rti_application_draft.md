# RTI application — Form 18 accident narratives

**TASK-210. Draft, ready to fill in and send. Not sent.**

`docs/findings_indian_data.md` established that Form 18 narratives exist by statute and are published
nowhere. An RTI request under the Right to Information Act 2005 is the only public route to them.

Three things make an RTI request succeed or fail, and all three are built into the draft below:

1. **Ask for records, not analysis.** A PIO must supply information "held in material form". A
   request phrased as *"how many accidents were caused by X"* invites a refusal under Section 2(f);
   a request for *copies of a named form for a named period* does not.
2. **Pre-empt Section 8(1)(j).** Personal information is exempt. Asking for the narrative fields with
   names, addresses and factory identity **redacted** removes the strongest ground for refusal, and
   costs nothing — the model needs the description, not the identity.
3. **Bound it.** An unbounded request gets refused as disproportionately diverting resources under
   Section 7(9). One year, one division, is defensible and is enough to test transfer.

---

## File it online — Telangana takes RTI applications through a portal

**`rti.telangana.gov.in`** accepts RTI applications and first appeals online, with a payment gateway
covering net banking, debit/credit card, RuPay and UPI. It serves 114 public authorities. That turns
this from "post an application with a ₹10 postal order" into a web form and a ₹10 UPI payment.

Two things to check when you get there:

1. **Whether the Department of Factories is among the 114 authorities listed.** If it is, select it
   and paste the text below into the application field. If it is not, the portal is not the route —
   file by post to the address below instead, and note in the project that the department was not
   covered, because that is itself a small finding about how reachable this data is.
2. **The character limit** on the application field. Portals commonly cap it (often 3,000
   characters). The request below is written to fit; if it is still too long, attach the full text as
   a PDF and put points 1–4 in the field.

The department also publishes its own RTI page at `tgfactories.cgg.gov.in/Rti.do`, which should carry
the current Public Information Officer and First Appellate Authority by name. It returned 403 to an
automated fetch, so **open it in a browser and put the PIO's name and designation into the address
block below** — an application addressed to the correct officer by designation is harder to misroute.

## Where to send it (if filing on paper)

The Public Information Officer at the state Directorate of Factories / Inspectorate of Factories.
For Telangana this is the **Directorate of Factories, Government of Telangana, Hyderabad**. Every
state has its own; the RTI online portal at `rtionline.gov.in` covers central bodies, and most states
run their own portal.

**Fee:** ₹10, by Indian Postal Order, demand draft, or online. Students below the poverty line are
exempt; ordinary students are not, so budget the ₹10 plus any per-page copying charge.

**Timeline:** 30 days for a reply. A "no such information held" answer is itself a result worth
recording in the project.

---

## The application

> **To**
> The Public Information Officer
> Directorate of Factories, Government of [STATE]
> [ADDRESS]
>
> **Subject:** Request for information under Section 6(1) of the Right to Information Act, 2005
>
> Sir/Madam,
>
> I am a student of [COLLEGE], conducting an academic project on the automated classification of
> workplace hazards from accident descriptions. I request the following information.
>
> **1.** For accidents reported to your office under Section 88 of the Factories Act, 1948 in
> **Form 18** (Notice of Accident) during the calendar year **[YEAR]**, in **[DISTRICT / DIVISION]**,
> copies of the following fields only:
>
> - (a) the description of the accident recorded in Part B of Form 18;
> - (b) the cause and contributing factors recorded in Part D;
> - (c) the nature of injury recorded in Part C;
> - (d) the date of the accident;
> - (e) the industry classification of the factory.
>
> **I do not seek the name, address or licence number of any factory, the name or any personal
> particulars of any injured person, or any other personal information.** I request that the
> information be provided with all such particulars redacted. This is to avoid any question arising
> under Section 8(1)(j) of the Act, as the identity of the persons and establishments concerned is
> not required for the purpose stated above.
>
> **2.** The total number of Form 18 notices received by your office in the calendar year **[YEAR]**.
>
> **3.** Whether the information at point 1 is maintained in electronic form, and if so in what
> format. If it is available as a spreadsheet or database export, I request it in that form, which
> would reduce the copying effort for your office.
>
> **4.** Whether any of the information at point 1 is already published, and if so where.
>
> I am willing to pay the prescribed fee and any additional copying charges. The application fee of
> ₹10 is enclosed by [Indian Postal Order / DD no. …].
>
> If any part of this request is held to be exempt, I request that the remainder be provided under
> Section 10(1) of the Act, along with the reasons for the partial refusal.
>
> Yours faithfully,
> **[NAME]**
> [ADDRESS] · [EMAIL] · [PHONE]
> Date: [DATE]

---

## What to do with the answer, either way

| Answer | What it means for the project |
|---|---|
| Narratives supplied | TASK-211 becomes live: train on OSHA, test on Indian text, report the drop honestly |
| Supplied but as scanned PDFs | Still usable; adds an OCR step. Worth saying so in the write-up |
| Refused under 8(1)(j) despite the redaction request | A finding. Record the section cited and the reasoning |
| "Not held in electronic form" | The strongest possible confirmation of `findings_indian_data.md` — the records exist on paper and are unreachable at scale |
| No reply in 30 days | First appeal to the First Appellate Authority; also a finding |

**Every one of those outcomes is reportable.** The project's claim is about disclosure policy, and a
refusal letter is evidence for that claim rather than an obstacle to it.
