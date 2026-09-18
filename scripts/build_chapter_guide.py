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
<a class="link-card" href="/pro-se/"><div class="label">Guide</div><h4>Filing without a lawyer</h4><p>What the court expects from a self-represented filer.</p></a>
<a class="link-card" href="/forms/"><div class="label">Reference</div><h4>Bankruptcy forms</h4><p>What each Official Form asks for.</p></a>
<a class="link-card" href="/deadline-calculator/"><div class="label">Tool</div><h4>Deadline calculator</h4><p>Key dates from your petition date.</p></a>
</div>
"""

# ------------------------------------------------------------------ builder
def faq_html(faq):
    out = ['<section class="faq"><h2>Frequently asked questions</h2>']
    for q, a in faq:
        out.append(f"<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>")
    out.append("</section>")
    return "".join(out)

def faq_schema(faq):
    return json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                       "mainEntity": [{"@type": "Question", "name": q,
                                       "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]},
                      ensure_ascii=False)

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
            f'Statutory citations are to Title 11 of the United States Code unless noted. See <a href="/research/methodology/">methodology &amp; sources</a>.</div>\n</div></section>')
    t = re.sub(r'<section class="hero">.*?</section>', hero, t, count=1, flags=re.S)
    crumb_html = f'<div class="breadcrumb"><a href="/">Home</a><span class="sep">/</span>{esc(page["h1"])}</div>'
    body = crumb_html + main_html + faq_html(page["faq"])
    t = re.sub(r'<div class="breadcrumb">.*?(?=<section class="obp-footer">)', body + "\n", t, count=1, flags=re.S)
    return t

def main():
    out = build(CH7, ch7_main())
    if "--check" in sys.argv:
        sys.stdout.write(out[:3000]); return
    d = os.path.join(ROOT, CH7["slug"]); os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "index.html")
    open(p, "w", encoding="utf-8", newline="\n").write(out)
    words = len(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", out, flags=re.S)).split())
    print("wrote", p, len(out), "bytes,", words, "words")

if __name__ == "__main__":
    main()
