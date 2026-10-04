>需补充group id、members、contact person信息
>需补充最后的provisional team信息（看要求好像是可以附到第二页）
MAIB7050 Group Project Proposal
Class: [MAIB7050]  |  Group ID: [______]  |  Members: []  |  Contact Person: [Name, Email]

1. **Direction and Provisional Title**
Primary direction:E. Risk Compliance and Escalation.
Provisional title: GuardKit Evidence — an evidence-grounded screening data product for suspicious payment messages in Hong Kong
2. **User, Decision and Action**
Intended user:Finance department staff at small and medium-sized enterprises
Business question or workflow:Front-line AP Staff (SME): Receive payment requests via SMS/WhatsApp (e.g., changed bank accounts) and decide whether to pay, hold, or verify.Back-line Fraud Analysts (Bank): Review escalated cases that require full evidence, not just automated scores. Output and Scope: Based on provided materials, this assessment supports rather than replaces human decision-making; it does not auto-block fraudulent content and requires secondary manual review.
3. **Data Sources**
Data Sources & Access Method: Official fraud alerts (e.g., HKMA, bank websites) and manually collected, bilingual team-annotated SMS messages (Traditional/Simplified Chinese, English).Data Types: Unstructured/semi-structured text and structured metadata.Initial Sample: 100+ SMS text samples and 20+ official evidence documents.Important limitations: Limited to recent Hong Kong fraud cases (regional/language constrained), unable to process image-based data, and lacks coverage for novel fraud techniques or real-time official updates.
4. **Course Connection**
Data management: Masking sensitive information in the corpus. From Business Need to Data Requirements：Used for designing the evidence layer, the corpus layer, and the structured layer. ER model and Relational schema：Concepts regarding table relationships and primary/foreign keys will be used to design the structures of tables such as those for organizations, evidence, and SMS messages.  
5. **Scope and Responsibilities**
This project focuses solely on predicting fraud based on textual content and presenting relevant evidence.This project does not automatically intercept text messages, nor can it identify fraudulent messages in the form of voice or images. Expected Credibility: Assessing fraud outcomes, reasons for suspicion, and official credibility.Main risks: Limited language coverage, scoring errors, and delayed evidence updates.
provisional team: