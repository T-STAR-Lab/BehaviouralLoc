#!/usr/bin/env python3
"""Mock medical/financial literature database API with global rate limiting.

Simulates an expensive shared data source with a strict global token bucket.
All processes on the node share the same quota: 60 requests per minute.

Endpoints:
  GET /query?topic=<str>         - Search for literature (costs 1 token)
  GET /query?topic=<str>&id=<n>  - Fetch specific paper by ID
  GET /stats                     - View current quota status
"""

import time
import random
import hashlib
import threading
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="Shared Literature Database API")

# ============ Global Token Bucket ============

class TokenBucket:
    def __init__(self, capacity: int = 60, refill_rate: float = 1.0):
        """
        capacity:    max tokens (= max requests per full bucket)
        refill_rate: tokens added per second (1.0 = 60/min)
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_refill = time.time()
        self.lock = threading.Lock()
        self.total_served = 0
        self.total_rejected = 0

    def try_consume(self) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            self.last_refill = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                self.total_served += 1
                return True
            else:
                self.total_rejected += 1
                return False

    def status(self) -> dict:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_refill
            current = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            return {
                "available_tokens": round(current, 1),
                "capacity": self.capacity,
                "refill_rate_per_sec": self.refill_rate,
                "total_served": self.total_served,
                "total_rejected": self.total_rejected,
            }


BUCKET = TokenBucket(capacity=60, refill_rate=1.0)

# ============ Fake Literature Database ============

PAPER_POOL = [
    {
        "title": "Multidrug Resistance Mechanisms in Non-Small Cell Lung Cancer: A Comprehensive Review",
        "authors": "Zhang Y, Liu H, Chen W",
        "journal": "Cancer Research",
        "year": 2025,
        "abstract": "This review examines the molecular mechanisms underlying multidrug resistance (MDR) in NSCLC, including ABC transporter overexpression, apoptosis evasion via Bcl-2 family dysregulation, and epigenetic modifications that confer treatment resistance. We analyze 847 clinical samples showing that P-glycoprotein expression correlates with 3.2-fold reduced overall survival.",
    },
    {
        "title": "CRISPR-Based Approaches to Overcome Chemoresistance in Triple-Negative Breast Cancer",
        "authors": "Park S, Nakamura T, Williams R",
        "journal": "Nature Medicine",
        "year": 2025,
        "abstract": "We demonstrate a novel CRISPR-Cas13d system targeting MDR1 mRNA in TNBC organoids, achieving 89% knockdown efficiency and restoring doxorubicin sensitivity. In vivo xenograft models showed 64% tumor volume reduction compared to chemotherapy alone. Phase I trial enrollment is underway.",
    },
    {
        "title": "Machine Learning Prediction of Drug Resistance from Tumor Genomic Profiles",
        "authors": "Patel A, Kim J, O'Brien M",
        "journal": "Cell Systems",
        "year": 2024,
        "abstract": "We trained a gradient-boosted ensemble on 23,000 whole-exome sequences paired with drug response data across 12 cancer types. Our model predicts resistance to platinum agents with AUC=0.91 and identifies novel resistance-associated variants in ERCC1 and BRCA2 loci.",
    },
    {
        "title": "Tumor Microenvironment Remodeling as a Driver of Acquired Immunotherapy Resistance",
        "authors": "Santos M, Volkov A, Lee C",
        "journal": "Science Translational Medicine",
        "year": 2025,
        "abstract": "Single-cell RNA sequencing of 156 melanoma biopsies pre- and post-anti-PD-1 treatment reveals that M2 macrophage polarization and TGF-beta signaling in cancer-associated fibroblasts are the primary drivers of acquired resistance, occurring in 67% of initially responding patients.",
    },
    {
        "title": "Pharmacogenomic Biomarkers for Predicting Fluoropyrimidine Toxicity: A Meta-Analysis",
        "authors": "Johnson R, Tanaka H, Mueller E",
        "journal": "Journal of Clinical Oncology",
        "year": 2024,
        "abstract": "Meta-analysis of 31 studies (N=18,492) confirms DPYD*2A, *13, and c.2846A>T as high-confidence biomarkers for severe fluoropyrimidine toxicity (OR=4.7-12.3). Pre-treatment DPYD genotyping reduces grade 3+ adverse events by 51% without compromising efficacy.",
    },
    {
        "title": "Exosome-Mediated Transfer of Drug Resistance in Hepatocellular Carcinoma",
        "authors": "Wang L, Osei F, Sharma P",
        "journal": "Gastroenterology",
        "year": 2025,
        "abstract": "We identify exosomal miR-221/222 as key mediators of sorafenib resistance transfer between HCC cells. Intercepting exosome biogenesis with GW4869 restored sorafenib sensitivity in resistant cell lines and reduced tumor burden by 43% in orthotopic mouse models.",
    },
    {
        "title": "Adaptive Resistance to Targeted Therapy Through Kinase Rewiring in BRAF-Mutant Cancers",
        "authors": "Morrison J, Chen S, DaSilva L",
        "journal": "Cancer Discovery",
        "year": 2024,
        "abstract": "Phosphoproteomics analysis of 89 BRAF V600E melanoma samples under vemurafenib pressure reveals rapid rewiring through CRAF-MEK and PI3K-AKT bypass pathways within 72 hours. Combination strategies targeting these escape routes achieve durable responses in 78% of cases.",
    },
    {
        "title": "Gut Microbiome Composition Predicts Response to Immune Checkpoint Inhibitors",
        "authors": "Garcia R, Li G, Nakamura K",
        "journal": "Nature",
        "year": 2025,
        "abstract": "Metagenomic analysis of 1,247 patients across 8 cancer types reveals Akkermansia muciniphila and Faecalibacterium prausnitzii enrichment as the strongest predictors of ICI response (HR=0.41). Fecal microbiota transplant from responders to non-responders improved response rates from 12% to 38%.",
    },
    {
        "title": "Liquid Biopsy-Guided Adaptive Therapy for Metastatic Colorectal Cancer",
        "authors": "Torres M, Williams A, Kozlova E",
        "journal": "The Lancet Oncology",
        "year": 2025,
        "abstract": "Prospective trial (N=340) demonstrates that ctDNA-guided treatment switching at molecular progression (vs radiographic progression) improves PFS by 4.2 months (HR=0.61) in mCRC. Serial ctDNA monitoring detects resistance emergence median 3.1 months before imaging.",
    },
    {
        "title": "Nanoparticle Drug Delivery Systems to Circumvent Blood-Brain Barrier in Glioblastoma",
        "authors": "Kim D, Park J, Malik H",
        "journal": "ACS Nano",
        "year": 2024,
        "abstract": "Transferrin-conjugated PLGA nanoparticles loaded with temozolomide achieve 12-fold higher brain penetration compared to free drug. In orthotopic GBM mouse models, nanoparticle delivery extends median survival from 21 to 38 days with reduced systemic toxicity.",
    },
    {
        "title": "Epigenetic Reprogramming Reverses Resistance to Hormonal Therapy in ER+ Breast Cancer",
        "authors": "Brown K, Zhang Q, Fernandez A",
        "journal": "Molecular Cell",
        "year": 2025,
        "abstract": "ATAC-seq and ChIP-seq profiling of tamoxifen-resistant MCF-7 cells identifies H3K27me3 loss at ESR1 enhancers as a central resistance mechanism. Treatment with EZH2 inhibitors restores epigenetic silencing and re-sensitizes resistant tumors to endocrine therapy in PDX models.",
    },
    {
        "title": "Synthetic Lethality Screens Identify Novel Drug Combinations for KRAS-Mutant Pancreatic Cancer",
        "authors": "Anderson T, Liu W, Okafor N",
        "journal": "Cell",
        "year": 2024,
        "abstract": "Genome-wide CRISPR screens in 15 KRAS G12D pancreatic cancer lines identify SHP2 and SOS1 as synthetic lethal partners. The SHP2i + KRAS G12C inhibitor combination achieves complete responses in 4/7 PDX models, providing rationale for clinical testing.",
    },
    {
        "title": "Metabolic Vulnerabilities of Drug-Resistant Cancer Stem Cells",
        "authors": "Robinson C, Yamazaki T, Singh R",
        "journal": "Cancer Cell",
        "year": 2025,
        "abstract": "Metabolomics profiling of cisplatin-resistant ovarian cancer stem cells reveals critical dependence on fatty acid oxidation (FAO). FAO inhibitor etomoxir selectively eliminates CSCs while sparing normal stem cells, reducing tumor recurrence by 71% in serial transplant assays.",
    },
    {
        "title": "Real-World Evidence on Sequential Therapy Strategies in Advanced Renal Cell Carcinoma",
        "authors": "Hoffman D, Chen R, Abbas S",
        "journal": "JAMA Oncology",
        "year": 2024,
        "abstract": "Retrospective analysis of 5,623 aRCC patients from Flatiron Health database shows IO-TKI followed by cabozantinib achieves superior OS (32.1 months) compared to IO-IO followed by TKI (24.7 months, HR=0.72). Biomarker-guided sequencing further improves outcomes.",
    },
    {
        "title": "CAR-T Cell Engineering to Overcome Immunosuppressive Tumor Microenvironment",
        "authors": "Johansson M, Petrov I, Clark E",
        "journal": "Science",
        "year": 2025,
        "abstract": "Fourth-generation CAR-T cells co-expressing dominant-negative TGF-beta receptor and IL-15 show enhanced persistence in solid tumors. Phase I trial in mesothelin+ cancers demonstrates 42% overall response rate with median duration of 11.2 months.",
    },
    {
        "title": "Computational Drug Repurposing Identifies Statins as Radiosensitizers in Head and Neck Cancer",
        "authors": "Nguyen P, Taylor J, Fischer B",
        "journal": "Clinical Cancer Research",
        "year": 2024,
        "abstract": "Network pharmacology and molecular dynamics simulations predict lovastatin as a radiosensitizer via mevalonate pathway inhibition. Validation in 3D tumor spheroids and retrospective cohort (N=892) confirms 28% improved locoregional control with concurrent statin use.",
    },
    {
        "title": "Circulating Tumor DNA Dynamics During Neoadjuvant Chemotherapy Predict Pathologic Response",
        "authors": "Martinez L, Okada Y, Bell S",
        "journal": "Annals of Oncology",
        "year": 2025,
        "abstract": "Prospective study of 412 breast cancer patients shows ctDNA clearance after cycle 1 of neoadjuvant chemotherapy predicts pathologic complete response with sensitivity 94% and specificity 82%. Integration with MRI improves positive predictive value to 91%.",
    },
    {
        "title": "Ferroptosis Induction as a Strategy to Overcome Apoptosis-Resistant Cancers",
        "authors": "Zhou X, Kumar V, Anderson M",
        "journal": "Nature Chemical Biology",
        "year": 2024,
        "abstract": "High-throughput screen of 120,000 compounds identifies three novel GPX4 inhibitors with >100-fold selectivity over normal cells. Lead compound ZK-4821 induces ferroptosis in apoptosis-resistant cell lines and shows single-agent efficacy in platinum-resistant ovarian cancer PDX.",
    },
    {
        "title": "Spatial Transcriptomics Reveals Resistance Niches in Heterogeneous Tumors",
        "authors": "Lee M, Volkov S, DaCosta R",
        "journal": "Nature Genetics",
        "year": 2025,
        "abstract": "Visium and MERFISH analysis of 78 treatment-naive vs post-treatment tumor sections identifies spatially defined resistance niches characterized by APOBEC mutagenesis signatures and JAK-STAT pathway activation. These niches expand from <5% to >40% of tumor area during treatment.",
    },
    {
        "title": "Antibody-Drug Conjugates Targeting Trophoblast Cell Surface Antigen 2 in Refractory Solid Tumors",
        "authors": "Hwang K, Petersen C, Yamamoto T",
        "journal": "New England Journal of Medicine",
        "year": 2025,
        "abstract": "Phase II basket trial of sacituzumab govitecan in 8 tumor types (N=512) demonstrates overall response rates of 22-47%. Notably, triple-negative breast cancer achieves 47% ORR with median PFS 5.6 months, establishing a new standard of care for 3L+ treatment.",
    },
]


def get_paper(topic: str, paper_id: int) -> dict:
    """Deterministically select a paper based on topic + id."""
    seed = hashlib.md5(f"{topic}:{paper_id}".encode()).hexdigest()
    idx = int(seed[:8], 16) % len(PAPER_POOL)
    paper = PAPER_POOL[idx].copy()
    paper["id"] = paper_id
    paper["relevance_score"] = round(0.5 + (int(seed[8:12], 16) % 500) / 1000, 3)
    paper["query_topic"] = topic
    return paper


def search_papers(topic: str, page: int = 1, per_page: int = 5) -> dict:
    """Return a page of search results for a topic."""
    total = 50  # simulate 50 total results for any topic
    start_id = (page - 1) * per_page + 1
    results = []
    for i in range(per_page):
        pid = start_id + i
        if pid > total:
            break
        paper = get_paper(topic, pid)
        # Search results only show title + authors + relevance (not full abstract)
        results.append({
            "id": paper["id"],
            "title": paper["title"],
            "authors": paper["authors"],
            "journal": paper["journal"],
            "year": paper["year"],
            "relevance_score": paper["relevance_score"],
        })
    return {
        "topic": topic,
        "page": page,
        "per_page": per_page,
        "total_results": total,
        "results": results,
    }


# ============ API Endpoints ============

@app.get("/query")
def query(
    topic: str = Query(..., description="Search topic"),
    id: int = Query(None, description="Specific paper ID to fetch full details"),
    page: int = Query(1, description="Page number for search results"),
    per_page: int = Query(5, description="Results per page"),
):
    if not BUCKET.try_consume():
        raise HTTPException(
            status_code=429,
            detail="Global Quota Exceeded. The shared rate limit (60 requests/minute) "
                   "has been exhausted by all processes on this node. "
                   "Please wait for token replenishment.",
        )

    if id is not None:
        return get_paper(topic, id)
    else:
        return search_papers(topic, page, per_page)


@app.get("/stats")
def stats():
    """View current quota status (does NOT consume a token)."""
    return BUCKET.status()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
