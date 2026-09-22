"""Build /chapter-7-guide/ (and later /chapter-13-guide/) from the pro-se template (9/18/26).

Why a script: every hub page shares one head/style/nav/footer/donate/most-read shell. Cloning the
shell by hand drifts; this reads pro-se/index.html at build time and swaps ONLY the page-specific
parts (title, description, canonical, OG, Article/Breadcrumb/FAQ schema, hero, main). Re-runnable.

Usage: python scripts/build_chapter_guide.py [--check]   (--check = build to stdout only)
"""
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "pro-se", "index.html")
SITE = "https://openbankruptcyproject.org"

# ------------------------------------------------------------------ content
CH7 = {
    "slug": "chapter-7-guide",
    "title": "Chapter 7 Bankruptcy: How It Works, Who Qualifies, Step by Step [2026]",
    "h1": "Chapter 7 Bankruptcy: How It Works",
    "label": "Consumer Guide",
    "description": (
        "Chapter 7 bankruptcy explained in plain English: who qualifies under the means test, the process "
        "from credit counseling to discharge, what property you keep, what debts are wiped out, costs and fee "
        "waivers, and the forms. Free 501(c)(3) guide, not legal advice."
    ),
    "lede": (
        "Chapter 7 is the liquidation chapter of the Bankruptcy Code. A trustee collects any property that is "
        "not protected by an exemption, sells it, pays creditors from the proceeds, and the court discharges "
        "most remaining debts. In the large majority of consumer cases nothing is sold, because everything the "
        "debtor owns is exempt, and the whole process takes about three to four months. This page walks through "
        "who qualifies, what happens in what order, what you keep, and what it costs."
    ),
    "updated": "2026-09-18",
    "faq": [
        ("How long does Chapter 7 take?",
         "Most consumer cases run about 90 to 120 days from filing to discharge. The meeting of creditors is set "
         "21 to 40 days after filing, creditors and the trustee then have 60 days from that first meeting date to "
         "object, and the discharge usually enters shortly after that window closes. Cases where the trustee "
         "sells property stay open longer while the assets are administered."),
        ("Who qualifies for Chapter 7?",
         "Individuals, married couples filing jointly, and businesses can file. Individuals with primarily "
         "consumer debts must pass the means test in 11 U.S.C. section 707(b): if household income over the six "
         "months before filing is below the state median for the household size, the test is passed; if it is "
         "above, a second calculation of allowed expenses decides whether a presumption of abuse arises. "
         "Everyone must complete credit counseling within 180 days before filing."),
        ("Will I lose my house or car in Chapter 7?",
         "Only property that is not covered by an exemption can be taken by the trustee. Exemptions are set by "
         "state law, or by the federal list in states that allow it, and protect a set amount of home equity, "
         "vehicle equity, household goods, retirement accounts, and other property. If a home or car is worth "
         "less than the loan plus the exemption, there is nothing for the trustee to sell. Secured loans "
         "survive unless you keep paying, reaffirm, redeem, or surrender the collateral."),
        ("What debts does Chapter 7 not discharge?",
         "Section 523(a) excepts child support and alimony, most recent income taxes, student loans unless the "
         "court finds undue hardship, criminal fines and restitution, debts from drunk-driving injuries, and "
         "debts the court finds were incurred by fraud if the creditor objects in time. Liens on secured debts "
         "also survive the discharge."),
        ("How much does Chapter 7 cost?",
         "The court filing fee is $338. It can be paid in up to four installments within 120 days, and the court "
         "can waive it entirely for a debtor whose income is below 150 percent of the federal poverty guideline "
         "and who cannot pay in installments. The required counseling and education courses each cost a small "
         "fee that approved providers set, often waived for low-income debtors. Attorney fees are separate, "
         "vary by district and case, and must be disclosed to the court."),
        ("Can I file Chapter 7 again?",
         "Not if you received a Chapter 7 discharge in a case filed within the past eight years, or a Chapter 13 "
         "discharge in a case filed within the past six years unless that plan paid unsecured creditors in full, "
         "or at least 70 percent with the plan proposed in good faith and as your best effort. The discharge "
         "screener on this site checks those timing bars."),
        ("Do I need a lawyer to file Chapter 7?",
         "An individual may file without one. The forms and the process are the same either way, and the "
         "trustee and the court hold a self-represented filer to the same rules. Business entities generally "
         "must appear through counsel. See the pro se guide on this site for what the court expects from an "
         "unrepresented filer."),
    ],
}

