# Application draft: SEER Research Data (via SEER*Stat)

> **DRAFT-UNREVIEWED. NOT SUBMITTED.** The process (register in the SEER Data Request System with an e-mail address; acknowledge the SEER Research Data Use Agreement and the SEER Treatment Data Limitations; verify the e-mail; receive a SEER*Stat account; each person who will access the data submits a separate request) was read from https://seer.cancer.gov/data/access.html on 2026-10-18. Whatever the live form asks for overrides this draft. The "Research Plus" product needs an eRA Commons or HHS account and is not requested here.

## Applicant
Name: [OWNER] E-mail: [OWNER] Organisation: [OWNER] Intended use: research (not personal use, not commercial): [OWNER to confirm the classification the form offers]

## Purpose (for the form)
Population-level priors for a breast-cancer follow-up research platform: age at diagnosis, stage and receptor-subtype distributions, and metastatic-site-at-diagnosis frequencies (bone, liver, lung, brain) stratified by subtype and stage, used as an explicitly labelled prior (tier `T-P`) for the baseline-risk module.

## Data and variables
SEER Research Data, breast cancer cases: age at diagnosis, year of diagnosis, derived AJCC stage group, breast subtype (2010 onward), SEER combined metastases at diagnosis (bone, liver, lung, brain), survival months, vital-status recode. No identifiers are requested or used.

## What this data cannot do (stated to the reviewer)
SEER has no serial laboratory results, no surveillance visits and no recurrence dates (`docs/EVIDENCE.md`, E13, graded SECONDARY), and is a US population. It supplies priors, not validation, and nothing derived from it will be presented as evidence about Nigerian patients.

## Data management
Local encrypted storage; no redistribution; no linkage to other identifiable data; only aggregate tables (cells below 10 suppressed) leave the machine; acknowledgement of NCI SEER in any report that uses the data; the repository holds no SEER rows.

## Acknowledgement
[OWNER] acknowledges the SEER Research Data Use Agreement and SEER Treatment Data Limitations on the live form. Date: [OWNER]
