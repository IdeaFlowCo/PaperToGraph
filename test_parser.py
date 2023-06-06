import parser

SAMPLE_LONG_INPUT = """
Abstract
Wilms tumour (WT) is a childhood embryonal tumour that is paradigmatic of the intersection between disrupted organogenesis and tumorigenesis. Many WT genes play a critical (non-redundant) role in early nephrogenesis. Improving patient outcomes requires advances in understanding and targeting of the multiple genes and cellular control pathways now identified as active in WT development. Decades of clinical and basic research have helped to gradually optimize clinical care. Curative therapy is achievable in 90% of affected children, even those with disseminated disease, yet survival disparities within and between countries exist and deserve commitment to change. Updated epidemiological studies have also provided novel insights into global incidence variations. Introduction of biology-driven approaches to risk stratification and new drug development has been slower in WT than in other childhood tumours. Current prognostic classification for children with WT is grounded in clinical and pathological findings and in dedicated protocols on molecular alterations. Treatment includes conventional cytotoxic chemotherapy and surgery, and radiation therapy in some cases. Advanced imaging to capture tumour composition, optimizing irradiation techniques to reduce target volumes, and evaluation of newer surgical procedures are key areas for future research.


Introduction
Wilms tumour (WT) is the most common renal tumour of infants and young children1,2. WT is intimately linked to early nephrogenesis, which it resembles morphologically3 and transcriptionally4,5. WT may occur sporadically or in the context of bilateral tumours, multifocal disease and specified genetic predisposition syndromes that frequently include either genitourinary malformation or overgrowth3. Beyond genetic predisposition, external causative factors for WT are not yet defined. The molecular drivers frequently involve blockade of genetic pathways that guide normal embryogenesis of the genitourinary tract but are not restricted to these. Indeed, the cancer genes that underpin WT are diverse and surprisingly involve ~40 genes.

The implementation of international co-operative group trials and studies across North America, Australia, New Zealand, Europe and Brazil has contributed significantly to improving outcomes6,7,8. Two international multidisciplinary cooperative consortia — the Children’s Oncology Group (COG) Renal Tumour Committee, previously known as the National Wilms Tumour Study Group (NWTSG), and the International Society of Paediatric Oncology (SIOP) Renal Tumour Study Group (RTSG) — have conducted large multicentre studies since 1969 and 1971, respectively, which have defined the current diagnostic and therapeutic approach to patients with WT (Fig. 1). These groups continue research to optimize disease and patient risk classification and treatment strategies9,10,11.

In the COG, WTs are treated with primary resection (if possible), followed by risk-adapted adjuvant therapy, whereas in the context of SIOP cooperation, neoadjuvant chemotherapy followed by resection and adjuvant therapy is the preferred treatment approach. Regardless of the initial approach, the overall survival of children with WT is remarkable with rates of >90%. Such satisfying survival rates have been achieved at the same time as fine-tuning treatment by adopting well-studied prognostic factors, leading to a two-drug regimen (vincristine and actinomycin D) prescribed in nearly two-thirds of affected children7,10. Notably, striking survival disparities still exist within countries12 and between different parts of the world, which remain to be addressed13,14. However, 20% of patients relapse after first-line therapy and up to 25% of survivors report severe late morbidity of treatment15,16. Addressing the long-term effect of radical nephrectomy on renal function and cardiovascular function will probably drive more attention on expanding the role of nephron-sparing surgery (NSS)17.

Molecular studies are expanding the landscape of cancer genes implicated in WT beyond exclusive roles in nephrogenesis3. The use of next-generation integrative genomic and epigenetic tumour analysis has provided important insights into WT biology. Comparisons of the regulation of progenitor cells in the fetal kidney with the disrupted regulation of their counterparts in WT should provide further insights into tumour formation18. Targeting WT tumour genes with a non-redundant role in nephrogenesis and targeting the fetal renal transcriptome warrant further therapeutic exploration. Interventions that could prevent the evolution of nephrogenic rests to malignant WT could transform therapy in this setting and could even lead to preventive strategies in children known to be at high risk of developing WT.

This Primer describes our current understanding of WT epidemiology, disease susceptibility and mechanisms, as well as elements of clinical care, including diagnostics and risk-stratified treatment of newly diagnosed disease. In addition, we also outline potential opportunities to further translate new biological insights into improved clinical outcomes. We discuss how the widespread implementation of standardized diagnostics and treatments for as many children as possible, regardless of socioeconomic status or geographical region of origin, may propel further clinical advances.


Epidemiology
Global disease burden

Malignant renal tumours comprise 5% of all cancers occurring before the age of 15 years19. Every year ~14,000 children (0–14 years of age) are diagnosed worldwide, and 5,000 children die from these diseases, with regional variation in mortality20 (Fig. 2). The incidence of childhood renal tumours is not associated with economic status, but mortality is higher in low-income areas than high-income areas (0.5 per million in high-income areas versus 7.5 per million in low-income areas).

WT is the most common renal tumour in children1 and studies have found variation in incidence between regions or ethnicities2,21 (Fig. 3). The annual incidence of WT in East Asia is lower than in North America or Europe (4.3 per million versus 8–9 per million)2. In the USA, children with African-American ancestry have the highest incidence (9.7 per million) whilst those with Asian-Pacific Islander ancestry have the lowest (3.7 per million)2. However, owing to the lack of population-based childhood cancer registries in resource-constrained regions, or because of the low quality of the data (that is, not all cancers are reported or not all children are reported), the estimation of global incidence has been difficult14,22,23. In addition, 50% of patients from areas with less resources have metastases at diagnosis24.

Up to 17% of WT occur as part of a recognizable malformation syndrome25, 10% of which are associated with known WT predisposition26 (Table 1). Overgrowth syndromes, in particular Beckwith–Wiedemann syndrome, carry ~5% risk of developing WT, ranging from 0.2% to 24% according to the underlying genetic cause27,28,29. Syndromes involving genitourinary anomalies combined with aniridia and variable intellectual disability, or with nephrotic syndrome, are associated with mutations of the gene WT1 on chromosome 11p13 and these patients have a greatly increased risk of developing WT3,30,31.

No temporal trends in the incidence of WT were observed within the period 1996–2010 (ref.2), suggesting that environmental factors play a marginal role in WT aetiology. Nevertheless, modifiable risk factors for WT are not well understood.
Influence of sex and age

WT is one of the few childhood cancers that is more common (~10%) in girls than in boys19. The age-specific incidence of WT peaks at 1 year of age in boys at 17.9 per million person-years. However, in girls, a similar peak remains almost constant at 1, 2 and 3 years of age, with the respective incidences of 17.8, 18.0 and 18.1 per million person-years (Fig. 4).
"""


print('*************')
print('Splitter info')
print('*************')
print()
print(f'Testing text splitting with hardcoded sample input with length: #{len(SAMPLE_LONG_INPUT)}')
split_input = parser.__split_to_size(SAMPLE_LONG_INPUT)
print(f'Sample input split into #{len(split_input)} different chunks.')
print('Length of each chunk:')
for chunk in split_input:
    print(len(chunk))

print('\n\n\n')

print('***************')
print('GPT prompt info')
print('***************')
print()
print('Prompt as will be sent in system message:')
print('\n-----')
print(parser.SYSTEM_MESSAGE_CONTENT)
print('-----')