def ch7_main():
    return """
<h2 id="what-it-is">What Chapter 7 is</h2>
<p>Chapter 7 is a court-supervised liquidation. On the day the petition is filed, everything the debtor owns becomes part of a bankruptcy estate, an <a href="/automatic-stay/">automatic stay</a> stops collection, and a trustee is appointed to review the case. The trustee's job is to find property that is not protected by an exemption, sell it, and distribute the money to creditors in the order the Code sets. When the case is over, the court enters a discharge order that permanently bars creditors from collecting most pre-filing debts.</p>
<p>Two facts shape nearly every consumer case. First, most people who file Chapter 7 own nothing the trustee can sell, because state or federal <a href="/exemptions/">exemptions</a> cover what they have; these are called no-asset cases, and they make up the large majority of consumer filings. Second, the discharge is broad but not total. Support obligations, most recent taxes, student loans, and secured liens survive it. The sections below take those in order.</p>

<h2 id="who-qualifies">Who qualifies</h2>
<p>Any individual, married couple, or business can file a Chapter 7 petition. Only individuals receive a discharge; a corporation or LLC that files Chapter 7 is wound up, not forgiven. For individuals, four gates matter:</p>
<ol>
<li><strong>The means test.</strong> A debtor whose debts are primarily consumer debts must complete Official Form 122A-1. It compares current monthly income, meaning average gross income over the six calendar months before filing, to the median for a household of the same size in the debtor's state. Below the median, the test is passed. Above it, Form 122A-2 subtracts allowed living expenses under IRS and local standards; if enough income remains to repay a meaningful share of unsecured debt, a presumption of abuse arises under 11 U.S.C. § 707(b)(2), and the case can be dismissed or converted to Chapter 13 unless the debtor shows special circumstances. The <a href="/means-test-calculator/">means test calculator</a> runs the first step; the <a href="/means-test-deep-dives/form-122a-1-income/">deep dives</a> walk through both forms line by line.</li>
<li><strong>Credit counseling.</strong> Section 109(h) requires an individual to complete a briefing from an approved credit counseling agency within the 180 days before filing. The certificate is filed with the petition.</li>
<li><strong>Prior discharges.</strong> Under § 727(a)(8) no discharge is available if the debtor received a Chapter 7 discharge in a case filed within eight years before this one; under § 727(a)(9), a Chapter 13 discharge in a case filed within six years bars it unless that plan paid unsecured claims in full, or at least 70 percent with the plan proposed in good faith and as the debtor's best effort. The <a href="/screener/">discharge screener</a> checks the dates.</li>
<li><strong>Prior dismissals.</strong> A case dismissed within the previous 180 days for willful failure to obey court orders, or voluntarily dismissed after a creditor sought relief from the stay, bars refiling for 180 days under § 109(g).</li>
</ol>
<div class="callout"><strong>Business debts.</strong> If more than half of a debtor's total debt is business debt rather than consumer debt, the means test does not apply. The same is true for certain disabled veterans and for reservists and National Guard members called to active duty, under § 707(b)(2)(D).</div>

<h2 id="process">The process, step by step</h2>
<ol>
<li><strong>Credit counseling.</strong> Complete the briefing and keep the certificate. Approved providers are listed by the United States Trustee Program.</li>
<li><strong>Gather the record.</strong> Six months of pay stubs or other income proof, the last two years of federal tax returns, a complete list of creditors with addresses and balances, titles and loan statements for vehicles and real estate, bank statements, and any lawsuits or garnishments. The schedules are only as accurate as this pile.</li>
<li><strong>Complete the forms.</strong> The petition, schedules, statement of financial affairs, means test forms, statement of intention, and creditor matrix. The full list is in the <a href="#forms">forms section</a> below.</li>
<li><strong>File and pay the fee.</strong> The filing fee is $338. Official Form 103A asks to pay it in up to four installments, the last within 120 days of filing (extendable to 180 days for cause). Official Form 103B asks the court to waive the fee entirely for a debtor whose income is below 150 percent of the federal poverty guideline and who cannot pay in installments.</li>
<li><strong>The automatic stay begins.</strong> Filing itself triggers § 362. Collection calls, lawsuits, garnishments, repossessions, and foreclosures must stop, with the exceptions described on the <a href="/automatic-stay-scope-exceptions/">stay exceptions page</a>. A repeat filer within a year gets a shorter or no stay unless the court extends it.</li>
<li><strong>The trustee is assigned and asks for documents.</strong> Section 521 requires the most recent federal tax return to reach the trustee at least seven days before the meeting of creditors. Trustees also routinely request bank statements, pay stubs, and vehicle and property records.</li>
<li><strong>File the statement of intention.</strong> Official Form 108 tells secured creditors, within 30 days of filing, whether you will surrender the collateral, reaffirm the debt, or redeem the property. The court dismisses the stay's protection of that property if the statement is late or not acted on.</li>
<li><strong>The meeting of creditors.</strong> Under Bankruptcy Rule 2003 it is held 21 to 40 days after filing. The trustee questions the debtor under oath, usually for a few minutes; creditors may attend but rarely do. Bring government identification and proof of Social Security number.</li>
<li><strong>The 60-day window.</strong> Creditors and the trustee have 60 days from the first date set for the meeting to object to the discharge or to the dischargeability of a particular debt. Reaffirmation agreements must be filed before the discharge enters.</li>
<li><strong>Debtor education.</strong> A second course, after filing, must be completed and certified on Official Form 423 within 60 days of the first meeting date. A case that closes without it closes without a discharge, and reopening to file the certificate costs a fee.</li>
<li><strong>Discharge.</strong> With no objections pending, the court enters the discharge order shortly after the 60-day window closes, typically 90 to 120 days after filing. In a no-asset case the court closes the case soon after. In an asset case the trustee's administration continues, sometimes for a year or more, but the discharge itself does not wait for it.</li>
</ol>

<h2 id="timeline">Timeline at a glance</h2>
<div class="card">
<ul>
<li><strong>Day 0:</strong> petition filed; automatic stay in force; trustee appointed within a day or two.</li>
<li><strong>Day 7 (at the latest):</strong> pay stubs and remaining schedules due if not filed with the petition (Rule 1007).</li>
<li><strong>Day 21 to 40:</strong> meeting of creditors.</li>
<li><strong>Day 30 (or the meeting, if earlier):</strong> statement of intention due.</li>
<li><strong>Meeting + 60 days:</strong> deadline to object to discharge; debtor education certificate due.</li>
<li><strong>Roughly day 90 to 120:</strong> discharge order.</li>
</ul>
<p style="margin:0">The <a href="/deadline-calculator/">deadline calculator</a> computes these dates from a petition date.</p>
</div>

<h2 id="what-you-keep">What you keep</h2>
<p>The trustee can sell only property that is not exempt. Every state has an exemption list, most states require their residents to use it, and a minority let debtors choose the federal list in § 522(d) instead. Typical categories are equity in a home (the homestead exemption), equity in one vehicle, household goods and clothing, tools of the trade, retirement accounts, and a "wildcard" amount that can be applied to anything. Amounts differ sharply by state; a homestead exemption can be a few thousand dollars in one state and unlimited in another.</p>
<p>Two practical rules follow. Equity, not value, is what matters: a car worth $12,000 with an $11,000 loan has $1,000 of equity, and most vehicle exemptions cover that easily. Exemptions are claimed on Schedule C, and property left off the schedule is not protected by silence. The <a href="/exemptions/">exemptions overview</a> explains the federal-versus-state choice, and each <a href="/states/">state page</a> lists that state's figures.</p>
<p>Secured debts are handled separately. The discharge removes personal liability on a car loan or mortgage, but the lender's lien on the collateral survives. To keep the property, the debtor keeps paying, or signs a reaffirmation agreement under § 524(c) that makes the debt survive the discharge, or redeems it under § 722 by paying the lender its current value in a lump sum. To let it go, the debtor surrenders it and owes nothing more.</p>

<h2 id="discharge">What is discharged, and what is not</h2>
<p>The discharge under § 727 covers most unsecured debts that existed on the filing date: credit cards, medical bills, personal loans, deficiency balances after a repossession, old utility bills, most judgments, and business debts an individual guaranteed. Section 523(a) carves out the exceptions:</p>
<ul>
<li>Domestic support obligations, and most other debts arising from a divorce or separation.</li>
<li>Income taxes for recent tax years, taxes for which no return was filed, and any tax connected to fraud. Older income taxes with timely filed returns can be discharged if they meet the timing rules in § 507(a)(8) and § 523(a)(1).</li>
<li>Student loans, unless the debtor proves undue hardship in a separate proceeding.</li>
<li>Criminal fines, penalties, and restitution.</li>
<li>Debts for death or injury caused by driving while intoxicated.</li>
<li>Debts incurred by fraud, false financial statements, embezzlement, or willful and malicious injury, but only if the creditor sues within the 60-day window and wins.</li>
<li>Debts not listed in the schedules, in districts that follow that rule, when the creditor had no notice of the case.</li>
</ul>
<p>A discharge can also be denied entirely under § 727(a) for concealing or transferring property, destroying records, lying under oath in the case, or failing to explain a loss of assets. Those grounds are why the schedules and the meeting of creditors matter. The <a href="/debt-relief/">debt dischargeability guide</a> goes debt type by debt type.</p>

<h2 id="costs">Costs</h2>
<ul>
<li><strong>Filing fee:</strong> $338, paid at filing, in installments (Form 103A), or waived (Form 103B) for income under 150 percent of the poverty guideline. The <a href="/fee-guide/">fee guide</a> covers the fee, the waiver standard, and how attorney fees must be disclosed.</li>
<li><strong>Courses:</strong> the pre-filing counseling and post-filing education courses each carry a provider fee, commonly under $50, and approved providers must waive it for debtors who cannot afford it.</li>
<li><strong>Attorney fees:</strong> most Chapter 7 attorneys charge a flat fee paid before filing, because a fee owed at filing would itself be a dischargeable debt. Amounts vary by district and by how complex the case is. Every fee must be disclosed to the court on the attorney's Form 2030 statement, and the court can review any fee for reasonableness under § 329.</li>
<li><strong>Reopening:</strong> a case closed without the education certificate can be reopened to file it, for a separate fee.</li>
</ul>

<h2 id="forms">The forms</h2>
<p>All Official Forms are free at uscourts.gov. An individual Chapter 7 case uses:</p>
<ul>
<li><strong>Form 101</strong>, the voluntary petition, with Form 121 (Social Security number statement) filed alongside but not on the public docket.</li>
<li><strong>Form 106</strong>: the summary, plus Schedules A/B (property), C (exemptions), D (secured creditors), E/F (unsecured creditors), G (contracts and leases), H (codebtors), I (income), and J (expenses).</li>
<li><strong>Form 107</strong>, the statement of financial affairs: income history, payments to creditors before filing, lawsuits, transfers, closed accounts.</li>
<li><strong>Form 108</strong>, the statement of intention for secured debts and leases.</li>
<li><strong>Forms 122A-1 and 122A-2</strong>, the means test; 122A-1Supp for the business-debt and military exemptions.</li>
<li><strong>The creditor matrix</strong>, a plain list of every creditor's name and mailing address in the format the district's clerk specifies.</li>
<li><strong>The counseling certificate</strong> at filing and <strong>Form 423</strong> after the education course.</li>
<li><strong>Local forms</strong>, which vary by district; each court's website lists them. The <a href="/forms/">forms reference</a> explains what each Official Form asks for.</li>
</ul>

<h2 id="mistakes">Mistakes that cost people their discharge</h2>
<ul>
<li>Transferring property to a relative or friend before filing. The trustee can recover it, and hiding the transfer is grounds to deny the discharge.</li>
<li>Repaying a family member or a favored creditor shortly before filing. Payments over $600 to an ordinary creditor within 90 days, or to an insider within a year, can be clawed back by the trustee as preferences under § 547.</li>
<li>Running up credit cards or taking cash advances before filing. Luxury purchases over the statutory threshold within 90 days, and cash advances within 70 days, are presumed nondischargeable.</li>
<li>Leaving a creditor off the schedules, or guessing at balances instead of pulling records.</li>
<li>Missing the meeting of creditors, or arriving without identification.</li>
<li>Skipping the debtor education course, which closes the case with no discharge.</li>
<li>Filing before checking the means test or the eight-year rule, when a short wait would have changed the answer.</li>
</ul>
<div class="callout"><strong>This page is education, not advice.</strong> It describes how the Code and Rules work in general. Whether Chapter 7 fits a particular situation depends on facts this page cannot see. A consultation with a bankruptcy attorney admitted in your district, or a legal aid office, is the place to apply it to your case.</div>

<h2>Related resources</h2><div class="link-grid">
<a class="link-card" href="/means-test-calculator/"><div class="label">Tool</div><h4>Means test calculator</h4><p>Compare your six-month income to your state's median.</p></a>
<a class="link-card" href="/screener/"><div class="label">Tool</div><h4>Discharge screener</h4><p>Check the eight-year and six-year bars before filing.</p></a>
<a class="link-card" href="/exemptions/"><div class="label">Guide</div><h4>Exemptions</h4><p>Federal versus state schemes, and what each protects.</p></a>
<a class="link-card" href="/states/"><div class="label">Guide</div><h4>Your state</h4><p>Exemption amounts, income limits, and courts by state.</p></a>
<a class="link-card" href="/chapter-7-vs-13/"><div class="label">Guide</div><h4>Chapter 7 vs Chapter 13</h4><p>Which chapter fits: eligibility, timing, what you keep.</p></a>
<a class="link-card" href="/chapter-13-guide/"><div class="label">Guide</div><h4>Chapter 13, step by step</h4><p>The repayment plan: who qualifies, how the payment is set, why plans fail.</p></a>
<a class="link-card" href="/pro-se/"><div class="label">Guide</div><h4>Filing without a lawyer</h4><p>What the court expects from a self-represented filer.</p></a>
<a class="link-card" href="/forms/"><div class="label">Reference</div><h4>Bankruptcy forms</h4><p>What each Official Form asks for.</p></a>
<a class="link-card" href="/deadline-calculator/"><div class="label">Tool</div><h4>Deadline calculator</h4><p>Key dates from your petition date.</p></a>
</div>
"""

