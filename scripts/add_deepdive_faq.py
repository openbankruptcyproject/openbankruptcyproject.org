"""Add a visible FAQ section + FAQPage schema to the four means-test deep dives (9/18/26).

Every answer below is drawn from the page's own text (headings and lead paragraphs read 9/18); no
claim is introduced that the page does not already make. Idempotent: skips a page that already
carries FAQPage schema.
"""
import html
import io
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DD = os.path.join(ROOT, "means-test-deep-dives")

FAQ = {
 "form-122a-1-income": [
  ("What is current monthly income on Form 122A-1?",
   "Current monthly income is the average monthly income the debtor received during the six-month period ending on the last day of the calendar month before the petition date, as defined in 11 U.S.C. section 101(10A). Form 122A-1 totals the receipts in each category over that period and divides by six."),
  ("Which six months count?",
   "The six full calendar months before the month in which the petition is filed. The filing month itself is excluded, so the look-back window shifts by a month depending on whether the case is filed on the last day of a month or the first day of the next."),
  ("What income is excluded from current monthly income?",
   "Section 101(10A)(B) excludes certain receipts regardless of amount, including benefits received under the Social Security Act, payments to victims of war crimes or terrorism, and certain veterans' disability and death-related benefits. The form captures these on a deduction line, but the substance is a statutory exclusion."),
  ("How does household size change the result?",
   "The state median comparison is made against a table indexed by state and household size. Two debtors with identical current monthly income can land on opposite sides of the median line because their household sizes place them on different rows of the table."),
  ("What documents will the trustee ask for?",
   "Standard requests are the six most recent pay statements for each wage earner, six months of bank statements showing deposits, and profit-and-loss statements for any self-employment income. The trustee uses them to test the figures entered on the form."),
  ("Who is exempt from the presumption of abuse regardless of income?",
   "Debtors whose debts are primarily non-consumer debts, certain disabled veterans, and reservists or National Guard members called to active duty file Form 122A-1Supp and are not subject to the presumption under section 707(b)(2), whatever their current monthly income."),
 ],
 "form-122a-2-deductions": [
  ("Who has to complete Form 122A-2?",
   "Only above-median debtors. Form 122A-1 routes a debtor whose annualized current monthly income exceeds the applicable state median to Form 122A-2, which subtracts the allowed deductions to determine whether a presumption of abuse arises."),
  ("What are the IRS National Standards?",
   "A single combined allowance for food, clothing and services, personal care, housekeeping supplies, and miscellaneous expenses. It is indexed by household size only and does not vary by where the debtor lives."),
  ("What are the IRS Local Standards?",
   "Allowances for housing and utilities and for transportation, the two largest expense categories for most households. They are specific to the county or metropolitan area, and the published tables vary substantially across the country."),
  ("Can I deduct an expense that is not on the list?",
   "Not under the Other Necessary Expenses family. That family is a closed enumeration: an expense that is not among its categories is not deductible there regardless of how necessary the debtor considers it. Additional expenses can be raised only as special circumstances under section 707(b)(2)(B)."),
  ("How are secured debt payments deducted?",
   "Section 707(b)(2)(A)(iii)(I) allows the average monthly payment on all secured debts, calculated as the total of the contractual payments scheduled to come due during the 60 months after the petition date, divided by 60."),
  ("What is the marital adjustment?",
   "For a married debtor filing individually, Form 122A-1 counts the non-filing spouse's income, and Form 122A-2 then allows a deduction for the portion of that income that is not contributed to the household's expenses."),
  ("When does the presumption of abuse arise?",
   "After all deductions are subtracted, the form multiplies monthly disposable income by 60 and compares the product to the thresholds in section 707(b)(2)(A)(i), which are adjusted every three years. If the product meets a threshold, the presumption arises and can be rebutted only by documented special circumstances."),
 ],
 "form-122c-chapter-13": [
  ("What is the applicable commitment period?",
   "Under section 1325(b)(4), a debtor whose annualized current monthly income is at or below the applicable state median has a three-year commitment period; a debtor above the median has a five-year period. Form 122C-1 performs the comparison."),
  ("Do below-median debtors complete Form 122C-2?",
   "No. A below-median Chapter 13 debtor does not use Form 122C-2 for the disposable-income calculation. What is reasonably necessary is determined under section 1325(b)(2) with the court's general discretion, informed by Schedules I and J."),
  ("How does Form 122C-1 differ from Form 122A-1?",
   "It mirrors it: the same six-month look-back and the same income categories. The difference is what the result does. In Chapter 7 the comparison drives a presumption of abuse; in Chapter 13 it sets the commitment period and decides whether Form 122C-2 applies."),
  ("What did Hamilton v. Lanning decide?",
   "In Hamilton v. Lanning, 560 U.S. 505 (2010), the Supreme Court held that projected disposable income under section 1325(b)(1)(B) permits a forward-looking adjustment where changes in the debtor's income or expenses are known or virtually certain at confirmation, rather than a purely mechanical multiplication of the look-back figure."),
  ("Are charitable contributions a reasonably necessary expense?",
   "Section 1325(b)(2) expressly treats charitable contributions of up to 15 percent of gross income as reasonably necessary, language added by the Religious Liberty and Charitable Donation Protection Act of 1998."),
  ("Who can object to a plan on disposable-income grounds?",
   "The trustee or any unsecured creditor, at confirmation. Over such an objection, a plan cannot be confirmed unless it pays unsecured claims in full or commits all of the debtor's projected disposable income for the applicable commitment period."),
 ],
 "presumed-abuse-rebuttal": [
  ("What counts as special circumstances under section 707(b)(2)(B)?",
   "The statute names two examples, a serious medical condition and a call or order to active duty in the Armed Forces, and the words \"such as\" make them illustrative rather than exhaustive. The circumstances must justify additional expenses or adjustments of current monthly income for which there is no reasonable alternative."),
  ("What must a debtor file to rebut the presumption?",
   "An itemized statement of each additional expense or income adjustment, with documentation, attested under oath, filed as part of Form 122A-2 or as a supplemental attachment. Under In re Pageau, 383 B.R. 221 (Bankr. D.N.H. 2008), the showing must identify each item, document it, and explain why there is no reasonable alternative."),
  ("Can a change in income be a special circumstance?",
   "Yes. Section 707(b)(2)(B)(i) permits adjustments of current monthly income, so a debtor whose six-month look-back captured income that has since terminated can present the change as a special circumstance with documentation."),
  ("What has been rejected as a special circumstance?",
   "The reported decisions consistently reject adjustments that reflect ordinary living expenses or voluntary financial choices rather than circumstances beyond the debtor's control. In re Egebjerg, 574 F.3d 1045 (9th Cir. 2009), held that monthly repayments of a 401(k) loan are not deductible as a special circumstance."),
  ("What is the section 707(b)(3) totality test?",
   "A backup inquiry. Even where the presumption does not arise or has been rebutted, the court may still find abuse under section 707(b)(3) if the petition was filed in bad faith or if the totality of the debtor's financial circumstances demonstrates abuse."),
  ("What are the options when Form 122A-2 triggers the presumption?",
   "Rebut it under section 707(b)(2)(B) with documented special circumstances, or convert to Chapter 13, where the same disposable-income figure funds a plan instead of barring relief. Which path fits depends on facts this page cannot see."),
 ],
}

