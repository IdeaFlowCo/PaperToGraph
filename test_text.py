import text



def test_split_to_size(input):
    print('*************')
    print('Splitter info')
    print('*************')
    print()
    print(f'Testing text splitting with hardcoded sample input with length: {len(input)}')
    print(f'is_text_oversized result: {text.is_text_oversized(input)}')
    split_input = text.split_to_size(input)
    print(f'Sample input split into {len(split_input)} different chunks.')
    print('Length of each chunk:')
    for chunk in split_input:
        print(len(chunk))



SAMPLE_LONG_INPUT = """
Published: 14 October 2021
Wilms tumour
Filippo Spreafico, Conrad V. Fernandez, Jesper Brok, Kayo Nakata, Gordan Vujanic, James I. Geller, Manfred Gessler, Mariana Maschietto, Sam Behjati, Angela Polanco, Vivian Paintsil, Sandra Luna-Fineman & Kathy Pritchard-Jones
Nature Reviews Disease Primers volume 7, Article number: 75 (2021) Cite this article

15k Accesses

34 Citations

56 Altmetric

Metricsdetails

Abstract
Wilms tumour (WT) is a childhood embryonal tumour that is paradigmatic of the intersection between disrupted organogenesis and tumorigenesis. Many WT genes play a critical (non-redundant) role in early nephrogenesis. Improving patient outcomes requires advances in understanding and targeting of the multiple genes and cellular control pathways now identified as active in WT development. Decades of clinical and basic research have helped to gradually optimize clinical care. Curative therapy is achievable in 90% of affected children, even those with disseminated disease, yet survival disparities within and between countries exist and deserve commitment to change. Updated epidemiological studies have also provided novel insights into global incidence variations. Introduction of biology-driven approaches to risk stratification and new drug development has been slower in WT than in other childhood tumours. Current prognostic classification for children with WT is grounded in clinical and pathological findings and in dedicated protocols on molecular alterations. Treatment includes conventional cytotoxic chemotherapy and surgery, and radiation therapy in some cases. Advanced imaging to capture tumour composition, optimizing irradiation techniques to reduce target volumes, and evaluation of newer surgical procedures are key areas for future research.

Introduction
Wilms tumour (WT) is the most common renal tumour of infants and young children1,2. WT is intimately linked to early nephrogenesis, which it resembles morphologically3 and transcriptionally4,5. WT may occur sporadically or in the context of bilateral tumours, multifocal disease and specified genetic predisposition syndromes that frequently include either genitourinary malformation or overgrowth3. Beyond genetic predisposition, external causative factors for WT are not yet defined. The molecular drivers frequently involve blockade of genetic pathways that guide normal embryogenesis of the genitourinary tract but are not restricted to these. Indeed, the cancer genes that underpin WT are diverse and surprisingly involve ~40 genes.

The implementation of international co-operative group trials and studies across North America, Australia, New Zealand, Europe and Brazil has contributed significantly to improving outcomes6,7,8. Two international multidisciplinary cooperative consortia — the Children’s Oncology Group (COG) Renal Tumour Committee, previously known as the National Wilms Tumour Study Group (NWTSG), and the International Society of Paediatric Oncology (SIOP) Renal Tumour Study Group (RTSG) — have conducted large multicentre studies since 1969 and 1971, respectively, which have defined the current diagnostic and therapeutic approach to patients with WT (Fig. 1). These groups continue research to optimize disease and patient risk classification and treatment strategies9,10,11.

Fig. 1: Timeline of key clinical advances that established the modern clinical management of children with Wilms tumour.
figure 1
1. The National Wilms Tumour Study group (NWTS), which was supplanted by the Children’s Oncology Group (COG) in 2002, and the International Society of Paediatric Oncology (SIOP) initiated organized protocols155,227,228,229. 2. Researchers started to collect data on the associations between Wilms tumour (WT)-specific therapies and late toxicity in survivors227. 3. In 1978, anaplastic morphology was shown to correlate with an increased mortality from WT98. 4. SIOP progressively recognized that histological subtypes after neoadjuvant chemotherapy were a prognostic factor122,160,228,230. 5. In 1990, SIOP established the Paediatric Oncology in Developing Countries (PODC) committee to promote paediatric oncology in poorly-resourced countries. 6. Researchers showed that lung radiotherapy could be avoided in subgroups of patients with metastases (good responders), setting the new standard231. 7. SIOP-9 trial (1987–1991) showed no benefit from prolonging pre-nephrectomy chemotherapy to 8 weeks with respect to stage distribution, the 4-week schedule becoming the standard for non-metastatic WT160. 8. Actinomycin D could be administered in a single dose rather than divided over 5 days, thereby reducing hospital visits for children and health-care delivery costs232,233. 9. Nephrectomy alone in children with very low-risk WT (defined as <24 months of age, with a stage I favourable histology tumour weighing <550 g) was shown to be a valid option, avoiding the risks of central line placement and chemotherapy136. 10. Risk stratification of WTs implemented with loss of heterozygosity (LOH) at chromosomes 1p and 16q as adverse prognostic markers39. 11. Current standard treatment for children with stage II and III intermediate-risk histology after preoperative chemotherapy omits doxorubicin (vincristine and actinomycin D)7. 12. In 2018, WHO launched the Global Initiative for Childhood Cancer, with the goal of improving outcome in children with cancer around the world, initially focusing on six common cancers including WT174.

Full size image
In the COG, WTs are treated with primary resection (if possible), followed by risk-adapted adjuvant therapy, whereas in the context of SIOP cooperation, neoadjuvant chemotherapy followed by resection and adjuvant therapy is the preferred treatment approach. Regardless of the initial approach, the overall survival of children with WT is remarkable with rates of >90%. Such satisfying survival rates have been achieved at the same time as fine-tuning treatment by adopting well-studied prognostic factors, leading to a two-drug regimen (vincristine and actinomycin D) prescribed in nearly two-thirds of affected children7,10. Notably, striking survival disparities still exist within countries12 and between different parts of the world, which remain to be addressed13,14. However, 20% of patients relapse after first-line therapy and up to 25% of survivors report severe late morbidity of treatment15,16. Addressing the long-term effect of radical nephrectomy on renal function and cardiovascular function will probably drive more attention on expanding the role of nephron-sparing surgery (NSS)17.

Molecular studies are expanding the landscape of cancer genes implicated in WT beyond exclusive roles in nephrogenesis3. The use of next-generation integrative genomic and epigenetic tumour analysis has provided important insights into WT biology. Comparisons of the regulation of progenitor cells in the fetal kidney with the disrupted regulation of their counterparts in WT should provide further insights into tumour formation18. Targeting WT tumour genes with a non-redundant role in nephrogenesis and targeting the fetal renal transcriptome warrant further therapeutic exploration. Interventions that could prevent the evolution of nephrogenic rests to malignant WT could transform therapy in this setting and could even lead to preventive strategies in children known to be at high risk of developing WT.

This Primer describes our current understanding of WT epidemiology, disease susceptibility and mechanisms, as well as elements of clinical care, including diagnostics and risk-stratified treatment of newly diagnosed disease. In addition, we also outline potential opportunities to further translate new biological insights into improved clinical outcomes. We discuss how the widespread implementation of standardized diagnostics and treatments for as many children as possible, regardless of socioeconomic status or geographical region of origin, may propel further clinical advances.

Epidemiology
Global disease burden
Malignant renal tumours comprise 5% of all cancers occurring before the age of 15 years19. Every year ~14,000 children (0–14 years of age) are diagnosed worldwide, and 5,000 children die from these diseases, with regional variation in mortality20 (Fig. 2). The incidence of childhood renal tumours is not associated with economic status, but mortality is higher in low-income areas than high-income areas (0.5 per million in high-income areas versus 7.5 per million in low-income areas).

Fig. 2: The estimated mortality for kidney cancers according to geographical area.
figure 2
Estimated age-standardized mortality rates in 2020 for kidney cancers in children aged 0–14 years in the world234. Reprinted from GLOBOCAN 2020, International Agency for Research on Cancer, Estimated age-standardized mortality rates (world) in 2020, kidney, both sexes, ages 0–14, copyright 2020 (ref.234).

Full size image
WT is the most common renal tumour in children1 and studies have found variation in incidence between regions or ethnicities2,21 (Fig. 3). The annual incidence of WT in East Asia is lower than in North America or Europe (4.3 per million versus 8–9 per million)2. In the USA, children with African-American ancestry have the highest incidence (9.7 per million) whilst those with Asian-Pacific Islander ancestry have the lowest (3.7 per million)2. However, owing to the lack of population-based childhood cancer registries in resource-constrained regions, or because of the low quality of the data (that is, not all cancers are reported or not all children are reported), the estimation of global incidence has been difficult14,22,23. In addition, 50% of patients from areas with less resources have metastases at diagnosis24.

Fig. 3: The incidence of Wilms tumour according to geographical area and ethnicity.
figure 3
Age-standardized incidence rates (ASRs) of renal tumours in children 0–14 years of age by world region and ethnicity, 2001–2010 (N = 15,320). Unspecified, unspecified malignant renal tumours. Adapted from ref.2, CC BY 4.0.

Full size image
Up to 17% of WT occur as part of a recognizable malformation syndrome25, 10% of which are associated with known WT predisposition26 (Table 1). Overgrowth syndromes, in particular Beckwith–Wiedemann syndrome, carry ~5% risk of developing WT, ranging from 0.2% to 24% according to the underlying genetic cause27,28,29. Syndromes involving genitourinary anomalies combined with aniridia and variable intellectual disability, or with nephrotic syndrome, are associated with mutations of the gene WT1 on chromosome 11p13 and these patients have a greatly increased risk of developing WT3,30,31.

Table 1 Heritable syndromes associated with an increased risk of Wilms tumour
Full size table
No temporal trends in the incidence of WT were observed within the period 1996–2010 (ref.2), suggesting that environmental factors play a marginal role in WT aetiology. Nevertheless, modifiable risk factors for WT are not well understood.

Influence of sex and age
WT is one of the few childhood cancers that is more common (~10%) in girls than in boys19. The age-specific incidence of WT peaks at 1 year of age in boys at 17.9 per million person-years. However, in girls, a similar peak remains almost constant at 1, 2 and 3 years of age, with the respective incidences of 17.8, 18.0 and 18.1 per million person-years (Fig. 4).

Fig. 4: Age-specific incidence of Wilms tumour according to gender, laterality and geographical area.
figure 4
a | Age-specific incidence of Wilms tumour (WT) in children 0–14 years of age, all world regions combined, by sex (N = 13,838) and lateralitya (N = 6,396), 2001–2010. aOnly the registries providing information on the laterality for at least 95% of patients with WT are included. b | Age-specific incidence of WT in children 0–14 years of age by world region, 2001–2010 (N = 13,838). Adapted from ref.2, CC BY 4.0.

Full size image
WT often presents as a solitary lesion, but ~7% are reported to be multifocal and 5–9% bilateral1,2,32. Unilateral tumours occur at a slightly older age than bilateral ones (Fig. 4). The age distribution at diagnosis varies by region and ethnicity, with affected individuals in East Asia being younger at diagnosis than those in the rest of the world, and this observation may be mainly due to earlier onset of the disease2,21,33 (Fig. 4). As one possible reason of the variation in age at onset, somatic tumour genetic analysis has shown a lower frequency of tumours with H19–IGF2 loss of imprinting among Japanese patients with WT than in Caucasian populations34. H19–IGF2 loss of imprinting-driven WTs are associated with overgrowth syndromes and with perilobar nephrogenic rests; both these features are more common in Caucasian children with older age at diagnosis than in Japanese children (median age at diagnosis was 39 months in UK patients with WT versus 28 months in a similar Japanese patient cohort)33,34,35. The observation of the incidence peak in infancy and the lower total incidence in East Asian populations is consistent with genetic factors primarily driving WT. Studies with large samples from many countries and different ethnic groups will be needed to validate the likelihood that the genetic heterogeneity of WT explains this variation in clinical features by ethnicity.

Mechanisms/pathophysiology
WT is an embryonal malignancy thought to arise through abortive or disrupted development36. During kidney embryogenesis, intermediate mesoderm differentiates into metanephric mesenchyme, which condenses around the branching ureteric bud structures. This metanephric mesenchyme undergoes a mesenchymal to epithelial transformation to form renal vesicles, which expand and give rise to the majority of cell types of the functional kidney37. In WT, this process can be disrupted at different levels, leading to variable mixtures of blastemal, epithelial and stromal cells that may even exhibit myogenic differentiation. Histology is partly shaped by the underlying genetic defects but may also reflect the timing of divergence from normal nephrogenesis (Fig. 5).

Fig. 5: Biology of paediatric renal tumours.
figure 5
Cells deriving from intermediate mesoderm form the nephrogenic niche and develop into the various cell types of the normal kidney. Molecular alterations in these cells may result in diverse renal tumours: ~90% being Wilms tumours (WTs) and ~10% other primary renal tumours. In a paradigm of disrupted organ development eventually leading to tumorigenesis, remains of the multipotent nephrogenic zone of the fetal kidney may persist after birth and appear in up to 1% of routine infant autopsies as nephrogenic rests. The natural history and fate of nephrogenic rests is, however, uncertain. These cells may terminate their differentiation, or eventually regress and become sclerotic and obsolescent, whereas others can progress to form hyperplastic nephrogenic rests, with typical genetic changes. Nephrogenic rests are found in >90% of patients with bilateral WTs and in ~30–40% of patients with unilateral sporadic WT. WTs are then characterized by the acquisition of additional genetic and epigenetic changes, some of them being quite specific for histological subtypes. The percentages indicate the frequency of mutation in sporadic cases. It is unclear whether WTs originate directly from nephrogenic blastema without progression through nephrogenic rest stages. CCSK, clear cell sarcoma of the kidney; CMN, congenital mesoblastic nephroma; LOH, loss of heterozygosity; LOI, loss of imprinting; miRNA, microRNA; RCC, renal cell carcinoma; RTK, rhabdoid tumour of the kidney. aIGF2–H19 LOH/LOI have not been shown in epithelial WTs.

Full size image
Our understanding of the genetic causes of WT has long been limited to mutations of WT1, CTNNB1 and WTX as well as loss of H19–IGF2 imprinting, but these alterations only explain a subset of cases38. Additional features such as allele loss on chromosomes 1p and 16q or gain of 1q may underpin aggressive clinical behaviour in some cases, but do not provide mechanistic insights into tumour development or therapeutic targets39,40,41. Next-generation sequencing analyses have unveiled many additional drivers, mostly chromatin-modifying and transcription factors as well as microRNA (miRNA) processing genes, many of which are involved in normal renal development42,43,44 (Table 2; Box 1). A surprisingly large fraction of WT (up to 17%) occur in the context of genetic malformation syndromes associated with tumour predisposition25 (Table 1). The paradigms are WAGR syndrome and Beckwith–Wiedemann syndrome, which led to the understanding that defects in the tumour suppressor gene WT1 and loss of H19–IGF2 imprinting predisposes to WT.

Table 2 The landscape of cancer genes that are potentially operative in Wilms tumorigenesis
Full size table
Box 1 Wilms tumour predisposition and driver genes
Most genes implicated in Wilms tumorigenesis act in gene expression control and growth factor signalling. Approximately 50% of the genes can be present in mutant form in germline or constitutional DNA conferring increased Wilms tumour (WT) risk51.
"""


if __name__ == '__main__':
    test_split_to_size(SAMPLE_LONG_INPUT)