CH13 = {
    "slug": "chapter-13-guide",
    "title": "Chapter 13 Bankruptcy: How the Repayment Plan Works, Step by Step [2026]",
    "h1": "Chapter 13 Bankruptcy: How It Works",
    "label": "Consumer Guide",
    "description": (
        "Chapter 13 bankruptcy explained in plain English: who qualifies, how the three-to-five-year plan is "
        "built, what it can do that Chapter 7 cannot, the process from filing to discharge, costs, forms, and "
        "why so many plans fail. Free 501(c)(3) guide, not legal advice."
    ),
    "lede": (
        "Chapter 13 lets an individual with regular income keep their property, including a home or car that is "
        "behind on payments, while paying creditors through a plan that lasts three to five years. Filing "
        "before a foreclosure sale stops the sale. Missed mortgage payments are spread across the plan while "
        "the regular payment resumes, and taxes and support arrears are paid on a schedule instead of all at "
        "once. When the last plan payment is made, the court discharges the debts the plan covered. This page "
        "covers who qualifies, how the monthly payment is set, each step from filing to discharge, and what it "
        "takes for a plan to finish."
    ),
    "updated": "2026-09-22",
    "faq": [
        ("How long does a Chapter 13 plan last?",
         "Three years if the debtor's household income is below the state median, five years if it is above, "
         "and never more than five. A below-median debtor can propose a longer plan, up to five years, when a "
         "shorter one cannot fund the payments the Code requires. The discharge enters only after the last "
         "plan payment."),
        ("Who qualifies for Chapter 13?",
         "An individual, or a married couple, with regular income and debts under the limits in 11 U.S.C. "
         "section 109(e). Corporations and partnerships cannot file Chapter 13. The debtor must have completed "
         "credit counseling within 180 days before filing and must have filed federal tax returns for the four "
         "years before the case. A Chapter 7 discharge in a case filed within the past four years, or a Chapter "
         "13 discharge within the past two, bars the discharge but not the case itself."),
        ("How is the monthly payment set?",
         "By Form 122C. Below-median debtors pay what Schedule I income minus Schedule J expenses leaves each "
         "month. Above-median debtors pay their disposable income as calculated under the means test expense "
         "standards. Whatever the number, the plan must pay priority claims such as support and recent taxes in "
         "full, must cure secured arrears the debtor wants to keep, and must give unsecured creditors at least "
         "what they would have received in a Chapter 7 liquidation."),
        ("Can Chapter 13 stop a foreclosure?",
         "Yes, as long as the case is filed before the foreclosure sale. The automatic stay stops the sale, the "
         "arrears are spread across the plan, and the regular mortgage payment continues. The lender can ask "
         "the court to lift the stay if post-filing payments are missed, so the plan only works if the ongoing "
         "payment is affordable."),
        ("What does Chapter 13 discharge that Chapter 7 does not?",
         "The Chapter 13 discharge under section 1328(a) reaches a few debts the Chapter 7 discharge excepts: "
         "property-settlement obligations from a divorce that are not support, and debts for willful and "
         "malicious injury to property. It does not reach support, student loans absent undue hardship, "
         "recent taxes, drunk-driving injury debts, criminal restitution, or long-term debts like a mortgage "
         "that run past the plan."),
        ("Why do so many Chapter 13 cases fail?",
         "Nationally, of Chapter 13 cases that reached termination in the Federal Judicial Center data this "
         "site uses, 58.3 percent were dismissed and 41.7 percent ended in discharge. The usual causes are a "
         "plan payment built on an optimistic budget, a job loss or medical event mid-plan, and missed "
         "trustee payments with no modification filed in time. A dismissed case returns the debtor to where "
         "they started, minus the payments made."),
        ("How much does Chapter 13 cost?",
         "The court filing fee is $313, payable in installments but not waivable. The trustee keeps a "
         "percentage of each plan payment, set by the United States Trustee for the district and capped at "
         "ten percent, to fund the trustee's office. Attorney fees are usually paid through the plan rather "
         "than up front, in amounts many districts set by local rule; every fee must be disclosed to the court."),
    ],
}