STYLE = ('<style id="obp-faq-style">.obp-faq{margin:2rem 0}.obp-faq h2{font-size:1.35rem;margin:0 0 .75rem}'
         '.obp-faq details{border:1px solid #30363d;border-radius:8px;padding:.85rem 1.1rem;margin:0 0 .6rem;background:#161b22}'
         '.obp-faq summary{cursor:pointer;font-weight:600}.obp-faq details p{margin:.6rem 0 0;color:#c9d1d9}</style>')

def main():
    for slug, qa in FAQ.items():
        p = os.path.join(DD, slug, "index.html")
        s = io.open(p, encoding="utf-8").read()
        if "FAQPage" in s:
            print(slug, ": already has FAQPage"); continue
        schema = json.dumps({"@context": "https://schema.org", "@type": "FAQPage",
                             "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in qa]},
                            ensure_ascii=False)
        head_add = f'<script type="application/ld+json">{schema}</script>\n' + ("" if "obp-faq-style" in s else STYLE + "\n")
        s = s.replace("</head>", head_add + "</head>", 1)
        sec = ['<section class="obp-faq" id="faq"><h2>Frequently asked questions</h2>']
        for q, a in qa:
            sec.append(f"<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>")
        sec.append("</section>\n")
        block = "".join(sec)
        # insert before the cross-references section (the page's last content h2)
        m = re.search(r'<h2[^>]*>\s*Open Bankruptcy Project cross-references', s)
        if m:
            s = s[:m.start()] + block + s[m.start():]
        else:
            s = s.replace("</main>", block + "</main>", 1) if "</main>" in s else s.replace("<footer", block + "<footer", 1)
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        print(slug, ": FAQ added,", len(qa), "questions")

if __name__ == "__main__":
    main()
