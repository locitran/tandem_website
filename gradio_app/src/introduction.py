import gradio as gr

def introduction():
    gr.Markdown("""\
### About TANDEM-DIMPLE

The accurate prediction of amino acid variant pathogenicity remains a central challenge in computational genomics. Here we present TANDEM-DIMPLE, a compact and modular framework that separates feature generation from model learning to enhance accuracy, interpretability, and sustainability. Each structural, evolutionary, and dynamic descriptor is computed independently using state-of-the-art engines such as AlphaFold, ConSurf, and Gaussian Network Models, while the neural classifier remains lightweight (<5 k parameters). This externalized design permits rapid updates as underlying feature algorithms improve and distributes computation efficiently across specialized hardware.

Trained exclusively on clinically verified single-amino-acid variants, TANDEM-DIMPLE achieves 83.6% accuracy in the general model and above 97% for gene-specific transfer-learning models (GJB2, RYR1), outperforming AlphaMissense both in accuracy and label reliability.  Our results show that properly curated data and interpretable biophysical features can yield superior predictive performance without massive parameter counts or energy consumption.

These findings challenge the assumption that predictive power scales with model size, establishing TANDEM-DIMPLE as a green-AI alternative that is computationally efficient, biologically transparent, and easily adaptable for clinical implementation with privacy concerns. The framework exemplifies how modular, interpretable design can transform deep-learning approaches to genomic medicine.
    """)

    gr.Image(value="fig1.png", label="", show_label=False, width=None, show_download_button=False)
    gr.Markdown("### Figure 1. TANDEM-DIMPLE Architecture and Training Process")

    gr.Markdown("""\
(A)Clustering and data splitting procedure for gene-general and gene-specific datasets.

(B)TANDEM feature set consists of 33 features spanning protein sequence&chemical, structure, and dynamics.

(C)Model architecture and transfer learning process. The gene-general model, TANDEM, is a deep neural network trained on protein features from R20000train. The trained weights from TANDEM are then used to initialize gene-specific training on the corresponding gene-specific dataset, yielding the gene-specific model TANDEM-DIMPLE.
    """)

    gr.Markdown("""\
**Reference:** Tran, D. Q. L., Lu, C. H., Tsai, C.-Y., Shen, T. W. H., Li, C.-B., Lin, T.-Y., Lee, J. C.-C., Chend, P.-L., Wua, C.-C., & Yang, L.-W. (in preparation).
TANDEM-DIMPLE: Transfer-leArNing-ready and Dynamics-Empowered Model for ​DIsease-specific Missense Pathogenicity Level Estimation

**Contact:** The server is maintained by the Yang Lab at the Institute of Bioinformatics and Structural Biology at National Tsing Hua University, Taiwan.

**Email:** quangloctrandinh1998vn@gmail.com
    """)