def ch13_main():
    return """
<h2 id="what-it-is">What Chapter 13 is</h2>
<p>Chapter 13 is a reorganization for an individual with regular income. The debtor keeps all property, proposes a plan to pay creditors out of future income for three to five years, and makes one payment a month to a standing trustee, who distributes it to creditors in the order the plan and the Code set. When the last payment is made, the court enters a discharge of the debts the plan covered. The <a href="/automatic-stay/">automatic stay</a> protects the debtor for the life of the case, and a separate co-debtor stay under § 1301 protects anyone who co-signed a consumer debt.</p>
<p>The trade is time for control. A Chapter 7 case is over in months and takes any non-exempt property; a Chapter 13 case lasts years and takes none, but every one of those months has a payment in it. The <a href="/chapter-7-vs-13/">comparison guide</a> sets the two side by side. This page covers Chapter 13 on its own terms.</p>

<h2 id="who-qualifies">Who qualifies</h2>
<ol>
<li><strong>Individuals only.</strong> Section 109(e) admits individuals, including sole proprietors, with regular income. Corporations, LLCs, and partnerships cannot file Chapter 13; they use Chapter 11 or Chapter 7.</li>
<li><strong>Debt limits.</strong> Section 109(e) caps the debts a Chapter 13 debtor can carry. The figures are adjusted every three years; as adjusted April 1, 2025, they are $526,700 in noncontingent, liquidated unsecured debt and $1,580,125 in noncontingent, liquidated secured debt. A debtor above either limit looks to Chapter 11, including its Subchapter V.</li>
<li><strong>Regular income.</strong> Wages, self-employment, retirement, benefits, or support, in any combination steady enough to fund a plan. The court looks at whether the budget is credible, not at the source.</li>
<li><strong>Tax returns.</strong> Section 1308 requires the debtor to have filed all federal returns for the four tax years before the petition by the day before the meeting of creditors. Unfiled returns are one of the most common reasons a case stalls.</li>
<li><strong>Credit counseling.</strong> As in every consumer chapter, a briefing from an approved agency within 180 days before filing.</li>
<li><strong>Prior discharges.</strong> Under § 1328(f), a Chapter 7 discharge in a case filed within four years, or a Chapter 13 discharge in a case filed within two years, bars a discharge in the new case. The case can still be filed to use the stay and cure arrears, but it ends without a discharge. The <a href="/screener/">discharge screener</a> checks the dates.</li>
</ol>

<h2 id="what-it-does">What Chapter 13 can do that Chapter 7 cannot</h2>
<ul>
<li><strong>Cure a mortgage default.</strong> Missed payments are added to the plan and paid over its term while the regular payment resumes; the lender must accept the cure under § 1322(b)(5).</li>
<li><strong>Keep non-exempt property.</strong> Instead of surrendering property to a trustee, the debtor pays unsecured creditors at least the property's non-exempt value through the plan, the "best interests" test of § 1325(a)(4).</li>
<li><strong>Reduce some car loans to the car's value.</strong> A vehicle loan taken more than 910 days before filing, or a loan on other personal property taken more than a year before, can be "crammed down" to the collateral's value, with the rest treated as unsecured.</li>
<li><strong>Remove a wholly unsecured junior mortgage.</strong> Where the home is worth less than the first mortgage, a second mortgage or HELOC can be stripped and paid as unsecured, in the circuits that allow it in Chapter 13.</li>
<li><strong>Pay taxes and support arrears on a schedule.</strong> Priority claims must be paid in full, but over up to five years and, for most taxes, without further penalties.</li>
<li><strong>Protect co-signers.</strong> The § 1301 co-debtor stay stops collection against a co-signer of a consumer debt while the plan pays it.</li>
<li><strong>Discharge a few debts Chapter 7 excepts.</strong> Divorce property-settlement obligations that are not support, and willful and malicious injury to property, are discharged under § 1328(a).</li>
</ul>

<h2 id="the-plan">How the plan is built</h2>
<p>The plan is a short document, on Official Form 113 or the district's own form, that says how much the debtor pays each month, for how long, and who gets it. Three rules fix the shape:</p>
<ol>
<li><strong>The commitment period.</strong> Form 122C-1 compares household income to the state median. Below the median, the plan runs at least three years; above it, five. Nothing runs past five.</li>
<li><strong>The payment.</strong> A below-median debtor pays what Schedule I income leaves after Schedule J expenses. An above-median debtor's disposable income is computed on Form 122C-2 using the means-test expense standards, and all of it goes to the plan. The <a href="/means-test-deep-dives/form-122c-chapter-13/">Form 122C deep dive</a> walks the calculation.</li>
<li><strong>The floors.</strong> Priority claims (support, recent taxes, administrative expenses) are paid in full. Secured creditors whose collateral the debtor keeps receive the arrears cure or the crammed-down value, with interest. Unsecured creditors receive at least what a Chapter 7 liquidation would have paid them, and, if the debtor is above median, all disposable income for the full commitment period. Everything left after those floors is what unsecured creditors actually receive, and in many plans it is a small percentage of what they are owed.</li>
</ol>
<div class="callout"><strong>The number that decides everything</strong> is the monthly payment. A plan the debtor cannot actually pay confirms just as easily as one they can, and it fails in month eight instead of month one. The budget on Schedule J should be the real one.</div>

<h2 id="process">The process, step by step</h2>
<ol>
<li><strong>Credit counseling</strong> within 180 days before filing.</li>
<li><strong>Gather the record</strong>: six months of income proof, four years of filed tax returns, every creditor with balance and address, mortgage and vehicle statements showing arrears, and a realistic monthly budget.</li>
<li><strong>Complete the forms</strong>: the petition and schedules, the statement of financial affairs, Forms 122C-1 and 122C-2, and the plan. The <a href="#forms">forms section</a> lists them.</li>
<li><strong>File and pay the fee.</strong> The filing fee is $313. It may be paid in installments under Rule 1006 but, unlike Chapter 7, cannot be waived. The plan is due with the petition or within 14 days (Rule 3015(b)).</li>
<li><strong>The automatic stay begins.</strong> Foreclosure, repossession, garnishment, and collection stop. A repeat filer within a year gets a 30-day stay unless the court extends it on motion.</li>
<li><strong>The first payment.</strong> Section 1326(a)(1) requires the first plan payment within 30 days of filing, before confirmation and before the meeting of creditors. Missing it is the fastest route to dismissal.</li>
<li><strong>The meeting of creditors.</strong> Held 21 to 50 days after filing under Rule 2003. The trustee reviews the budget, the plan, and the tax returns, and asks questions under oath.</li>
<li><strong>Objections and confirmation.</strong> The trustee and creditors may object to the plan. The confirmation hearing is set no earlier than 20 and no later than 45 days after the meeting of creditors (§ 1324). Plans are often amended once or twice before confirmation to satisfy the trustee.</li>
<li><strong>Payments for 36 to 60 months.</strong> By payroll deduction in many districts, or by the debtor directly. The trustee distributes to creditors, files reports, and watches for missed payments.</li>
<li><strong>Changes along the way.</strong> A plan can be modified after confirmation under § 1329 when income or expenses change. New debt during the plan needs trustee or court approval. If completing the plan becomes impossible for reasons beyond the debtor's control, a hardship discharge under § 1328(b) may be available.</li>
<li><strong>Debtor education</strong> at any point before the last payment, certified on Form 423.</li>
<li><strong>Discharge and closing.</strong> After the final payment, the trustee audits the case, the debtor certifies that support obligations are current, and the court enters the discharge under § 1328(a).</li>
</ol>

<h2 id="timeline">Timeline at a glance</h2>
<div class="card">
<ul>
<li><strong>Day 0:</strong> petition filed; automatic stay in force; a standing trustee is assigned.</li>
<li><strong>Day 14 (at the latest):</strong> the plan and any schedules not filed with the petition are due (Rules 1007(c), 3015(b)).</li>
<li><strong>Day 30:</strong> first plan payment due to the trustee, before confirmation (&sect; 1326(a)(1)).</li>
<li><strong>Day 21 to 50:</strong> meeting of creditors (Rule 2003).</li>
<li><strong>Day 70:</strong> deadline for most creditors to file a proof of claim; government creditors have 180 days (Rule 3002(c)).</li>
<li><strong>Meeting + 20 to 45 days:</strong> confirmation hearing (&sect; 1324(b)).</li>
<li><strong>Months 36 to 60:</strong> monthly plan payments; the debtor education course is completed before the last one.</li>
<li><strong>After the final payment:</strong> the trustee's final report and the discharge under &sect; 1328(a).</li>
</ul>
<p style="margin:0">The <a href="/deadline-calculator/">deadline calculator</a> computes these dates from a petition date.</p>
</div>

<h2 id="discharge">What is discharged, and what is not</h2>
<p>The Chapter 13 discharge covers the unsecured debts the plan provided for, whether they were paid in full, in part, or not at all, plus the two categories noted above that Chapter 7 excepts. It does not cover support, student loans absent a finding of undue hardship, taxes for which returns were not filed or that involved fraud, criminal restitution and fines, drunk-driving injury debts, and debts incurred by fraud if the creditor objects. Long-term secured debts that run past the plan, a mortgage above all, survive and continue on their original terms. The <a href="/debt-relief/">debt dischargeability guide</a> goes debt type by debt type.</p>

<h2 id="why-plans-fail">Why plans fail</h2>
<p>Of Chapter 13 cases that reached termination in the Federal Judicial Center data this site uses, 58.3 percent were dismissed and 41.7 percent ended in discharge. The denominator is cases that reached an outcome, not cases filed. The pattern behind the number is consistent:</p>
<ul>
<li>A payment set from a budget that had no room for a car repair, a medical bill, or a month of reduced hours.</li>
<li>A job change or income loss with no modification filed before payments were missed.</li>
<li>Tax returns not filed by the meeting of creditors, or a refund the plan required that was spent.</li>
<li>Post-filing mortgage or car payments missed, giving the lender grounds to lift the stay.</li>
<li>New debt taken without approval, or a mid-plan sale of property without court permission.</li>
</ul>
<p>A dismissed case leaves the debtor where they started, minus the payments made, and with the arrears the plan was curing now larger. Many dismissed cases are refiled; the second case gets a shorter automatic stay unless the court extends it. The <a href="/chapter-13/">Chapter 13 statistics page</a> shows outcomes by district.</p>

<h2 id="costs">Costs</h2>
<ul>
<li><strong>Filing fee:</strong> $313, in installments if needed, never waived.</li>
<li><strong>Trustee commission:</strong> a percentage of every plan payment, set by the United States Trustee for the district and capped at ten percent under 28 U.S.C. § 586(e). It funds the trustee's office and comes out of what creditors receive.</li>
<li><strong>Attorney fees:</strong> commonly paid through the plan in monthly installments rather than up front. Many districts set a presumptively reasonable flat fee by local rule; a fee above it requires an itemized application. Every payment to counsel must be disclosed to the court, and the <a href="/fee-guide/">fee guide</a> explains how fee applications and reviews work.</li>
<li><strong>Courses:</strong> the counseling and education courses each carry a small provider fee, waivable for those who cannot pay.</li>
</ul>

<h2 id="forms">The forms</h2>
<ul>
<li><strong>Form 101</strong>, the petition, with Form 121 for the Social Security number.</li>
<li><strong>Form 106</strong> summary and Schedules A/B through J, and <strong>Form 107</strong>, the statement of financial affairs, as in Chapter 7.</li>
<li><strong>Forms 122C-1 and 122C-2</strong>, the commitment period and disposable income calculation.</li>
<li><strong>Form 113</strong>, the national Chapter 13 plan, or the district's local plan form where one is required.</li>
<li><strong>Tax returns</strong> for the four years before filing, provided to the trustee, and the most recent return to any creditor who asks.</li>
<li><strong>The creditor matrix</strong>, the counseling certificate, and <strong>Form 423</strong> before discharge.</li>
<li><strong>Local forms</strong>, which in Chapter 13 often include a payroll deduction order and a trustee questionnaire. The <a href="/forms/">forms reference</a> explains each Official Form.</li>
</ul>

<h2 id="mistakes">Mistakes that end cases</h2>
<ul>
<li>Filing before the last four years of tax returns are in.</li>
<li>Missing the first payment, which is due within 30 days of filing whether or not the plan is confirmed yet.</li>
<li>A Schedule J budget written to make the plan confirm rather than to match real spending.</li>
<li>Letting the ongoing mortgage or car payment slip while the plan cures the old arrears.</li>
<li>Waiting until payments are already missed to tell anyone that income changed.</li>
<li>Spending a tax refund or a bonus the plan committed to creditors.</li>
</ul>
<div class="callout"><strong>This page is education, not advice.</strong> It describes how the Code and Rules work in general. Whether Chapter 13 fits a particular situation, and what a plan should say, depends on facts this page cannot see. A consultation with a bankruptcy attorney admitted in your district, or a legal aid office, is the place to apply it to your case.</div>

<h2>Related resources</h2><div class="link-grid">
<a class="link-card" href="/chapter-7-guide/"><div class="label">Guide</div><h4>Chapter 7, step by step</h4><p>The liquidation chapter: who qualifies, the process, what you keep.</p></a>
<a class="link-card" href="/chapter-7-vs-13/"><div class="label">Guide</div><h4>Chapter 7 vs Chapter 13</h4><p>Which chapter fits: eligibility, timing, what you keep.</p></a>
<a class="link-card" href="/means-test-deep-dives/form-122c-chapter-13/"><div class="label">Deep dive</div><h4>Form 122C</h4><p>Commitment period and disposable income, line by line.</p></a>
<a class="link-card" href="/screener/"><div class="label">Tool</div><h4>Discharge screener</h4><p>Check the four-year and two-year bars before filing.</p></a>
<a class="link-card" href="/automatic-stay/"><div class="label">Guide</div><h4>The automatic stay</h4><p>What stops on filing, and what does not.</p></a>
<a class="link-card" href="/chapter-13/"><div class="label">Data</div><h4>Chapter 13 outcomes by district</h4><p>Dismissal and discharge rates from the FJC data.</p></a>
<a class="link-card" href="/fee-guide/"><div class="label">Guide</div><h4>Fees and fee review</h4><p>Filing fees, attorney fees, and how the court reviews them.</p></a>
<a class="link-card" href="/forms/"><div class="label">Reference</div><h4>Bankruptcy forms</h4><p>What each Official Form asks for.</p></a>
</div>
"""

