# Wardrobe Portability — Future Interview / Survey Script v1

Status: internal design only. Do not send or publish without the applicable external-action authorization.

## Screening
1. Do you currently use, or have you seriously considered using, a digital wardrobe/closet app? `YES / NO`
2. Roughly how many wearable items do you own? `<25 / 25-49 / 50-99 / 100-199 / 200+`
3. Are you primarily a professional/high-volume clothing reseller? `YES / NO`

Primary qualified segment: Q1=YES, Q2>=50, Q3=NO.

## Problem-first questions — ask before showing any proposition
1. Tell me about the last time you tried to organize or digitize your wardrobe. What did you actually do?
2. What took the most time or caused the most frustration?
3. If you already use a closet app, what would happen to your wardrobe record if that app disappeared tomorrow?
4. Have you ever wanted to switch closet apps but avoided it because you would need to start over? What happened?
5. How do you currently notice clothes you rarely wear?
6. Think of the last item you meant to sell or donate. What stopped or delayed you?
7. Which problem matters most today: setup time, inaccurate item data, daily upkeep, backup/data loss, switching apps, outfit ideas, deciding what to sell/donate, or something else?

## Concept comparison — randomize order A/B/C/D
Show the frozen text from `landing_variants.md` without changing copy during one test version.

For each concept ask:
1. How useful would this be to you? `0-10`
2. How believable is the promise? `0-10`
3. What, if anything, would make you try it?
4. What would stop you?
5. Does this solve a problem you already have, or just sound interesting?

After all concepts:
- Which ONE would you try first?
- Which ONE would you be most disappointed to lose after using for a year?
- Which ONE feels meaningfully different from tools you already know?

## Monetization proxy — stated preference only, never revenue proof
If the selected concept worked reliably, which payment model feels least objectionable?
- one-time migration fee
- monthly/annual fee for portable backup + insights
- transaction-linked fee only when resale assistance creates value
- none / would not pay

Optional price-band question must be reported as stated willingness only, not actual willingness to pay.

## Evidence coding
Code each qualified response with:
- exact_problem_confirmation: YES/NO + verbatim summary
- current_workaround
- switching_or_backup_pain: NONE/LOW/MEDIUM/HIGH
- underused_item_recovery_pain: NONE/LOW/MEDIUM/HIGH
- preferred_variant: A/B/C/D
- generic_ai_primary_motivation: YES/NO
- monetization_model_preference
- contradiction_or_disconfirming_evidence

## Safety / privacy
Do not solicit minors, payment credentials, home addresses, financial account data, or sensitive personal data. Use the minimum information needed to test the product hypothesis.
