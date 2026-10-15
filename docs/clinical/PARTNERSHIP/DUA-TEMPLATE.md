# Bilateral Data Use Agreement (DUA) Template (docs/clinical/PARTNERSHIP/DUA-TEMPLATE.md)

**BETWEEN:**  
**1. [PARTNER HOSPITAL NAME]**, an academic healthcare institution located at [Hospital Address, City, State, Nigeria] (hereinafter referred to as the **"Data Provider"** or **"Disclosing Party"**), represented by its Chief Medical Director / Director of Clinical Research;  
**AND:**  
**2. THE VIGIL ONCOLOGY RESEARCH INITIATIVE**, a precision oncology software and clinical AI research initiative (`gasthecreator/vigil`) represented by the Principal Investigator [Gideon Sanni / Authorized Representative] (hereinafter referred to as the **"Data Recipient"**).

---

## 1. Preamble & Regulatory Authority

WHEREAS the Data Provider maintains clinical records, laboratory datasets, and follow-up trajectories of breast cancer patients treated within its oncology services;  
WHEREAS the Data Recipient has developed the **Vigil Precision Oncology Platform**, an open-source, non-commercial clinical decision-support engine designed to assist oncologists by detecting longitudinal biomarker anomalies;  
WHEREAS both Parties desire to collaborate on a retrospective chart-review research study entitled *"Retrospective Longitudinal Biomarker Surveillance for Early Detection of Metastatic Breast Cancer Recurrence in Nigerian Tertiary Oncology Centers"* (the **"Study"**);  
WHEREAS both Parties are committed to the highest standards of patient privacy, ethical research, and legal compliance under the **Nigeria Data Protection Act 2023 (NDPA)** [E14], the **National Code for Health Research Ethics (NCHRE/NHREC)**, and the **Declaration of Helsinki**;

NOW, THEREFORE, the Parties agree to the following terms and conditions:

---

## 2. Definitions

1. **"De-Identified Data":** Health records from which all eighteen (18) direct personal identifiers (including patient names, hospital numbers, National Identification Numbers [NIN], phone numbers, email addresses, exact dates of birth, and home addresses) have been irreversibly removed, and all calendar dates have been converted into relative integer day offsets preserving inter-visit intervals.
2. **"Permitted Purpose":** The execution of statistical validation, machine learning model calibration, lead-time evaluation, and the Missed-Signal Audit (M10) strictly as described in the approved Study Protocol.
3. **"Pseudonymization Key":** The master linkage table mapping original hospital patient identifiers to research study UUIDs (`patient_id`), maintained exclusively behind the Data Provider's secure institutional firewall.

---

## 3. Scope of Data Transfer & Ownership

1. **Minimal Dataset:** The Data Provider agrees to disclose solely the minimal de-identified dataset specified in `DATA-DICTIONARY.md`, comprising baseline tumor characteristics, serial laboratory test results, and confirmed metastatic recurrence outcomes.
2. **Retention of Ownership:** The Data Provider retains all proprietary rights, clinical title, and institutional ownership of the raw medical record data. No commercial transfer of underlying clinical records is effected by this Agreement.
3. **Open Research & Algorithmic Weights:** All validated mathematical models, calibration tables, and open-source software libraries created during the study shall be made publicly accessible under permissive academic licenses (Apache 2.0 / MIT) for global clinical benefit, with institutional co-authorship properly credited.

---

## 4. Recipient Obligations & Data Protection Safeguards

The Data Recipient explicitly warrants and covenants:
1. **Ban on Re-Identification:** Recipient shall **not** attempt, facilitate, or permit any re-identification of individual patients, nor link the de-identified dataset to any external registry, public record, or demographic database.
2. **Access Restrictions:** Access to the de-identified dataset shall be strictly restricted to named research investigators with verified research credentials who have executed written non-disclosure and data protection commitments.
3. **Cryptographic Storage & Security:** All shared data must be encrypted in transit (TLS 1.3 / SSH) and encrypted at rest using AES-256 encryption. Datasets must reside on encrypted storage volumes with multi-factor authentication (MFA) and audited access logs.
4. **No Third-Party Sharing:** The Recipient shall not sell, license, lease, assign, or distribute the dataset, in whole or in part, to any commercial third party, insurance carrier, pharmaceutical entity, or external vendor.
5. **Breach Notification:** In the event of any unauthorized access, loss, or security compromise involving the dataset, the Recipient shall formally notify the Data Provider within **seventy-two (72) hours** in accordance with NDPA 2023 statutory guidelines.

---

## 5. Ethical Oversight & Institutional Approval

1. **IRB / HREC Clearance:** Transmission of data is strictly contingent upon formal ethical clearance and protocol approval by the Data Provider’s Institutional Health Research Ethics Committee (HREC), with a valid approval certificate appended to this Agreement.
2. **Consent Waiver Compliance:** The Parties confirm that data processing proceeds under an approved HREC waiver of individual informed consent, grounded in retrospective secondary analysis of anonymized records with minimal risk.

---

## 6. Academic Dissemination, Authorship, and Value Delivery

1. **Collaborative Authorship:** Any peer-reviewed scientific publications, conference abstracts, or whitepapers arising from the Study shall include the Data Provider’s clinical and chemical pathology investigators as co-authors, conforming to International Committee of Medical Journal Editors (ICMJE) criteria.
2. **Missed-Signal Audit Delivery:** The Data Recipient shall deliver to the Data Provider an executive institutional report detailing the **Missed-Signal Audit (M10)**, providing hospital leadership with actionable quality-improvement insights into diagnostic lead time, laboratory reference intervals, and follow-up retention.

---

## 7. Term and Termination

1. **Term:** This Agreement becomes effective on the date of final signature by both Parties and shall remain in effect for a period of **three (3) years**, renewable upon mutual written consent.
2. **Data Disposition on Termination:** Upon completion of the Study or termination of this Agreement, the Data Recipient shall, at the direction of the Data Provider, securely purge, sanitize, or destroy all local copies of the de-identified dataset using DoD 5220.22-M compliant data wiping methods, retaining only cryptographic checksum manifests required for academic reproducibility.

---

## 8. Signatures and Execution

IN WITNESS WHEREOF, the authorized representatives of the Parties have executed this Data Use Agreement as of the date written below:

**FOR THE DATA PROVIDER:**  
Signature: __________________________________  
Name: _____________________________________  
Title: Chief Medical Director / HREC Chair  
Institution: [Partner Teaching Hospital]  
Date: _____________________________________  

**FOR THE DATA RECIPIENT:**  
Signature: __________________________________  
Name: Gideon Sanni  
Title: Lead Architect & Principal Investigator, Vigil Initiative  
Date: _____________________________________  