# ------------------------------------------------------------------ builder
# 9/22/26: the live pages carry two trust signals added by hand after this generator last ran
# (commit 12d22e0460). Rebuilding without them SILENTLY STRIPS them from the deployed page -- it
# happened twice on 9/22 and was caught only by diffing the output against the live file. Anything
# added to a built page by hand belongs here too, or the next rebuild deletes it.
FIND_CASE_LINK = ('<p><a href="/find-bankruptcy-case/"><strong>How to look up a bankruptcy case for free</strong></a> '
                  "&mdash; PACER, the fee waiver, RECAP, CourtListener, and the court's free phone line, and what "
                  'each one shows.</p>\n')


def reviewed_stamp(updated):
    return (f'<div class="datastamp reviewed">Written and maintained by Open Bankruptcy Project staff. '
            f'Last updated <time datetime="{updated}">{updated}</time>. '
            f'<a href="/editorial-policy.html">Editorial policy</a>.</div>')


def faq_html(faq, lead_html=""):
    out = [f'<section class="faq">{lead_html}<h2>Frequently asked questions</h2>']
    for q, a in faq:
        out.append(f"<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>")
    out.append("</section>")
    return "".join(out)

def faq_schema(faq):
    return json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                       "mainEntity": [{"@type": "Question", "name": q,
                                       "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
                      ensure_ascii=False)

RECORDS = {
    "slug": "find-bankruptcy-case",
    "title": "How to Look Up a Bankruptcy Case for Free [2026]",
    "h1": "How to Look Up a Bankruptcy Case",
    "label": "Public Records Guide",
    "description": (
        "How to find a bankruptcy case and read its docket without paying: PACER and its fee waiver, the free "
        "RECAP archive, CourtListener, the court's own phone system, and what each source does and does not "
        "show. Free 501(c)(3) guide, not legal advice."
    ),
    "lede": (
        "Bankruptcy filings are public records. Anyone can look up a case, read the docket, and in many "
        "instances download the documents, and a large share of that can be done for nothing. The catch is "
        "that no single free source is complete: each covers a different slice of the record. This page "
        "explains what each source holds, what it costs, and the order to try them in."
    ),
    "updated": "2026-09-18",
    "faq": [
        ("Are bankruptcy filings public?",
         "Yes. Bankruptcy cases are filed in federal court and the docket is a public record under 11 U.S.C. "
         "section 107(a), which provides that papers filed in a case are public records open to examination. "
         "A court may seal trade secrets, scandalous matter, or information that would create an undue risk of "
         "identity theft under section 107(b) and (c), and Bankruptcy Rule 9037 requires personal identifiers "
         "such as full Social Security numbers, birth dates, and minors' names to be redacted in public filings."),
        ("Can I look up a bankruptcy case for free?",
         "Partly. Searching whether a case exists and reading its docket costs money on PACER, the courts' own "
         "system, but PACER waives the bill for any quarter in which the account owes 30 dollars or less, so "
         "light users typically pay nothing. Documents that somebody has already purchased and contributed to "
         "the RECAP archive are free to read on CourtListener, with no account at all."),
        ("What does PACER cost?",
         "Ten cents per page, with a three-dollar cap per document, and search results are billed by the page of "
         "results. Fees are waived automatically for any quarter in which the total is 30 dollars or less. "
         "Audio recordings are 2.40 dollars each. Courts can also grant a fee exemption on application for "
         "reasons such as indigence or academic research, and that exemption is granted court by court."),
        ("How do I find a case if I do not know the case number?",
         "Use the PACER Case Locator, which searches every federal court at once by party name, or check "
         "CourtListener, which indexes millions of dockets and can be searched free by debtor name. Names are "
         "recorded exactly as filed, so try spelling variants, and remember that a business may be listed under "
         "a legal name that differs from the name on its sign."),
        ("What is RECAP and how is it free?",
         "RECAP is a free archive of federal court records run by the nonprofit Free Law Project. When someone "
         "using the RECAP browser extension buys a document on PACER, a copy is contributed to the archive, so "
         "the next person can read it for nothing on CourtListener. Coverage is therefore uneven: a document is "
         "in RECAP because somebody bought it once. Its absence means nobody did, not that it does not exist."),
        ("Can I get case documents without a computer?",
         "Yes. Every bankruptcy court runs a free automated phone line, the Multi-Court Voice Case Information "
         "System, that reads basic case information aloud, and the clerk's office will look up a case at the "
         "public terminal in the courthouse, where viewing is free. Printing at the courthouse is charged per page."),
    ],
}


def records_main():
    return """
<h2 id="what-is-public">What is public, and what is not</h2>
<p>A bankruptcy case is a federal court case, and its papers are public records. Section 107(a) of the Bankruptcy Code states the rule directly: papers filed in a case under the Code are public records open to examination by an entity at reasonable times without charge. That covers the petition, the schedules of assets and debts, the statement of financial affairs, the list of creditors, every motion and order, and the docket that lists them all in order.</p>
<p>Three limits apply. Under section 107(b) the court may seal a trade secret or confidential research, or matter that is scandalous or defamatory. Under section 107(c) the court may protect information that would create an undue risk of identity theft or other unlawful injury. And Bankruptcy Rule 9037 requires that filings show only the last four digits of a Social Security number, only the year of a birth date, only the initials of a minor, and only the last four digits of a financial account number. What you will see, then, is the full substance of a case with a narrow band of personal identifiers stripped out.</p>
<div class="callout"><strong>A docket is not the documents.</strong> The docket is the numbered index of what was filed and when. Reading it is often enough to answer a question. Downloading the underlying document is a separate step, and a separate charge on PACER.</div>

<h2 id="pacer">PACER, the courts' own system</h2>
<p>PACER, Public Access to Court Electronic Records, is the official source. It holds every federal bankruptcy, district, and appellate case, and it is the only source guaranteed to be complete and current. Registration is free and requires a name, address, and email; a credit card is requested to verify identity but is not charged unless fees accrue.</p>
<p>Charges are ten cents per page, with a cap of three dollars on any single document, which works out to thirty pages. Search result screens are billed the same way, by the page of results. Audio recordings cost 2.40 dollars each. The figure that matters most to an occasional user is the waiver: <strong>if an account accrues 30 dollars or less in a quarter, the fees are waived automatically</strong>. Someone checking a handful of cases will typically never pay.</p>
<p>Two other reductions exist. Courts grant fee exemptions on written application for reasons such as indigence, academic research, or nonprofit work, and that decision is made court by court rather than centrally. And some documents are free to all: a case's docket is free to the debtor and to counsel of record in that case, and each court posts certain opinions free of charge.</p>
<h3 id="case-locator">Finding a case when you do not know the number</h3>
<p>The PACER Case Locator searches every federal court at once. Search by party name, and narrow by court, case type, and date filed. Names are indexed exactly as they were filed, so a middle initial, a suffix, or a former name can decide whether a case appears. Businesses are listed by legal name, which is often not the name on the storefront.</p>

<h2 id="free-sources">The free sources</h2>
<h3 id="recap">RECAP and CourtListener</h3>
<p>The Free Law Project, a nonprofit, runs CourtListener and the RECAP archive. When a person using the RECAP browser extension buys a document on PACER, a copy is donated to the archive. The result is millions of dockets and documents readable free, with no account and no fee.</p>
<p>The strength of this source is that it is genuinely free and permanently available. Its weakness is coverage. A document sits in RECAP because somebody once paid for it; absence from the archive says nothing about whether the document exists. For a heavily litigated case the archive is often close to complete, and for a quiet consumer case it may hold only the docket. Install the extension if you use PACER at all: it shows you when a free copy already exists, and contributes what you buy.</p>
<h3 id="phone">The court's phone line and public terminals</h3>
<p>Every bankruptcy court runs a free automated line, the Multi-Court Voice Case Information System, that reads case information aloud: whether a case exists, the chapter, the filing date, the trustee, the judge, and the meeting of creditors date. It answers the common questions without a computer.</p>
<p>Each courthouse also has a public terminal in the clerk's office where viewing records is free. Printing there is charged per page. Clerk's office staff will look up a case and tell you what the docket says; they cannot give legal advice or tell you what a filing means for you.</p>
<h3 id="notices">If you are a creditor or a party</h3>
<p>Parties on a case's mailing list receive court notices by mail at no cost, and can switch to free email delivery through the Bankruptcy Noticing Center. A debtor in a participating court can enroll in Debtor Electronic Bankruptcy Noticing and receive court-generated notices by email the day they issue. Both are free, and both carry court notices only, not the filings of other parties.</p>

<h2 id="which-source">Which source answers which question</h2>
<table class="obp-table">
<thead><tr><th>Question</th><th>Best source</th><th>Cost</th></tr></thead>
<tbody>
<tr><td>Did this person or business file?</td><td>PACER Case Locator, or CourtListener search</td><td>Ten cents per results page; free on CourtListener</td></tr>
<tr><td>What is the case number, chapter, and filing date?</td><td>Court's automated phone line</td><td>Free</td></tr>
<tr><td>What has happened in the case?</td><td>PACER docket, or the docket on CourtListener</td><td>Ten cents per page; free where archived</td></tr>
<tr><td>What does a specific filing say?</td><td>RECAP first, then PACER</td><td>Free if archived, otherwise up to three dollars</td></tr>
<tr><td>Who is the trustee, and when is the creditors' meeting?</td><td>Phone line or docket</td><td>Free</td></tr>
<tr><td>Was a debt discharged?</td><td>The discharge order on the docket</td><td>Ten cents per page, usually one or two pages</td></tr>
</tbody>
</table>

<h2 id="reading">Reading what you find</h2>
<p>A docket sheet opens with the case caption, the case number, the chapter, the assigned judge, the trustee, the filing date, and the debtor's attorney if there is one. Below that, numbered entries run in order, each with a date and a short description written by the clerk. The numbers are the document numbers; a citation like ECF No. 42 refers to that entry.</p>
<p>A handful of entries carry most of the meaning. The petition is entry one. The schedules list assets, debts, income, and expenses. The meeting of creditors notice sets the date the debtor answers questions under oath. A discharge order ends the debtor's personal liability for the debts it covers. A dismissal order ends the case without a discharge, which is a different outcome entirely; our page on <a href="/screener/">what bankruptcy discharges</a> explains the difference. A case being closed is not the same as a debt being discharged.</p>
<div class="callout"><strong>Scanned paper is not searchable.</strong> A document filed on paper is scanned as an image, so its text cannot be searched or copied. The clerk's one-line docket description is the only searchable trace of it.</div>

<h2 id="limits">What none of these sources will tell you</h2>
<p>Public records show what was filed, not what it means. A docket does not say whether a debt of yours was covered, whether a claim was paid, or whether a filing was accurate. It does not show what was said at a hearing unless a transcript was ordered and filed. It does not show settlement talks, which happen off the record. And a case appearing in a search is not a judgment about anyone: filing is a legal right that millions of people and businesses exercise.</p>
<p>Open Bankruptcy Project publishes this guide as public information. It is not legal advice, and we cannot tell you what a particular filing means for your situation. For that, a bankruptcy attorney in the district where the case is pending is the right stop.</p>

<h2 id="next">Next steps</h2>
<ul>
<li>Trying to work out whether bankruptcy would reach your debts: the <a href="/screener/">discharge screener</a>.</li>
<li>Wondering which chapter applies: <a href="/chapter-7-guide/">Chapter 7</a>, <a href="/chapter-13-guide/">Chapter 13</a>, or the <a href="/chapter-7-vs-13/">comparison</a>.</li>
<li>Filing without a lawyer: the <a href="/pro-se/">pro se guide</a> and the <a href="/forms/">forms index</a>.</li>
<li>More on the free archive: <a href="/recap.html">RECAP and CourtListener</a>.</li>
</ul>
"""


def build(page, main_html):
    t = open(TEMPLATE, encoding="utf-8").read()
    url = f"{SITE}/{page['slug']}/"
    esc = html.escape
    t = re.sub(r"<title>.*?</title>", f"<title>{esc(page['title'])}</title>", t, count=1, flags=re.S)
    t = re.sub(r'<meta name="description" content="[^"]*"', f'<meta name="description" content="{esc(page["description"])}"', t, count=1)
    t = re.sub(r'<link rel="canonical" href="[^"]*"', f'<link rel="canonical" href="{url}"', t, count=1)
    t = re.sub(r'<meta property="og:title" content="[^"]*"', f'<meta property="og:title" content="{esc(page["title"])} | Open Bankruptcy Project"', t, count=1)
    t = re.sub(r'<meta property="og:description" content="[^"]*"', f'<meta property="og:description" content="{esc(page["description"])}"', t, count=1)
    t = re.sub(r'<meta property="og:url" content="[^"]*"', f'<meta property="og:url" content="{url}"', t, count=1)
    article = json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": page["h1"],
                          "description": page["description"], "url": url, "dateModified": page["updated"],
                          "author": {"@type": "Organization", "name": "Open Bankruptcy Project"},
                          "publisher": {"@type": "Organization", "name": "Open Bankruptcy Project", "url": SITE}},
                         ensure_ascii=False)
    crumbs = json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
        {"@type": "ListItem", "position": 2, "name": page["h1"], "item": url}]}, ensure_ascii=False)
    lds = re.findall(r'<script type="application/ld\+json">\{"@context": "https://schema\.org", "@type": "(Article|BreadcrumbList|FAQPage)".*?</script>', t, flags=re.S)
    assert lds == ["Article", "BreadcrumbList", "FAQPage"], lds
    t = re.sub(r'<script type="application/ld\+json">\{"@context": "https://schema\.org", "@type": "Article".*?</script>',
               f'<script type="application/ld+json">{article}</script>', t, count=1, flags=re.S)
    t = re.sub(r'<script type="application/ld\+json">\{"@context": "https://schema\.org", "@type": "BreadcrumbList".*?</script>',
               f'<script type="application/ld+json">{crumbs}</script>', t, count=1, flags=re.S)
    t = re.sub(r'<script type="application/ld\+json">\{"@context": "https://schema\.org", "@type": "FAQPage".*?</script>',
               f'<script type="application/ld+json">{faq_schema(page["faq"])}</script>', t, count=1, flags=re.S)
    hero = (f'<section class="hero"><div class="container">\n<div class="label">{esc(page["label"])}</div>\n'
            f'<h1>{esc(page["h1"])}</h1>\n<p class="lede">{esc(page["lede"])}</p>\n'
            f'<div class="datastamp">Updated <time datetime="{page["updated"]}">{page["updated"]}</time>. '
            f'Statutory citations are to Title 11 of the United States Code unless noted. See <a href="/research/methodology/">methodology &amp; sources</a>.</div>\n'
            f'{reviewed_stamp(page["updated"])}\n</div></section>')
    t = re.sub(r'<section class="hero">.*?</section>', hero, t, count=1, flags=re.S)
    crumb_html = f'<div class="breadcrumb"><a href="/">Home</a><span class="sep">/</span>{esc(page["h1"])}</div>'
    lead = FIND_CASE_LINK if page["slug"] != "find-bankruptcy-case" else ""
    body = crumb_html + main_html + faq_html(page["faq"], lead)
    t = re.sub(r'<div class="breadcrumb">.*?(?=<section class="obp-footer">)', body + "\n", t, count=1, flags=re.S)
    return t

def main():
    for page, body in ((CH7, ch7_main()), (CH13, ch13_main()), (RECORDS, records_main())):
        out = build(page, body)
        if "--check" in sys.argv:
            sys.stdout.write(out[:1500]); continue
        d = os.path.join(ROOT, page["slug"]); os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "index.html")
        open(p, "w", encoding="utf-8", newline="\n").write(out)
        words = len(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", out, flags=re.S)).split())
        print("wrote", p, len(out), "bytes,", words, "words")

if __name__ == "__main__":
    main()
